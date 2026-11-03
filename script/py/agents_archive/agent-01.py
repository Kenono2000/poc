#!/usr/bin/env python3
"""Stage 01 - basic single-turn LLM chat.

Purpose
-------
The smallest useful LangChain pipeline: format a prompt, send it to a local
Ollama model once, and parse the response into a plain Python string.

Pipeline
--------
ChatPromptTemplate | OllamaLLM | StrOutputParser

What this stage does NOT have
-----------------------------
No conversation memory, no tools, and no agent loop - those arrive in later
stages. Each run answers exactly one question and then exits.

Model configuration
-------------------
The model comes from the ``AGENT_MODEL`` environment variable (default
``gemma4:e2b``) and the endpoint from ``OLLAMA_HOST`` (default
``http://localhost:11434``). Ollama must be running and the model must be
pulled locally. If the ``langchain_ollama`` import fails or the Ollama API is
unreachable, this script prints an actionable message and exits with status 1
instead of raising a bare traceback.

Usage
-----
    python agent-01.py
    python agent-01.py "Why is the sky blue?"

Requires Python 3.11+.
"""

import json
import os
import sys

# ---------------------------------------------------------------------------
# Shared configuration (every stage in this archive uses the same contract).
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "gemma4:e2b"
MODEL_NAME = os.getenv("AGENT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _configure_stdio() -> None:
    """Force UTF-8 console output so non-ASCII model text never crashes Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()

# ---------------------------------------------------------------------------
# Third-party imports, guarded so a missing package is a clear message rather
# than an ImportError traceback ("python agent-01.py" still works as a script).
# ---------------------------------------------------------------------------
try:
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_ollama import OllamaLLM
except ImportError as exc:
    _MISSING = getattr(exc, "name", None) or "a required package"
    sys.stderr.write(
        f"[ERROR] Missing Python package: {_MISSING}\n"
        "        This stage needs langchain-core and langchain-ollama.\n"
        "        Install them with:\n"
        "            python -m pip install langchain-core langchain-ollama\n"
        "        Then start Ollama and pull the model:\n"
        "            ollama serve\n"
        f"            ollama pull {MODEL_NAME}\n"
    )
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# Small helpers shared by the stages.
# ---------------------------------------------------------------------------
def abort(message: str) -> None:
    """Print an actionable error and exit with status 1 (never a bare traceback)."""
    sys.stderr.write(f"[ERROR] {message}\n")
    raise SystemExit(1)


def ensure_ollama_available() -> None:
    """Fail fast, with instructions, if the local Ollama HTTP API is unreachable."""
    from urllib import error, request

    try:
        with request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=3) as response:
            payload = response.read().decode("utf-8", errors="replace")
    except (error.URLError, OSError, ValueError) as exc:
        abort(
            f"Cannot reach Ollama at {OLLAMA_HOST} ({type(exc).__name__}: {exc}).\n"
            "        Start it with: ollama serve\n"
            f"        Pull the model with: ollama pull {MODEL_NAME}\n"
            "        Or set OLLAMA_HOST to a running Ollama endpoint."
        )

    # The tags endpoint is informational: warn (do not fail) about missing models.
    try:
        models = json.loads(payload).get("models", [])
        names = [str(model.get("name", "")) for model in models if isinstance(model, dict)]
    except (ValueError, AttributeError):
        return

    if not names:
        print(f"[WARN] Ollama is running but has no models. Pull one with: ollama pull {MODEL_NAME}")
    elif not any(name == MODEL_NAME or name.startswith(f"{MODEL_NAME}:") for name in names):
        print(f"[WARN] Model '{MODEL_NAME}' is not installed locally (available: {', '.join(names)}).")
        print(f"       Pull it with: ollama pull {MODEL_NAME}")


def build_llm(temperature: float = 0.0):
    """Return the shared Ollama model wrapper configured from the environment."""
    return OllamaLLM(model=MODEL_NAME, base_url=OLLAMA_HOST, temperature=temperature)


def invoke_or_exit(runnable, payload: dict) -> str:
    """Invoke a LangChain chain, converting backend failures into clear guidance."""
    try:
        return runnable.invoke(payload)
    except KeyboardInterrupt:
        raise
    except Exception as exc:  # noqa: BLE001 - demo: turn any backend failure into guidance
        abort(
            f"Model call failed ({type(exc).__name__}: {exc}).\n"
            f"        Check that Ollama is running at {OLLAMA_HOST} and that the\n"
            f"        model '{MODEL_NAME}' is available (ollama pull {MODEL_NAME})."
        )


# ---------------------------------------------------------------------------
# Stage 01 pipeline.
# ---------------------------------------------------------------------------
def main() -> int:
    """Run one prompt/response round-trip against the configured Ollama model."""
    ensure_ollama_available()

    llm = build_llm(temperature=0.2)

    # A chat prompt is a fixed system message plus a user slot filled per run.
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a friendly, concise assistant. Answer in complete sentences."),
            ("human", "{input}"),
        ]
    )

    # The pipe operator composes the three runnables left to right:
    # prompt (formats messages) -> llm (generates) -> parser (string).
    chain = prompt | llm | StrOutputParser()

    # The first CLI argument is the question; fall back to a demo question.
    question = " ".join(sys.argv[1:]).strip() or "Why is the sky blue? Explain in two sentences."

    print(f"Model : {MODEL_NAME}")
    print(f"Ollama: {OLLAMA_HOST}")
    print(f"\nQuestion: {question}\n")

    answer = invoke_or_exit(chain, {"input": question})
    print(f"Answer:\n{answer}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
        raise SystemExit(130) from None
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - last-resort user-friendly failure
        print(f"[ERROR] Unexpected failure ({type(exc).__name__}: {exc}).", file=sys.stderr)
        raise SystemExit(1) from None
