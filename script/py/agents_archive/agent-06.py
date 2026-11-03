#!/usr/bin/env python3
"""Stage 06 - multi-agent supervisor collaboration.

Architecture
------------
A supervisor model coordinates two workers:

    supervisor  ->  researcher worker  (offline knowledge + LLM summary)
                ->  calculator worker (deterministic safe_calculate)

On each step the supervisor sees the task plus the transcript of work already
delegated, then replies in exactly one of three forms::

    Delegate: researcher | <question>
    Delegate: calculator | <arithmetic expression>
    Finish: <final answer>

The runner parses that reply, executes the named worker, appends the result to
the transcript, and loops (bounded by MAX_DELEGATIONS). If the supervisor
stops following the protocol or runs out of steps, a separate synthesis chain
writes the final answer from the transcript. The calculator worker is
deterministic, so arithmetic cannot drift between supervisor and worker.

Model configuration
-------------------
``AGENT_MODEL`` selects the model (default ``gemma4:e2b``) and ``OLLAMA_HOST``
the endpoint (default ``http://localhost:11434``). Missing packages and an
unreachable Ollama server are reported clearly and exit with status 1.

Usage
-----
    python agent-06.py

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
MAX_DELEGATIONS = 4


def _configure_stdio() -> None:
    """Force UTF-8 console output so non-ASCII model text never crashes Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


_configure_stdio()

# ---------------------------------------------------------------------------
# Third-party imports, guarded so a missing package is a clear message rather
# than an ImportError traceback ("python agent-06.py" still works as a script).
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
# Stage 06: worker knowledge + prompts.
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
}


def search_knowledge(query: str) -> str:
    """Search the bundled offline knowledge base for the researcher worker."""
    tokens = {token for token in re.split(r"[^a-z0-9]+", query.lower()) if len(token) > 1}
    scored: list[tuple[int, str, str]] = []
    for topic, note in _LOCAL_KNOWLEDGE.items():
        overlap = len(tokens & set(topic.split()))
        if overlap:
            scored.append((overlap, topic, note))

    if not scored:
        return f"No local knowledge matched {query!r}. Available topics: {', '.join(_LOCAL_KNOWLEDGE)}."

    scored.sort(key=lambda item: (-item[0], item[1]))
    return "\n\n".join(f"{topic}: {note}" for _, topic, note in scored[:2])


SUPERVISOR_SYSTEM_PROMPT = (
    "You are the supervisor of a two-worker team.\n"
    "Workers:\n"
    "- researcher: answers factual questions from a small offline knowledge base.\n"
    "- calculator: evaluates a single arithmetic expression safely.\n\n"
    "Delegate work one step at a time. Reply with exactly one of these formats:\n"
    "1) Delegate: researcher | <question>\n"
    "2) Delegate: calculator | <arithmetic expression>\n"
    "3) Finish: <final answer for the user>\n\n"
    "Rules: use the calculator for arithmetic instead of mental math; base the final "
    "answer on the worker results in the transcript; do not invent worker output."
)

SUPERVISOR_HUMAN_PROMPT = (
    "Task: {task}\n\n"
    "Team transcript so far:\n{transcript}\n\n"
    "What is your next action?"
)

RESEARCHER_SYSTEM_PROMPT = (
    "You are the researcher worker on a small team.\n"
    "Answer the question using ONLY the retrieved notes below. "
    "If the notes do not cover it, say so plainly. Keep the answer to 2-4 sentences."
)

RESEARCHER_HUMAN_PROMPT = "Question: {question}\n\nRetrieved notes:\n{notes}"

SYNTHESIS_SYSTEM_PROMPT = (
    "You are the supervisor. Write the final answer to the user's task using only the "
    "worker results in the transcript. Do not delegate or mention internal protocols."
)

SYNTHESIS_HUMAN_PROMPT = "Task: {task}\n\nWorker transcript:\n{transcript}\n\nFinal answer:"


def parse_supervisor_reply(text: str):
    """Parse a supervisor reply into ("finish", answer) or ("delegate", worker, input)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        lower = line.lower()

        if lower.startswith("finish:"):
            first_line = line.split(":", 1)[1].strip()
            remainder = " ".join(lines[index + 1:])
            return ("finish", " ".join(part for part in (first_line, remainder) if part).strip())

        if lower.startswith("delegate:"):
            body = line.split(":", 1)[1].strip()
            if "|" not in body:
                continue
            worker, worker_input = body.split("|", 1)
            worker = worker.strip().strip("`'\"").lower()
            worker_input = worker_input.strip().strip("`'\"")
            if worker and worker_input:
                return ("delegate", worker, worker_input)

    return None


class SupervisorTeam:
    """Supervisor model plus researcher/calculator workers sharing a transcript."""

    def __init__(self) -> None:
        llm = build_llm(temperature=0.0)

        self.supervisor_chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", SUPERVISOR_SYSTEM_PROMPT),
                    ("human", SUPERVISOR_HUMAN_PROMPT),
                ]
            )
            | llm
            | StrOutputParser()
        )
        self.researcher_chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", RESEARCHER_SYSTEM_PROMPT),
                    ("human", RESEARCHER_HUMAN_PROMPT),
                ]
            )
            | llm
            | StrOutputParser()
        )
        self.synthesis_chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", SYNTHESIS_SYSTEM_PROMPT),
                    ("human", SYNTHESIS_HUMAN_PROMPT),
                ]
            )
            | llm
            | StrOutputParser()
        )

    def run_worker(self, worker_name: str, worker_input: str) -> str:
        """Execute one worker and return its observation as text."""
        if worker_name == "calculator":
            # Deterministic: the calculator never hallucinates a result.
            result = safe_calculate(worker_input)
            if result.startswith("Error"):
                return result
            return f"{worker_input} = {result}"

        if worker_name == "researcher":
            notes = search_knowledge(worker_input)
            return invoke_or_exit(
                self.researcher_chain,
                {"question": worker_input, "notes": notes},
            )

        return (
            f"Error: unknown worker {worker_name!r}. "
            "Available workers: researcher, calculator."
        )

    @staticmethod
    def _print_delegation_summary(delegations: list[tuple[str, str, str]]) -> None:
        print("\nDelegation summary:")
        if not delegations:
            print("  (no worker was delegated; the supervisor answered directly)")
            return
        for index, (worker, worker_input, result) in enumerate(delegations, start=1):
            brief = " ".join(result.split())
            if len(brief) > 100:
                brief = brief[:97] + "..."
            print(f"  {index}. {worker}({worker_input!r}) -> {brief}")

    def run(self, task: str) -> str:
        """Run the supervisor loop and return the final answer."""
        print(f"\nTask: {task}\n")
        transcript: list[str] = []
        delegations: list[tuple[str, str, str]] = []
        final_answer: str | None = None

        for step in range(1, MAX_DELEGATIONS + 1):
            transcript_text = "\n".join(transcript) if transcript else "(no work delegated yet)"
            raw = invoke_or_exit(
                self.supervisor_chain,
                {"task": task, "transcript": transcript_text},
            )
            print(f"[supervisor step {step}] {raw.strip()}")
            decision = parse_supervisor_reply(raw)

            if decision is None:
                print("[WARN] Supervisor reply did not follow the protocol; using synthesis fallback.")
                break

            if decision[0] == "finish":
                final_answer = decision[1]
                break

            _, worker_name, worker_input = decision
            print(f"[delegate -> {worker_name}] {worker_input}")
            worker_result = self.run_worker(worker_name, worker_input)
            delegations.append((worker_name, worker_input, worker_result))
            print(f"[worker result]\n{worker_result}")
            transcript.append(
                f"[{len(delegations)}] Delegate to {worker_name}\n"
                f"Input: {worker_input}\n"
                f"Result: {worker_result}"
            )
        else:
            print(f"[WARN] Reached the {MAX_DELEGATIONS}-delegation limit without Finish.")

        if final_answer is None:
            transcript_text = "\n".join(transcript) if transcript else "(no worker results)"
            final_answer = invoke_or_exit(
                self.synthesis_chain,
                {"task": task, "transcript": transcript_text},
            ).strip()

        self._print_delegation_summary(delegations)
        print(f"\n{'=' * 70}\nFinal answer:\n{final_answer}\n{'=' * 70}")
        return final_answer


def main() -> int:
    """Run a task that needs both a research worker and a calculator worker."""
    ensure_ollama_available()

    print(f"Model : {MODEL_NAME}")
    print("Stage : multi-agent supervisor collaboration\n")

    team = SupervisorTeam()
    task = (
        "Plan a one-day AI workshop: explain what an AI agent is, and calculate the total "
        "cost for 24 attendees at $85 per attendee."
    )
    final_answer = team.run(task)
    return 0 if final_answer.strip() else 1


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
