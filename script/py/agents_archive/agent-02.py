#!/usr/bin/env python3
"""Stage 02 - prompt formatting plus conversational memory.

Purpose
-------
Build on stage 01 by giving the chain memory: every invocation receives the
earlier turns as LangChain chat messages, so follow-up questions can refer to
what was said before ("What is my name?", "Summarise our conversation").

Pipeline
--------
ChatPromptTemplate (system + MessagesPlaceholder("history") + human)
    | OllamaLLM
    | StrOutputParser

Memory model
------------
``ChatMemory`` is a minimal in-process buffer of HumanMessage/AIMessage
objects. It is deliberately not a database: the point of this stage is that
each *chain invocation* gets the full history (LangChain's recommended way to
do conversation memory without a retrieval layer). The transcript therefore
survives for the life of this process only.

Model configuration
-------------------
``AGENT_MODEL`` selects the model (default ``gemma4:e2b``) and ``OLLAMA_HOST``
the endpoint (default ``http://localhost:11434``). A missing
``langchain_ollama`` package or an unreachable Ollama server produces an
actionable message and exit status 1 - never a bare traceback.

Usage
-----
    python agent-02.py

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
# than an ImportError traceback ("python agent-02.py" still works as a script).
# ---------------------------------------------------------------------------
try:
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
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
# Stage 02: conversation memory.
# ---------------------------------------------------------------------------
class ChatMemory:
    """In-process buffer of the conversation as LangChain message objects.

    History is retained only for this process, but every chain invocation sees
    it, which is all the "multi-turn" stage needs. Callers receive copies so
    the buffer cannot be mutated from outside.
    """

    def __init__(self) -> None:
        self._messages: list = []

    def messages(self) -> list:
        """Return a shallow copy of the stored HumanMessage/AIMessage objects."""
        return list(self._messages)

    def add_turn(self, user_text: str, assistant_text: str) -> None:
        """Append one completed user/assistant exchange to the history."""
        self._messages.append(HumanMessage(content=user_text))
        self._messages.append(AIMessage(content=assistant_text))

    def __len__(self) -> int:
        return len(self._messages)


def main() -> int:
    """Run a short scripted conversation where each turn reuses the history."""
    ensure_ollama_available()

    llm = build_llm(temperature=0.0)

    # MessagesPlaceholder inserts the memory buffer where the model expects it.
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a helpful assistant. Use the earlier conversation when it is "
                "relevant, and never claim to remember things that were not said.",
            ),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ]
    )
    chain = prompt | llm | StrOutputParser()

    memory = ChatMemory()
    # Turn 2 only works because turn 1 is in memory; turn 3 summarises both.
    scripted_turns = [
        "Hi! My name is Alex and I'm learning about AI agents.",
        "What is my name, and what topic am I learning about?",
        "Summarise our conversation so far in one sentence.",
    ]

    print(f"Model : {MODEL_NAME}\n")

    for turn_number, user_text in enumerate(scripted_turns, start=1):
        print(f"--- Turn {turn_number} ---")
        print(f"User      : {user_text}")
        answer = invoke_or_exit(chain, {"input": user_text, "history": memory.messages()})
        print(f"Assistant : {answer}")
        memory.add_turn(user_text, answer)
        print(f"[memory] {len(memory)} messages retained for the next turn\n")

    print("[done] Every turn was answered with the conversation history included in the prompt.")
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
