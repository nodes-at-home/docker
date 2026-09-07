#!/usr/bin/env python3
"""hermes-stt — OpenAI-kompatibler STT-Shim für faster-whisper (dustynv/faster-whisper-Image).

Endpoint (OpenAI-Shape, damit Hermes den eingebauten openai-Provider mit
base_url-Override nutzen kann):
  POST /v1/audio/transcriptions  → {"text": ...} (response_format=json) oder Plain-Text
  GET  /health

Multipart-Felder (openai-SDK): file, model (ignor.), language, response_format.
Das Whisper-Modell wird beim Start auf der GPU (Orin) geladen und bleibt
resident (float16).
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
log = logging.getLogger("hermes-stt")

MODEL = os.environ.get("WHISPER_MODEL", "large-v3")
DEVICE = os.environ.get("WHISPER_DEVICE", "auto")
COMPUTE = os.environ.get("WHISPER_COMPUTE", "float16")
LANG = os.environ.get("WHISPER_LANG", "de")
BEAM = int(os.environ.get("WHISPER_BEAM", "5"))
MODEL_ROOT = os.environ.get("WHISPER_MODEL_ROOT", "/data")
MODEL_PATH = os.environ.get("WHISPER_MODEL_PATH", "")
PORT = int(os.environ.get("PORT", "8000"))
VAD = os.environ.get("WHISPER_VAD", "true").lower() in ("1", "true", "yes")

_model = None
_model_desc = "unbekannt"


def _find_local_model() -> str | None:
    """HF-Hub-Layout: <root>/models--Systran--faster-whisper-<name>/snapshots/<hash>/model.bin"""
    if MODEL_PATH and Path(MODEL_PATH).is_dir():
        return MODEL_PATH
    cands = sorted(Path(MODEL_ROOT).glob(
        f"models--Systran--faster-whisper-{MODEL}/snapshots/*/model.bin"))
    return str(cands[-1].parent) if cands else None


def _load_model() -> None:
    global _model, _model_desc
    from faster_whisper import WhisperModel
    local = _find_local_model()
    if local:
        log.info("Lade Whisper-Modell aus lokalem Cache: %s (device=%s, compute=%s)",
                 local, DEVICE, COMPUTE)
        _model = WhisperModel(local, device=DEVICE, compute_type=COMPUTE)
        _model_desc = f"local:{Path(local).parent.parent.name}"
    else:
        log.warning("Kein lokales Modell unter %s — lade '%s' via HuggingFace", MODEL_ROOT, MODEL)
        _model = WhisperModel(MODEL, device=DEVICE, compute_type=COMPUTE,
                              download_root=MODEL_ROOT)
        _model_desc = f"hub:{MODEL}"
    log.info("Whisper-Modell bereit: %s", _model_desc)


app = FastAPI(title="hermes-stt")


@app.on_event("startup")
def _startup() -> None:
    # Blockierender Load im Startup-Event: Server nimmt Anfragen erst an,
    # wenn das Modell geladen ist (Orin-GPU, ~10-60 s).
    _load_model()


@app.get("/health")
def health() -> dict:
    return {"ok": _model is not None, "model": _model_desc,
            "device": DEVICE, "compute": COMPUTE, "lang": LANG}


def _to_wav16(audio: bytes) -> bytes | None:
    """Beliebiges Audio (ogg/mp3/m4a/wav) → PCM-16 WAV via ffmpeg; None wenn unmöglich."""
    if audio[:4] == b"RIFF":
        return audio  # bereits WAV
    if shutil.which("ffmpeg") is None:
        return None
    out = tempfile.mktemp(suffix=".wav")
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", "-y", out]
    try:
        p = subprocess.run(args, input=audio, capture_output=True, timeout=180)
        if p.returncode != 0:
            log.error("ffmpeg-Dekodierung fehlgeschlagen: %s", p.stderr.decode()[:200])
            return None
        return Path(out).read_bytes()
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def _run(audio: bytes, language: str | None):
    wav = _to_wav16(audio)
    payload = io.BytesIO(wav if wav is not None else audio)
    segments, info = _model.transcribe(
        payload, language=language, beam_size=BEAM, vad_filter=VAD)
    # segments ist ein Generator — sofort materialisieren
    return [(s.start, s.end, s.text) for s in segments], info


@app.post("/v1/audio/transcriptions")
async def transcriptions(request: Request) -> Response:
    form = None
    try:
        form = await request.form()
    except Exception as e:
        return JSONResponse({"error": f"form parse failed: {e}"[:200]}, status_code=400)
    file = form.get("file") if hasattr(form, "get") else None
    if file is None or not hasattr(file, "read"):
        return JSONResponse({"error": "no audio file"}, status_code=400)
    audio = await file.read()
    if not audio:
        return JSONResponse({"error": "empty audio"}, status_code=400)
    model_id = str(form.get("model") or MODEL)
    language = form.get("language") or LANG or None
    rfmt = str(form.get("response_format") or "json").lower()

    log.info("STT: %d Bytes, model=%s, lang=%s, response_format=%s",
             len(audio), model_id, language, rfmt)
    try:
        segments, info = await asyncio.to_thread(_run, audio, language)
    except Exception as e:
        log.exception("Transkription fehlgeschlagen")
        return JSONResponse({"error": str(e)[:300]}, status_code=500)

    text = " ".join(t.strip() for _, _, t in segments if t.strip()).strip()
    if rfmt == "text":
        return Response(content=text.encode("utf-8"), media_type="text/plain")
    return JSONResponse({
        "text": text,
        "language": info.language,
        "duration": round(float(info.duration), 2),
        "segments": [{"start": round(s, 2), "end": round(e, 2), "text": t.strip()}
                     for s, e, t in segments],
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
