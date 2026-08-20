import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from string import Template
from typing import Any

import yaml
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from litellm import acompletion
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, ConfigDict, ValidationError


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class ModelTarget:
    model: str
    api_base: str
    api_key: str


@dataclass
class RouterSettings:
    app_host: str
    app_port: int
    log_level: str
    request_timeout_sec: int
    enable_rule_router: bool
    enable_llm_router: bool
    classifier_prompt: str
    classifier_max_tokens: int
    classifier_temperature: float
    model_groups: dict[str, ModelTarget]
    fallbacks: dict[str, str]
    keyword_list: list[str]
    exposed_general_name: str
    exposed_coder_name: str


class ChatCompletionRequest(BaseModel):
    model: str | None = None
    messages: list[dict[str, Any]] | None = None
    prompt: str | None = None
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = None
    chat_template_kwargs: dict[str, Any] | None = None
    extra_body: dict[str, Any] | None = None

    model_config = ConfigDict(extra="allow")


class RouterError(Exception):
    pass


COMPLETED_REQUESTS_TOTAL = Counter(
    "completed_requests_total",
    "Completed chat completion requests",
    ["status_code", "model_group"],
)

ROUTING_DECISIONS_TOTAL = Counter(
    "routing_decisions_total",
    "Routing decisions made by the gateway",
    ["strategy", "decision"],
)

MODEL_USAGE_TOTAL = Counter(
    "model_usage_total",
    "Number of upstream model invocations",
    ["model_group"],
)

ROUTING_DURATION_SECONDS = Histogram(
    "routing_duration_seconds",
    "End-to-end routing duration in seconds",
    ["model_group", "status_code"],
)


def setup_logger(level: str) -> logging.Logger:
    logger = logging.getLogger("litellm-router")
    logger.setLevel(level.upper())
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def env_expand(value: str) -> str:
    return Template(value).safe_substitute(os.environ)


def load_config() -> RouterSettings:
    config_path = os.getenv("LITELLM_CONFIG_PATH", "/app/litellm_config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    groups = raw.get("model_groups", {})
    if "general" not in groups or "coder" not in groups:
        raise RuntimeError("litellm_config.yaml must define model_groups.general and model_groups.coder")

    general_model = os.getenv("GENERAL_MODEL", env_expand(groups["general"]["model"]))
    general_api_base = os.getenv("GENERAL_API_BASE", env_expand(groups["general"]["api_base"]))
    general_api_key = os.getenv("GENERAL_API_KEY", env_expand(groups["general"]["api_key"]))

    coder_model = os.getenv("CODER_MODEL", env_expand(groups["coder"]["model"]))
    coder_api_base = os.getenv("CODER_API_BASE", env_expand(groups["coder"]["api_base"]))
    coder_api_key = os.getenv("CODER_API_KEY", env_expand(groups["coder"]["api_key"]))

    keyword_override = os.getenv("ROUTER_KEYWORDS", "").strip()
    default_keywords = raw.get("routing", {}).get("keyword_list", [])
    if keyword_override:
        keyword_list = [k.strip().lower() for k in keyword_override.split(",") if k.strip()]
    else:
        keyword_list = [str(k).strip().lower() for k in default_keywords if str(k).strip()]

    llm_prompt = os.getenv(
        "LLM_CLASSIFIER_PROMPT",
        raw.get("routing", {}).get("llm_classifier_prompt", "Return GENERAL or CODING only. User request: {{prompt}}"),
    )

    fallbacks = raw.get("fallbacks", {"coder": "general", "general": "general"})

    return RouterSettings(
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP_PORT", "4000")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        request_timeout_sec=int(os.getenv("REQUEST_TIMEOUT_SEC", "180")),
        enable_rule_router=parse_bool(os.getenv("ENABLE_RULE_ROUTER", "true"), True),
        enable_llm_router=parse_bool(
            os.getenv("ENABLE_LLM_ROUTER", raw.get("routing", {}).get("enable_llm_router", "false")),
            False,
        ),
        classifier_prompt=llm_prompt,
        classifier_max_tokens=int(os.getenv("ROUTER_CLASSIFIER_MAX_TOKENS", "8")),
        classifier_temperature=float(os.getenv("ROUTER_CLASSIFIER_TEMPERATURE", "0")),
        model_groups={
            "general": ModelTarget(general_model, general_api_base, general_api_key),
            "coder": ModelTarget(coder_model, coder_api_base, coder_api_key),
        },
        fallbacks={str(k): str(v) for k, v in fallbacks.items()},
        keyword_list=keyword_list,
        exposed_general_name=os.getenv("EXPOSED_GENERAL_NAME", "general"),
        exposed_coder_name=os.getenv("EXPOSED_CODER_NAME", "coder"),
    )


settings = load_config()
logger = setup_logger(settings.log_level)
app = FastAPI(title="LiteLLM Local Router", version="1.0.0")


def log_event(event: str, **fields: Any) -> None:
    payload = {
        "ts_ms": now_ms(),
        "event": event,
        **fields,
    }
    logger.info(json.dumps(payload, ensure_ascii=False))


def extract_prompt_text(body: ChatCompletionRequest) -> str:
    if body.prompt:
        return body.prompt

    if not body.messages:
        return ""

    chunks: list[str] = []
    for msg in body.messages:
        role = str(msg.get("role", ""))
        if role not in {"user", "system", "assistant"}:
            continue
        content = msg.get("content", "")
        if isinstance(content, str):
            chunks.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    if isinstance(text, str):
                        chunks.append(text)
    return "\n".join(chunks)


def rule_route(prompt: str) -> tuple[str | None, str]:
    if not settings.enable_rule_router:
        return None, "rule_disabled"

    haystack = prompt.lower()
    for kw in settings.keyword_list:
        if kw and kw in haystack:
            ROUTING_DECISIONS_TOTAL.labels(strategy="rule", decision="coder").inc()
            return "coder", f"rule_keyword:{kw}"

    ROUTING_DECISIONS_TOTAL.labels(strategy="rule", decision="general").inc()
    return None, "rule_no_match"


async def llm_classify(prompt: str) -> tuple[str, str]:
    classifier_text = settings.classifier_prompt.replace("{{prompt}}", prompt)
    target = settings.model_groups["general"]

    response = await acompletion(
        model=target.model,
        api_base=target.api_base,
        api_key=target.api_key,
        timeout=settings.request_timeout_sec,
        messages=[
            {"role": "system", "content": "You are a strict classifier."},
            {"role": "user", "content": classifier_text},
        ],
        max_tokens=settings.classifier_max_tokens,
        temperature=settings.classifier_temperature,
    )

    text = ""
    try:
        text = response.choices[0].message.content or ""
    except Exception:
        text = ""

    category = text.strip().upper()
    if "CODING" in category:
        ROUTING_DECISIONS_TOTAL.labels(strategy="llm", decision="coder").inc()
        return "coder", "llm_classifier:CODING"

    ROUTING_DECISIONS_TOTAL.labels(strategy="llm", decision="general").inc()
    return "general", "llm_classifier:GENERAL"


async def pick_route(prompt: str) -> tuple[str, str]:
    rule_decision, reason = rule_route(prompt)
    if rule_decision == "coder":
        return "coder", reason

    if settings.enable_llm_router:
        try:
            return await llm_classify(prompt)
        except Exception as exc:
            log_event("llm_router_error", error=str(exc))
            ROUTING_DECISIONS_TOTAL.labels(strategy="llm", decision="general").inc()
            return "general", "llm_router_error:fallback_general"

    ROUTING_DECISIONS_TOTAL.labels(strategy="default", decision="general").inc()
    return "general", "default_general"


def normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    extra_body = merged.pop("extra_body", None)
    if isinstance(extra_body, dict):
        merged.update(extra_body)
    merged.pop("model", None)
    return merged


async def invoke_upstream(model_group: str, payload: dict[str, Any]) -> Any:
    target = settings.model_groups[model_group]
    MODEL_USAGE_TOTAL.labels(model_group=model_group).inc()
    return await acompletion(
        model=target.model,
        api_base=target.api_base,
        api_key=target.api_key,
        timeout=settings.request_timeout_sec,
        **payload,
    )


async def invoke_with_fallback(primary_group: str, payload: dict[str, Any]) -> tuple[Any, str, str]:
    fallback_group = settings.fallbacks.get(primary_group, primary_group)
    chain = [primary_group]
    if fallback_group not in chain:
        chain.append(fallback_group)

    last_error: Exception | None = None
    for idx, group in enumerate(chain):
        try:
            result = await invoke_upstream(group, payload)
            route_reason = "primary" if idx == 0 else f"fallback:{primary_group}->{group}"
            return result, group, route_reason
        except Exception as exc:
            last_error = exc
            log_event("upstream_error", attempted_group=group, error=str(exc))

    raise RouterError(f"All upstream attempts failed: {last_error}")


def response_to_dict(response: Any) -> dict[str, Any]:
    if hasattr(response, "model_dump"):
        return response.model_dump()
    if isinstance(response, dict):
        return response
    raise RouterError("Upstream response cannot be serialized")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, Any]:
    upstreams: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for group, target in settings.model_groups.items():
            expected_model = target.model.split("/", 1)[-1]
            models_url = f"{target.api_base.rstrip('/')}/models"

            try:
                response = await client.get(
                    models_url,
                    headers={"Authorization": f"Bearer {target.api_key}"},
                )
                response.raise_for_status()
                available_models = {
                    item.get("id")
                    for item in response.json().get("data", [])
                    if isinstance(item, dict)
                }
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"{group} upstream unavailable: {exc}") from exc

            if expected_model not in available_models:
                raise HTTPException(
                    status_code=503,
                    detail=f"{group} upstream does not expose expected model {expected_model}",
                )

            upstreams[group] = expected_model

    return {"status": "ready", "upstreams": upstreams}


@app.get("/metrics")
async def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.get("/v1/models")
async def v1_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": settings.exposed_general_name,
                "object": "model",
                "owned_by": "local",
            },
            {
                "id": settings.exposed_coder_name,
                "object": "model",
                "owned_by": "local",
            },
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request) -> Any:
    request_id = str(uuid.uuid4())
    started = time.perf_counter()
    status_code = "500"
    selected_group = "unknown"
    routing_reason = "unknown"

    try:
        body_raw = await request.json()
        body = ChatCompletionRequest.model_validate(body_raw)

        prompt_text = extract_prompt_text(body)
        if not prompt_text.strip():
            raise HTTPException(status_code=400, detail="Request must include non-empty messages or prompt")

        selected_group, routing_reason = await pick_route(prompt_text)
        payload = normalize_payload(body.model_dump(exclude_none=True))

        upstream_response, used_group, fallback_reason = await invoke_with_fallback(selected_group, payload)
        selected_group = used_group

        if fallback_reason != "primary":
            routing_reason = f"{routing_reason}|{fallback_reason}"

        duration_sec = time.perf_counter() - started

        if payload.get("stream", False):
            async def event_generator() -> Any:
                nonlocal status_code
                try:
                    async for chunk in upstream_response:
                        if hasattr(chunk, "model_dump"):
                            chunk_dict = chunk.model_dump()
                        elif isinstance(chunk, dict):
                            chunk_dict = chunk
                        else:
                            chunk_dict = {"object": "error", "message": "Unknown stream chunk"}
                        yield f"data: {json.dumps(chunk_dict, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                    status_code = "200"
                except Exception as exc:
                    status_code = "502"
                    error_payload = {
                        "error": {
                            "message": f"Streaming upstream error: {exc}",
                            "type": "upstream_error",
                            "code": "stream_failed",
                        }
                    }
                    yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
                    yield "data: [DONE]\n\n"
                finally:
                    COMPLETED_REQUESTS_TOTAL.labels(status_code=status_code, model_group=selected_group).inc()
                    ROUTING_DURATION_SECONDS.labels(model_group=selected_group, status_code=status_code).observe(
                        max(duration_sec, 0.0)
                    )
                    log_event(
                        "request_complete",
                        request_id=request_id,
                        status_code=int(status_code),
                        model_group=selected_group,
                        routing_reason=routing_reason,
                        duration_ms=int((time.perf_counter() - started) * 1000),
                    )

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        response_dict = response_to_dict(upstream_response)
        status_code = "200"

        COMPLETED_REQUESTS_TOTAL.labels(status_code=status_code, model_group=selected_group).inc()
        ROUTING_DURATION_SECONDS.labels(model_group=selected_group, status_code=status_code).observe(duration_sec)

        log_event(
            "request_complete",
            request_id=request_id,
            status_code=200,
            model_group=selected_group,
            routing_reason=routing_reason,
            duration_ms=int(duration_sec * 1000),
        )

        return JSONResponse(content=response_dict, status_code=200)

    except ValidationError as exc:
        status_code = "400"
        COMPLETED_REQUESTS_TOTAL.labels(status_code=status_code, model_group=selected_group).inc()
        ROUTING_DURATION_SECONDS.labels(model_group=selected_group, status_code=status_code).observe(
            max(time.perf_counter() - started, 0.0)
        )
        log_event("request_validation_error", request_id=request_id, error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid request body")

    except HTTPException:
        raise

    except Exception as exc:
        status_code = "502"
        COMPLETED_REQUESTS_TOTAL.labels(status_code=status_code, model_group=selected_group).inc()
        ROUTING_DURATION_SECONDS.labels(model_group=selected_group, status_code=status_code).observe(
            max(time.perf_counter() - started, 0.0)
        )
        log_event(
            "request_failed",
            request_id=request_id,
            model_group=selected_group,
            routing_reason=routing_reason,
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=str(exc),
        )
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": f"Upstream routing failed: {exc}",
                    "type": "upstream_error",
                    "code": "gateway_upstream_failed",
                }
            },
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"message": exc.detail}})
