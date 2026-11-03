#!/usr/bin/env python3
"""Stage 05 - multi-turn conversational agent with scratchpad reasoning.

Purpose
-------
Combine the two previous ideas: memory (stage 02) and tool use (stage 03),
but make the reasoning visible and per-turn. For every user message the agent
keeps a scratchpad of ``Thought`` / ``Action`` / ``Observation`` lines, fills
it one step at a time by calling the model, executes the requested tool, and
only records the final answer in conversation memory once the turn finishes.

Why the scratchpad matters
--------------------------
The scratchpad is re-sent on every step of the turn, so the model can see what
it has already tried. The conversation history is re-sent on every step too,
so references such as "that budget" resolve against earlier turns. This is a
hand-rolled ReAct loop: explicit, inspectable, and easy to debug.

Tools
-----
calculator
    Shared AST-based ``safe_calculate`` from ``libs/py`` (no ``eval``), loaded
    via a path derived from ``__file__`` so the script runs from any cwd.
search
    Tiny bundled offline knowledge base - no network access.

Model configuration
-------------------
``AGENT_MODEL`` selects the model (default ``gemma4:e2b``) and ``OLLAMA_HOST``
the endpoint (default ``http://localhost:11434``). Missing packages and an
unreachable Ollama server are reported clearly and exit with status 1.

Usage
-----
    python agent-05.py

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
MAX_STEPS = 4


def _configure_stdio() -> None:
    """Force UTF-8 console output so non-ASCII model text never crashes Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()

# ---------------------------------------------------------------------------
# Third-party imports, guarded so a missing package is a clear message rather
# than an ImportError traceback ("python agent-05.py" still works as a script).
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
# Stage 05: tools (same shared helper as stage 03) and local knowledge base.
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


_LOCAL_KNOWLEDGE = {
    "ai agent": (
        "An AI agent is a program that uses a language model to reason about a goal and "
        "take actions - such as calling tools - until the goal is met."
    ),
    "budget planning": (
        "A practical budget keeps a contingency of roughly 10-20% and tracks committed "
        "spending against the total before new costs are approved."
    ),
    "ollama": (
        "Ollama runs open language models locally and exposes an HTTP API at "
        "http://localhost:11434 by default."
    ),
    "langchain": (
        "LangChain is a Python framework for composing prompts, models, tools, output "
        "parsers, and agent runtimes into pipelines."
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


TOOLS = {
    "calculator": calculator_tool,
    "search": search_tool,
}

SYSTEM_PROMPT = (
    "You are a conversational reasoning agent.\n"
    "You can use two tools:\n"
    "- calculator: evaluates an arithmetic expression (for example '0.15 * 1200').\n"
    "- search: searches a small offline knowledge base by topic.\n\n"
    "Think before you act. On each step reply using exactly one of these shapes:\n"
    "  Thought: <your reasoning>\n"
    "  Action: <calculator or search>\n"
    "  Action Input: <tool input>\n"
    "or, when you can answer:\n"
    "  Thought: I now know the final answer\n"
    "  Final Answer: <answer>\n\n"
    "Use the conversation history to resolve references such as 'that budget'. "
    "Never invent tool results; wait for the Observation that follows your Action."
)

HUMAN_PROMPT = (
    "Answer the latest user question using the conversation history.\n"
    "Question: {question}\n\n"
    "Scratchpad for this turn:\n{scratchpad}\n\n"
    "Write only your next Thought plus either an Action or the Final Answer."
)


def build_chain():
    """Build the prompt -> model -> string chain used for every reasoning step."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", HUMAN_PROMPT),
        ]
    )
    return prompt | build_llm(temperature=0.0) | StrOutputParser()


class ChatMemory:
    """In-process conversation buffer shared across turns of one process run."""

    def __init__(self) -> None:
        self._messages: list = []

    def messages(self) -> list:
        """Return a copy of the stored HumanMessage/AIMessage objects."""
        return list(self._messages)

    def add_turn(self, user_text: str, assistant_text: str) -> None:
        """Append one completed exchange to the conversation history."""
        self._messages.append(HumanMessage(content=user_text))
        self._messages.append(AIMessage(content=assistant_text))

    def __len__(self) -> int:
        return len(self._messages)


def parse_response(text: str) -> tuple[str | None, str | None, str | None, list[str]]:
    """Split a ReAct-style reply into (final_answer, action, action_input, thoughts)."""
    final_answer: str | None = None
    action: str | None = None
    action_input: str | None = None
    thoughts: list[str] = []
    lines = text.splitlines()

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        lower = stripped.lower()

        if lower.startswith("thought:"):
            thoughts.append(stripped)
        elif lower.startswith("final answer:"):
            first_line = stripped.split(":", 1)[1].strip()
            remainder = [extra.strip() for extra in lines[index + 1:] if extra.strip()]
            final_answer = " ".join([first_line, *remainder]).strip()
        elif lower.startswith("action:"):
            action = stripped.split(":", 1)[1].strip().strip("`'\"").lower()
            for following in lines[index + 1:index + 3]:
                following = following.strip()
                if following.lower().startswith("action input:"):
                    action_input = following.split(":", 1)[1].strip().strip("`'\"")
                    break

    return final_answer, action, action_input, thoughts


def run_turn(chain, memory: ChatMemory, user_text: str, turn_number: int) -> str:
    """Run one user turn: scratchpad loop -> answer -> store the exchange in memory."""
    print(f"\n{'=' * 70}\nTurn {turn_number}\nUser: {user_text}\n{'=' * 70}")
    scratchpad_lines: list[str] = []
    answer: str | None = None
    last_observation: str | None = None

    for step in range(1, MAX_STEPS + 1):
        scratchpad = "\n".join(scratchpad_lines) if scratchpad_lines else "(empty)"
        raw = invoke_or_exit(
            chain,
            {"question": user_text, "scratchpad": scratchpad, "history": memory.messages()},
        )
        final_answer, action, action_input, thoughts = parse_response(raw)
        scratchpad_lines.extend(thoughts)

        if final_answer:
            answer = final_answer
            scratchpad_lines.append(f"Final Answer: {answer}")
            break

        if action is None:
            print("[WARN] Reply contained neither a valid Action nor a Final Answer; using it as the answer.")
            answer = raw.strip()
            scratchpad_lines.append(raw.strip())
            break

        tool = TOOLS.get(action)
        if tool is None:
            observation = f"Error: unknown tool {action!r}. Available: {', '.join(TOOLS)}."
        else:
            try:
                observation = tool(action_input or "")
            except Exception as exc:  # noqa: BLE001 - tool errors are shown to the model
                observation = f"Error: {type(exc).__name__}: {exc}"

        last_observation = observation
        scratchpad_lines.append(f"Action: {action}")
        scratchpad_lines.append(f"Action Input: {action_input}")
        scratchpad_lines.append(f"Observation: {observation}")
        print(f"[step {step}] {action}({action_input!r}) -> {observation}")

    if answer is None:
        print(f"[WARN] Reached the {MAX_STEPS}-step limit without a Final Answer.")
        answer = last_observation or "I could not complete this turn with the available tools."
        print(f"[fallback] {answer}")

    print("\nReasoning scratchpad:")
    for line in scratchpad_lines:
        print(f"  {line}")

    memory.add_turn(user_text, answer)
    print(f"\nAssistant: {answer}")
    print(f"[memory] {len(memory)} messages retained for the next turn")
    return answer


def main() -> int:
    """Run a three-turn conversation that mixes memory, reasoning and tools."""
    ensure_ollama_available()

    print(f"Model : {MODEL_NAME}")
    print("Stage : multi-turn conversation + scratchpad reasoning\n")

    chain = build_chain()
    memory = ChatMemory()
    scripted_turns = [
        "My name is Sam. I'm planning a workshop with a total budget of $1,200.",
        "If 15% of that budget goes to materials, how much money is left? Use the calculator.",
        "Search the knowledge base for 'budget planning', then remind me of my name and my remaining budget.",
    ]

    for turn_number, user_text in enumerate(scripted_turns, start=1):
        run_turn(chain, memory, user_text, turn_number)

    print("\n[done] Each turn reused the growing history and reasoned on its own scratchpad.")
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
