# ─────────────────────────────────────────────────────────────────────────────
#  ollama_client.py  –  Thin wrapper around Ollama's /api/generate endpoint
# ─────────────────────────────────────────────────────────────────────────────

import time
import requests
from config import OLLAMA_URL, OLLAMA_EMBED_URL, OLLAMA_MODEL, EMBEDDING_MODEL

_TIMEOUT    = 180   # seconds per attempt
_MAX_RETRIES = 3    # total attempts before giving up


def generate(
    prompt:     str,
    system:     str = "",
    model:      str | None = None,
    max_tokens: int = 200,
    temperature: float = 0.85,
) -> str:
    """
    Call the local Ollama model and return the generated text.
    Retries up to _MAX_RETRIES times on timeout before giving up.
    Blocks until the response arrives (run in a thread for non-blocking use).
    """
    _model = model or OLLAMA_MODEL
    payload = {
        "model":  _model,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p":       0.92,
            "stop":        ["\n\n\n", "---"],
        },
    }

    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=_TIMEOUT)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

        except requests.exceptions.ConnectionError:
            return "[Ollama no detectado — ejecuta: ollama serve]"

        except requests.exceptions.Timeout:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(2)   # breve pausa antes de reintentar
                continue
            return "[Timeout: el modelo tardó demasiado]"

        except Exception as exc:
            return f"[Error Ollama: {exc}]"

    return "[Timeout: el modelo tardó demasiado]"


def embed(text: str, model: str | None = None) -> list[float] | None:
    """
    Get a vector embedding from Ollama. Returns None on any failure
    (model not pulled, server down, etc.) so callers can fall back gracefully.
    """
    if not text or not text.strip():
        return None
    _model = model or EMBEDDING_MODEL
    try:
        resp = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": _model, "prompt": text.strip()[:2000]},
            timeout=30,
        )
        resp.raise_for_status()
        emb = resp.json().get("embedding")
        return emb if isinstance(emb, list) and emb else None
    except Exception:
        return None

