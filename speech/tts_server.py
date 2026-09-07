#!/usr/bin/env python3
"""hermes-tts — OpenAI-kompatibler TTS-Shim für Piper (dustynv/piper-tts-Image).

Endpoint (OpenAI-Shape, damit Hermes den eingebauten openai-Provider mit
base_url-Override nutzen kann):
  POST /v1/audio/speech   → Audio (wav; mp3/opus/flac via ffmpeg)
  GET  /health            → Status + geladene Voices

Annimmt Multipart-Form (openai-SDK) oder JSON. Felder:
  input/text, voice, model (ignor.), response_format, speed
"""
import asyncio
import io
import json
import logging
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hermes-tts")

DATA_DIR = os.environ.get("PIPER_DATA_DIR", "/data/models/piper")
DEFAULT_VOICE = os.environ.get("PIPER_VOICE", "de_DE-thorsten-high")
USE_CUDA = os.environ.get("PIPER_CUDA", "true").lower() in ("1", "true", "yes")
PORT = int(os.environ.get("PORT", "8000"))

from piper.voice import PiperVoice  # noqa: E402  (nach Env-Setup)

_voices: dict[str, PiperVoice] = {}


def _voice_path(name: str) -> Path:
    return Path(DATA_DIR) / f"{name}.onnx"


def load_voice(name: str) -> PiperVoice:
    if name not in _voices:
        onnx = _voice_path(name)
        cfg = onnx.with_suffix(onnx.suffix + ".json")
        if not onnx.exists():
            raise FileNotFoundError(f"Voice nicht gefunden: {onnx}")
        log.info("Lade Voice %s (cuda=%s) ...", name, USE_CUDA)
        _voices[name] = PiperVoice.load(
            str(onnx), str(cfg) if cfg.exists() else None, use_cuda=USE_CUDA
        )
        log.info("Voice %s geladen", name)
    return _voices[name]


app = FastAPI(title="hermes-tts")


@app.on_event("startup")
def _startup() -> None:
    try:
        load_voice(DEFAULT_VOICE)
    except Exception:
        log.exception("Default-Voice nicht ladbar — Service startet trotzdem")


@app.get("/health")
def health() -> dict:
    return {"ok": True, "default_voice": DEFAULT_VOICE,
            "loaded_voices": sorted(_voices.keys()), "cuda": USE_CUDA}


def _parse_body(request_body: bytes, content_type: str) -> dict:
    if "multipart/form-data" in content_type:
        # openai-SDK sendet reine Form-Felder (keine Dateien)
        parts: dict[str, str] = {}
        boundary = content_type.split("boundary=", 1)[1].encode()
        for part in request_body.split(b"--" + boundary):
            if b"\r\n\r\n" not in part:
                continue
            head, val = part.split(b"\r\n\r\n", 1)
            name = None
            for line in head.split(b"\r\n"):
                low = line.lower()
                if low.startswith(b"content-disposition:"):
                    for kv in low.split(b";"):
                        kv = kv.strip()
                        if kv.startswith(b'name="'):
                            name = kv[6:-1].decode()
            if name is not None:
                parts[name] = val.rstrip(b"\r\n").decode("utf-8", "replace")
        return parts
    try:
        return json.loads(request_body or b"{}")
    except Exception:
        return {}


def _synthesize(text: str, voice: str, speed: float) -> bytes:
    """WAV (16-bit mono) per Piper; speed → length_scale (1/speed, geklemmt)."""
    pvoice = load_voice(voice) if _voice_path(voice).exists() else load_voice(DEFAULT_VOICE)
    length_scale = max(0.5, min(2.0, 1.0 / speed)) if speed and speed > 0 else 1.0
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        pvoice.synthesize(text, wf, length_scale=length_scale,
                          noise_scale=0.667, noise_w=0.333, sentence_silence=0.2)
    return buf.getvalue()


def _convert(wav_bytes: bytes, fmt: str) -> bytes | None:
    """WAV → mp3/opus(ogg)/flac via ffmpeg; None wenn nicht möglich."""
    if shutil.which("ffmpeg") is None:
        return None
    out_suffix = {"mp3": ".mp3", "mpeg": ".mp3", "opus": ".ogg",
                  "ogg": ".ogg", "flac": ".flac"}[fmt]
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0", "-y"]
    if fmt in ("mp3", "mpeg"):
        args += ["-c:a", "libmp3lame", "-b:a", "128k"]
    elif fmt in ("opus", "ogg"):
        args += ["-c:a", "libopus", "-ar", "24000", "-b:a", "48k"]
    elif fmt == "flac":
        args += ["-c:a", "flac"]
    out = tempfile.mktemp(suffix=out_suffix)
    args.append(out)
    try:
        p = subprocess.run(args, input=wav_bytes, capture_output=True, timeout=120)
        if p.returncode != 0:
            log.error("ffmpeg %s fehlgeschlagen: %s", fmt, p.stderr.decode()[:200])
            return None
        return Path(out).read_bytes()
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


MEDIA_TYPES = {"mp3": "audio/mpeg", "mpeg": "audio/mpeg", "opus": "audio/ogg",
               "ogg": "audio/ogg", "flac": "audio/flac"}


@app.post("/v1/audio/speech")
async def speech(request: Request) -> Response:
    body = await request.body()
    data = _parse_body(body, request.headers.get("content-type", ""))
    text = str(data.get("input") or data.get("text") or "").strip()
    if not text:
        return JSONResponse({"error": "missing 'input' text"}, status_code=400)
    voice = str(data.get("voice") or DEFAULT_VOICE)
    try:
        speed = float(data.get("speed") or 1.0)
    except (TypeError, ValueError):
        speed = 1.0
    fmt = str(data.get("response_format") or "wav").lower()

    try:
        wav = await asyncio.to_thread(_synthesize, text, voice, speed)
    except FileNotFoundError:
        return JSONResponse({"error": f"Voice unbekannt: {voice}"}, status_code=400)
    except Exception as e:
        log.exception("Synthese fehlgeschlagen")
        return JSONResponse({"error": str(e)[:300]}, status_code=500)

    if fmt == "wav":
        return Response(content=wav, media_type="audio/wav",
                        headers={"content-disposition": 'inline; filename="speech.wav"'})
    converted = await asyncio.to_thread(_convert, wav, fmt)
    if converted is not None:
        return Response(content=converted, media_type=MEDIA_TYPES[fmt])
    log.warning("response_format=%s nicht konvertierbar — fälle zurück auf wav", fmt)
    return Response(content=wav, media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
