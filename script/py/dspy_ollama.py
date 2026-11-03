"""
DSPy prompt optimiser backed by a local Ollama model.

Takes a short creative brief and turns it into a detailed cinematic video
prompt using a DSPy ``ChainOfThought`` module.

Configuration (environment variables)
-------------------------------------
    DSPY_OLLAMA_MODEL   DSPy model string, default ``ollama/gemma4:e2b``.
                        The ``ollama/`` prefix tells DSPy to use the Ollama
                        provider; the part after it is the Ollama model tag.
    OLLAMA_HOST         Ollama server base URL, default
                        ``http://localhost:11434``.

Model auto-detection
--------------------
People very often configure a model tag they never pulled (or a stale tag),
which surfaces as an opaque "model not found" error at inference time.  Before
building the DSPy LM this script queries ``{OLLAMA_HOST}/api/tags`` and, when
the configured tag is not installed, falls back to the first locally available
model and prints a clear warning naming both tags.  If Ollama is unreachable
the configured model is kept so the eventual error still mentions the real
model and host.

Usage
-----
    python dspy_ollama.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

import dspy

# --- Configuration ---------------------------------------------------------
DEFAULT_MODEL = "ollama/gemma4:e2b"
DEFAULT_OLLAMA_HOST = "http://localhost:11434"
#: DSPy/Ollama model prefix that must be preserved on the resolved model.
OLLAMA_PREFIX = "ollama/"
#: Short timeout so a missing Ollama server does not stall the script.
TAGS_TIMEOUT_SECONDS = 3.0


def fetch_ollama_models(host: str, timeout: float = TAGS_TIMEOUT_SECONDS) -> list[str]:
    """Return the model tags installed on the Ollama server at ``host``.

    Uses the stable ``/api/tags`` endpoint.  Any network or payload problem
    returns an empty list (a warning is printed) so callers can decide how to
    degrade gracefully instead of crashing.
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
    # Ollama treats an untagged name as ":latest".
    if ":" not in configured_bare and f"{configured_bare}:latest" in available:
        return True
    if ":" not in configured_bare:
        # e.g. configured "llama3" vs installed "llama3:8b".
        return any(name.split(":", 1)[0] == configured_bare for name in available)
    return False


def resolve_dspy_model(configured_model: str, host: str) -> str:
    """Return a model string that exists on the Ollama server.

    Falls back to the first installed model (with a clear warning) when the
    configured tag is absent.  The configured string is returned unchanged
    when the server cannot be queried or already has the model.
    """
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


class VideoPromptGenerator(dspy.Signature):
    """Convert a basic video concept into a structured, highly descriptive cinematic prompt."""

    creative_brief = dspy.InputField(desc="The core video concept or idea")
    optimized_prompt = dspy.OutputField(
        desc="A detailed prompt following the Subject -> Style -> Camera -> Lighting format"
    )


def build_lm() -> tuple[object, str, str]:
    """Resolve configuration and build a configured DSPy Ollama LM.

    Returns ``(lm, resolved_model, host)``.
    """
    configured_model = os.getenv("DSPY_OLLAMA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    host = os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_HOST).strip() or DEFAULT_OLLAMA_HOST
    resolved_model = resolve_dspy_model(configured_model, host)

    lm = dspy.LM(
        model=resolved_model,
        api_base=host,
        api_key="none",  # Ollama does not require an API key
        config={
            "max_tokens": 4096,
            "temperature": 0.2,      # low temperature keeps the format stable
            "top_p": 0.9,
            "num_ctx": 8192,
            "repeat_penalty": 1.15,
        },
    )
    return lm, resolved_model, host


def main() -> int:
    """Run one optimisation end-to-end; return the process exit code."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

    try:
        lm, resolved_model, host = build_lm()
    except Exception as exc:  # configuration errors from DSPy (missing driver, etc.)
        print(f"[ERROR] Failed to initialise the DSPy LM: {exc}", file=sys.stderr)
        return 1

    dspy.settings.configure(lm=lm)
    prompt_optimizer = dspy.ChainOfThought(VideoPromptGenerator)

    brief = "A futuristic cyberpunk hover-car driving down a rainy street."
    print(f"Model: {resolved_model}  |  Ollama host: {host}\n")

    try:
        result = prompt_optimizer(creative_brief=brief)
    except Exception as exc:  # network/server/model failures from Ollama
        print(f"[ERROR] Prompt optimisation failed: {exc}", file=sys.stderr)
        print(
            "        Check that the Ollama server is running "
            f"({host}) and the model is pulled: `ollama pull <model>`",
            file=sys.stderr,
        )
        return 1

    rationale_text = str(
        getattr(result, "rationale", None) or "Model did not provide a reasoning chain."
    ).strip()
    optimized_prompt_text = str(getattr(result, "optimized_prompt", "") or "").strip()

    print(f"Creative Brief: {brief}\n")
    print(f"Rationale:\n{rationale_text}\n")
    print(f"Optimized Prompt:\n{optimized_prompt_text or '(model returned an empty prompt)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
