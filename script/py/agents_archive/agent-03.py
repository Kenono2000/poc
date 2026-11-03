#!/usr/bin/env python3
"""Stage 03 - dynamic tool invocation (calculator + local search).

Purpose
-------
Teach the model to act instead of only talk. The model is given a short tool
menu and replies with a structured tool request; this script parses that
request, executes the matching Python function, feeds the observation back to
the model, and repeats until the model produces a Final Answer.

Tools
-----
calculator
    Reuses the shared, AST-based ``safe_calculate`` helper from ``libs/py``
    (no ``eval``). The import path is resolved from this file's location, so
    the script runs from any working directory.
search
    Searches a tiny bundled knowledge base entirely offline (no network).

Pipeline
--------
ChatPromptTemplate | OllamaLLM | StrOutputParser, invoked in a bounded loop
(MAX_STEPS) with the accumulated Action/Observation scratchpad as extra input.

Model configuration
-------------------
``AGENT_MODEL`` selects the model (default ``gemma4:e2b``) and ``OLLAMA_HOST``
the endpoint (default ``http://localhost:11434``). Missing packages and an
unreachable Ollama server are reported clearly and exit with status 1.

Usage
-----
    python agent-03.py

Requires Python 3.11+.
"""

import json
import os
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Shared configuration (every stage in this archive uses the same contract).
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "gemma4:e2b"
MODEL_NAME = os.getenv("AGENT_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
LIBS_DIR = Path(__file__).resolve().parents[3] / "libs" / "py"
MAX_STEPS = 3


def _configure_stdio() -> None:
    """Force UTF-8 console output so non-ASCII model text never crashes Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()

# ---------------------------------------------------------------------------
# Third-party imports, guarded so a missing package is a clear message rather
# than an ImportError traceback ("python agent-03.py" still works as a script).
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
# Stage 03: tools. safe_calculate comes from the shared library, imported via
# a path derived from __file__ so the working directory never matters.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(LIBS_DIR))
try:
    from utilities import safe_calculate
except Exception as exc:  # noqa: BLE001 - report any dependency problem as guidance
    abort(
        f"Could not import safe_calculate from {LIBS_DIR} "
        f"({type(exc).__name__}: {exc}).\n"
        "        Install the shared library dependencies, for example:\n"
        "            python -m pip install numpy psycopg2-binary python-dotenv "
        "langchain-community langchain-openai langchain-text-splitters"
    )


def calculator_tool(expression: str) -> str:
    """Evaluate an arithmetic expression with the shared safe AST calculator."""
    return safe_calculate(expression)


# The offline knowledge base is intentionally tiny so the demo needs no network.
_LOCAL_KNOWLEDGE = {
    "ai agent": (
        "An AI agent is a program that uses a language model to reason about a goal and "
        "take actions - such as calling tools - until the goal is met."
    ),
    "langchain": (
        "LangChain is a Python framework for composing prompts, models, tools, output "
        "parsers, and agent runtimes into pipelines."
    ),
    "ollama": (
        "Ollama runs open language models locally and exposes an HTTP API at "
        "http://localhost:11434 by default."
    ),
    "calculator": (
        "The calculator tool safely evaluates arithmetic containing +, -, *, /, ** "
        "and parentheses."
    ),
}


def search_tool(query: str) -> str:
    """Search the bundled offline knowledge base (never touches the network)."""
    tokens = {token for token in re.split(r"[^a-z0-9]+", query.lower()) if len(token) > 1}
    scored: list[tuple[int, str, str]] = []
    for topic, note in _LOCAL_KNOWLEDGE.items():
        overlap = len(tokens & set(topic.split()))
        if overlap:
            scored.append((overlap, topic, note))

    if not scored:
        return (
            f"No local knowledge matched {query!r}. "
            f"Available topics: {', '.join(_LOCAL_KNOWLEDGE)}."
        )

    scored.sort(key=lambda item: (-item[0], item[1]))
    return "\n".join(f"{topic}: {note}" for _, topic, note in scored[:2])


# Tool registry: the model names a tool; the runner looks up the callable.
TOOLS = {
    "calculator": calculator_tool,
    "search": search_tool,
}

TOOL_DESCRIPTIONS = (
    "calculator - evaluates an arithmetic expression. Input example: '128 * 7 + 42'.\n"
    "search - searches a small offline knowledge base. Input example: 'AI agent'."
)

SYSTEM_PROMPT = (
    "You are a tool-using assistant.\n"
    "Available tools:\n"
    f"{TOOL_DESCRIPTIONS}\n\n"
    "Reply with exactly ONE of these two formats:\n"
    "1) To call a tool:\n"
    "Action: <calculator or search>\n"
    "Action Input: <expression or query>\n"
    "2) When you can answer:\n"
    "Final Answer: <your answer>\n\n"
    "Rules: use the calculator for arithmetic instead of doing mental math; use search for "
    "facts about AI agents, LangChain, Ollama, or the calculator; never invent tool output."
)

HUMAN_PROMPT = (
    "Question: {question}\n\n"
    "Tool calls and observations so far:\n{scratchpad}\n\n"
    "What is your next step?"
)

# Case-insensitive "Final Answer:" match; DOTALL because the answer may span lines.
FINAL_ANSWER_RE = re.compile(r"final\s+answer\s*:\s*(.+)", re.IGNORECASE | re.DOTALL)


def build_chain():
    """Build the prompt -> model -> string chain used for every reasoning step."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    )
    return prompt | build_llm(temperature=0.0) | StrOutputParser()


def parse_final_answer(text: str) -> str | None:
    """Extract the text after 'Final Answer:' (case-insensitive), if present."""
    match = FINAL_ANSWER_RE.search(text)
    return match.group(1).strip() if match else None


def parse_action(text: str) -> tuple[str, str] | None:
    """Extract a (tool_name, tool_input) pair from an 'Action:' reply, if present."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if not line.lower().startswith("action:"):
            continue
        tool_name = line.split(":", 1)[1].strip().strip("`'\"").lower()
        if not tool_name:
            continue
        # The input normally follows on the next line (allow one blank/noisy line).
        for candidate in lines[index + 1:index + 3]:
            if candidate.lower().startswith("action input:"):
                tool_input = candidate.split(":", 1)[1].strip().strip("`'\"")
                if tool_input:
                    return tool_name, tool_input
    return None


def run_agent(chain, question: str) -> str:
    """Answer one question with a bounded thought/tool loop."""
    print(f"\n{'=' * 70}\nQuestion: {question}\n{'=' * 70}")
    scratchpad = "(nothing yet)"
    observations: list[str] = []

    for step in range(1, MAX_STEPS + 1):
        raw = invoke_or_exit(chain, {"question": question, "scratchpad": scratchpad})
        print(f"\n[model step {step}]\n{raw.strip()}")

        final_answer = parse_final_answer(raw)
        if final_answer:
            print(f"\n[final answer] {final_answer}")
            return final_answer

        action = parse_action(raw)
        if action is None:
            print("\n[WARN] Model reply matched neither format; using it as the final answer.")
            return raw.strip()

        tool_name, tool_input = action
        tool = TOOLS.get(tool_name)
        if tool is None:
            observation = f"Error: unknown tool {tool_name!r}. Available: {', '.join(TOOLS)}."
        else:
            try:
                observation = tool(tool_input)
            except Exception as exc:  # noqa: BLE001 - tool errors go back to the model
                observation = f"Error: {type(exc).__name__}: {exc}"

        observations.append(observation)
        print(f"[tool] {tool_name}({tool_input!r}) -> {observation}")
        scratchpad = (
            f"{scratchpad}\n"
            f"Action: {tool_name}\n"
            f"Action Input: {tool_input}\n"
            f"Observation: {observation}"
        )

    print(f"\n[WARN] Reached the {MAX_STEPS}-step limit without a Final Answer.")
    fallback = observations[-1] if observations else "(no tool observations)"
    print(f"[fallback] {fallback}")
    return fallback


def main() -> int:
    """Run two demo questions so both tools are exercised."""
    ensure_ollama_available()

    print(f"Model : {MODEL_NAME}")
    print(f"Tools : {', '.join(TOOLS)}\n")

    chain = build_chain()
    demo_questions = [
        "What is 128 * 7 + 42? Use the calculator.",
        "Search the knowledge base for 'AI agent' and explain the result in one sentence.",
    ]
    for question in demo_questions:
        run_agent(chain, question)

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
