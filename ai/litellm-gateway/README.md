# LiteLLM Local AI Gateway (Jetson Thor)

This project provides a local OpenAI-compatible gateway with automatic routing for:

- `general` -> `qwen3.6` / Qwen3.6-35B-A3B-NVFP4 (`http://thor:8000/v1`)
- `coder` -> `qwen2.5-coder` / Qwen2.5-Coder-14B-Instruct-NVFP4 (`http://thor:8001/v1`)
- `classifier` -> `qwen3-routing-classifier` / kaitchup/Qwen3-1.7B-NVFP4 (`http://thor:8002/v1`)

Architecture:

Open-WebUI -> LiteLLM Router (FastAPI + LiteLLM) -> local vLLM model endpoints

## Features

- OpenAI-compatible endpoint: `POST /v1/chat/completions`
- Model groups: `general`, `coder`
- Rule-based routing by coding keywords
- Optional LLM classifier routing (`ENABLE_LLM_ROUTER=true`)
- Explicit model routing for `general`, `coder`, and their upstream aliases
- `classify` mode to force model-based routing from Hermes or another client
- Dedicated Qwen3 1.7B NVFP4 classifier for model-based routing
- Fallback chain:
  - `coder -> general`
  - `general -> general`
- Structured JSON logs
- Full request/response audit log in JSONL format (`/app/logs/llm-requests.jsonl`)
- Prometheus metrics endpoint: `GET /metrics`
- Health checks: `GET /healthz`, `GET /readyz`

## Files

- `docker-compose.yml`
- `litellm_config.yaml`
- `router.py`
- `requirements.txt`
- `.env.example`

## Startanleitung

1. Copy environment template:

```bash
cp .env.example .env
```

2. Adjust values in `.env` if needed.

3. Start the gateway:

```bash
docker compose up -d
```

4. Verify:

```bash
curl -s http://127.0.0.1:4000/healthz
curl -s http://127.0.0.1:4000/v1/models | jq
```

## Open-WebUI Integration

In Open-WebUI add a custom OpenAI endpoint:

- Base URL: `http://<gateway-host>:4000/v1`
- API key: any non-empty string (for example `sk-local`)

For normal chat UX, send:

```json
"chat_template_kwargs": {"enable_thinking": false}
```

## LiteLLM Integration

This gateway already uses LiteLLM internally.
If another client should call through this gateway, use it exactly like an OpenAI API:

- `POST /v1/chat/completions`
- `GET /v1/models`

Routing precedence is:

1. Explicit `model` value `classify` forces the LLM classifier
2. Explicit `model` value (`general`, `coder`, `qwen3.6`, or `qwen2.5-coder`)
3. Coding keyword match when `ENABLE_RULE_ROUTER=true`
4. LLM classifier when `ENABLE_LLM_ROUTER=true`
5. General model as the default

In Hermes, select the OpenAI-compatible model `classify` when you want the
router to decide between the general and coder backends. Select `general` or
`coder` to force a direct mode.

The configured fallback `coder -> general` is used only when the selected coder
upstream request fails. It does not override explicit model selection.

## LLM audit log

The audit log is enabled in the main Compose service for local testing. Each
request produces JSONL records for the request start and completion, including
the routing decision, upstream model, response, status, and duration. Streaming
responses are stored as their collected chunks after completion.

The host log directory is `~/docker/vllm/litellm-gateway/logs`. Contents are truncated
per string at `LLM_AUDIT_LOG_MAX_CHARS`, rotated at `LLM_AUDIT_LOG_MAX_BYTES`, and
sensitive keys such as API keys and authorization values are redacted. Disable it with `LLM_AUDIT_LOG=false` when
prompts and responses should not be persisted.

Inspect recent records with:

```bash
jq . ~/docker/litellm-router/logs/llm-requests.jsonl
```

## Prometheus Integration

Scrape the metrics endpoint:

- URL: `http://<gateway-host>:4000/metrics`

Exposed metrics:

- `completed_requests_total`
- `routing_decisions_total`
- `model_usage_total`
- `routing_duration_seconds`

Example scrape config:

```yaml
scrape_configs:
  - job_name: litellm_router
    metrics_path: /metrics
    static_configs:
      - targets: ["litellm-router:4000"]
```

## Health Checks

- Liveness: `GET /healthz`
- Readiness: `GET /readyz`

## Beispiel-curl-Aufrufe

### 1) General request

```bash
curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "auto",
    "messages": [
      {"role": "user", "content": "Erklaere kurz den Unterschied zwischen RAM und VRAM."}
    ],
    "max_tokens": 256,
    "temperature": 0,
    "chat_template_kwargs": {"enable_thinking": false}
  }' | jq
```

### 2) Coding request (rule-based -> coder)

```bash
curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "auto",
    "messages": [
      {"role": "user", "content": "Schreibe ein Python Skript fuer Docker Log Parsing."}
    ],
    "max_tokens": 256,
    "temperature": 0,
    "chat_template_kwargs": {"enable_thinking": false}
  }' | jq
```

### 3) Enable optional LLM router

```bash
ENABLE_LLM_ROUTER=true docker compose up -d
```

### 4) Streaming request

```bash
curl -N http://127.0.0.1:4000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "auto",
    "messages": [{"role": "user", "content": "Nenne drei Debugging Tipps."}],
    "stream": true,
    "max_tokens": 256
  }'
```

## Notes for Jetson AGX Thor

- Keep model servers local (`thor:8000` and `thor:8001`).
- For normal UI flows, disable thinking in requests to avoid long reasoning traces.
- Fallback is automatic when coder endpoint is unavailable.
