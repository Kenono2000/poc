"""
FastAPI service that optimises video creative briefs with a local Ollama model.

Endpoint
--------
``POST /api/chat/optimize``

    request : {"message": "<creative brief>"}
    response: {
        "user_brief": "...",
        "rationale": "...",        # chain-of-thought reason (best effort)
        "optimized_prompt": "..."  # Subject -> Style -> Camera -> Lighting prompt
    }

Errors
------
* ``400`` -- the supplied brief is blank/whitespace only.
* ``500`` -- Ollama/DSPy failed (server down, model missing, empty completion,
  unexpected exception).  The exception is caught as ``Exception`` on purpose:
  referencing ``dspy.utils.Error`` can itself raise ``AttributeError`` when the
  attribute does not exist in the installed DSPy version, which would hide the
  original failure and return an unhandled 500 traceback instead of a clean
  HTTP error response.

Configuration (environment variables)
-------------------------------------
    DSPY_OLLAMA_MODEL   DSPy model string, default ``ollama/gemma4:e2b``.
    OLLAMA_HOST         Ollama base URL, default ``http://localhost:11434``.

Model auto-detection
--------------------
Before the first optimisation request the service resolves the configured
model against ``{OLLAMA_HOST}/api/tags``.  If the configured tag is not
installed it falls back to the first available local model and logs a clear
warning, which turns a confusing "model not found" failure into a working
request (or an explicit message when no models are installed at all).

Run
---
    python dspy_server.py
    # or: uvicorn dspy_server:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
import urllib.error
import urllib.request

import dspy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# --- Configuration ---------------------------------------------------------
DEFAULT_MODEL = "ollama/gemma4:e2b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
OLLAMA_PREFIX = "ollama/"
TAGS_TIMEOUT_SECONDS = 3.0

app = FastAPI(title="AI Video Prompt Optimizer API")


# ---------------------------------------------------------------------------
# Ollama model discovery (kept self-contained so this file can be deployed
# alone; mirrors the helper in dspy_ollama.py).
# ---------------------------------------------------------------------------
def fetch_ollama_models(host: str, timeout: float = TAGS_TIMEOUT_SECONDS) -> list[str]:
    """Return the model tags installed on the Ollama server at ``host``.

    Returns an empty list (with a warning) when the server is unreachable or
    returns something unexpected.
    """
    url = f"{host.rstrip('/')}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        print(f"[WARN] Could not query Ollama model list at {url}: {exc}", file=sys.stderr)
        return []

    if not isinstance(payload, dict):
        return []

    models: list[str] = []
    for entry in payload.get("models", []) or []:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("model")
        if isinstance(name, str) and name.strip():
            models.append(name.strip())
    return sorted(dict.fromkeys(models), key=str.lower)


def _model_is_installed(configured_bare: str, available: list[str]) -> bool:
    """True when ``configured_bare`` matches an installed Ollama tag."""
    if configured_bare in available:
        return True
    if ":" not in configured_bare and f"{configured_bare}:latest" in available:
        return True
    if ":" not in configured_bare:
        return any(name.split(":", 1)[0] == configured_bare for name in available)
    return False


def resolve_dspy_model(configured_model: str, host: str) -> str:
    """Return a model string that exists on the Ollama server when possible."""
    configured_model = (configured_model or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    bare = (
        configured_model[len(OLLAMA_PREFIX):]
        if configured_model.startswith(OLLAMA_PREFIX)
        else configured_model
    )

    available = fetch_ollama_models(host)
    if not available:
        print(
            f"[WARN] Could not verify model '{configured_model}' "
            f"(no model list from {host}); using it as configured.",
            file=sys.stderr,
        )
        return configured_model

    if _model_is_installed(bare, available):
        return configured_model

    fallback_name = available[0]
    fallback_model = (
        f"{OLLAMA_PREFIX}{fallback_name}"
        if configured_model.startswith(OLLAMA_PREFIX)
        else fallback_name
    )
    print("[WARN] Configured Ollama model is not installed; falling back.", file=sys.stderr)
    print(f"       configured: {configured_model!r} (looked for {bare!r})", file=sys.stderr)
    preview = ", ".join(available[:8]) + (" ..." if len(available) > 8 else "")
    print(f"       available : {preview}", file=sys.stderr)
    print(
        f"       using     : {fallback_model!r} "
        "(run `ollama pull <model>` or set DSPY_OLLAMA_MODEL to change this)",
        file=sys.stderr,
    )
    return fallback_model


# ---------------------------------------------------------------------------
# DSPy signature / lazily-built module
# ---------------------------------------------------------------------------
class VideoPromptGenerator(dspy.Signature):
    """Convert a basic video concept into a structured, highly descriptive cinematic prompt."""

    creative_brief = dspy.InputField(
        desc="The core high-level video concept or idea from the user"
    )
    optimized_prompt = dspy.OutputField(
        desc="A detailed prompt following the Subject -> Style -> Camera -> Lighting format"
    )


class ChatRequest(BaseModel):
    """Request body for the optimise endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Response body for the optimise endpoint."""

    user_brief: str
    rationale: str
    optimized_prompt: str


_optimizer: dspy.ChainOfThought | None = None
_optimizer_lock = threading.Lock()


def get_optimizer() -> dspy.ChainOfThought:
    """Build (once) and return the DSPy prompt-optimiser module.

    Building lazily keeps ``import dspy_server`` cheap and means a missing
    Ollama server produces a clean per-request 500 instead of an import crash.
    """
    global _optimizer
    if _optimizer is not None:
        return _optimizer

    with _optimizer_lock:
        if _optimizer is not None:
            return _optimizer

        configured_model = (
            os.getenv("DSPY_OLLAMA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        )
        host = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).strip() or DEFAULT_OLLAMA_HOST
        resolved_model = resolve_dspy_model(configured_model, host)

        lm = dspy.LM(
            model=resolved_model,
            api_base=host,
            api_key="none",
            config={
                "num_ctx": 65536,
                "temperature": 0.2,
                "top_p": 0.9,
                "repeat_penalty": 1.15,
            },
        )
        dspy.settings.configure(lm=lm)
        _optimizer = dspy.ChainOfThought(VideoPromptGenerator)
        print(
            f"[INFO] DSPy optimizer ready (model={resolved_model!r}, host={host!r})",
            file=sys.stderr,
        )
        return _optimizer


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.post("/api/chat/optimize", response_model=ChatResponse)
async def optimize_user_prompt(payload: ChatRequest) -> ChatResponse:
    """Turn a creative brief into an optimised cinematic prompt."""
    brief = (payload.message or "").strip()
    if not brief:
        raise HTTPException(
            status_code=400,
            detail="The creative brief cannot be blank or empty.",
        )

    try:
        optimizer = get_optimizer()
        # DSPy is synchronous and network-bound: keep the event loop responsive.
        response = await asyncio.to_thread(optimizer, creative_brief=brief)

        rationale_text = str(
            getattr(response, "rationale", None)
            or "Model did not provide a reasoning chain."
        ).strip()
        optimized_prompt_text = str(
            getattr(response, "optimized_prompt", "") or ""
        ).strip()

        if not optimized_prompt_text:
            raise ValueError("model returned an empty prompt")

        return ChatResponse(
            user_brief=brief,
            rationale=rationale_text,
            optimized_prompt=optimized_prompt_text,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all (see module docstring)
        print(f"[ERROR] Prompt optimisation failed: {exc}", file=sys.stderr)
        raise HTTPException(
            status_code=500,
            detail=f"Internal Engine Processing Failure: {exc!s}",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    print(
        f"[INFO] Starting DSPy Ollama server "
        f"(model={os.getenv('DSPY_OLLAMA_MODEL', DEFAULT_MODEL)!r}, "
        f"host={os.getenv('OLLAMA_HOST', DEFAULT_OLLAMA_HOST)!r})",
        file=sys.stderr,
    )
    uvicorn.run("dspy_server:app", host="127.0.0.1", port=8000, reload=True)
