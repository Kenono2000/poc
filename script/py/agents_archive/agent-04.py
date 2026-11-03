#!/usr/bin/env python3
"""Stage 04 - structured JSON output parsing.

Purpose
-------
Ask the model for a machine-readable object instead of free prose, then parse
it defensively: strip markdown fences, locate the JSON object inside any
surrounding chatter, validate the expected fields and their types, and make
exactly one repair attempt if the first reply is malformed. If the repair also
fails, print a clear diagnostic and exit with status 1 - no traceback.

Expected schema
---------------
````json
{
  "topic": "short topic label",
  "summary": "one or two informative sentences",
  "confidence": 0.85,
  "keywords": ["keyword one", "keyword two"]
}
````

Pipeline
--------
ChatPromptTemplate | OllamaLLM | StrOutputParser, plus a deterministic
extract -> json.loads -> validate post-processing layer written in plain
Python. No Pydantic or other extra dependency is required.

Model configuration
-------------------
``AGENT_MODEL`` selects the model (default ``gemma4:e2b``) and ``OLLAMA_HOST``
the endpoint (default ``http://localhost:11434``). Missing packages and an
unreachable Ollama server are reported clearly and exit with status 1.

Usage
-----
    python agent-04.py

Requires Python 3.11+.
"""

import json
import os
import re
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
# than an ImportError traceback ("python agent-04.py" still works as a script).
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
# Stage 04: schema, prompts and defensive parsing.
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = ("topic", "summary", "confidence", "keywords")

# Passed to the prompt as a *variable* so its JSON braces are not interpreted
# as ChatPromptTemplate placeholders.
SCHEMA_EXAMPLE = json.dumps(
    {
        "topic": "short topic label",
        "summary": "one or two informative sentences",
        "confidence": 0.85,
        "keywords": ["keyword one", "keyword two"],
    },
    indent=2,
)

SYSTEM_PROMPT = (
    "You convert a short piece of text into one compact JSON object.\n"
    "Return ONLY the JSON object - no prose, no markdown fences, no comments.\n"
    "Required fields:\n"
    "- topic: string, a short topic label\n"
    "- summary: string, one or two informative sentences\n"
    "- confidence: number between 0 and 1\n"
    "- keywords: array of two to five short strings\n"
    "Follow this shape (the values are examples):\n{schema_example}"
)

HUMAN_PROMPT = "Analyse this text and return the JSON object:\n{input_text}"

REPAIR_SYSTEM_PROMPT = (
    "You repair malformed JSON.\n"
    "Return ONLY a corrected JSON object with these fields: "
    "topic (string), summary (string), confidence (number between 0 and 1), "
    "keywords (array of two to five strings).\n"
    "No markdown fences and no commentary."
)

REPAIR_HUMAN_PROMPT = (
    "The previous reply was invalid.\n"
    "Problems:\n{problems}\n\n"
    "Previous reply:\n{bad_output}\n\n"
    "Return the corrected JSON object only."
)

# Matches a fenced block such as ```json ... ``` or ``` ... ``` (case-insensitive).
FENCED_BLOCK_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def build_chains():
    """Return the (primary, repair) prompt|model|parser chains."""
    llm = build_llm(temperature=0.0)

    primary_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", HUMAN_PROMPT),
        ]
    )
    repair_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", REPAIR_SYSTEM_PROMPT),
            ("human", REPAIR_HUMAN_PROMPT),
        ]
    )
    return (
        primary_prompt | llm | StrOutputParser(),
        repair_prompt | llm | StrOutputParser(),
    )


def extract_json_object(raw: str) -> dict:
    """Find the first JSON object in model output, tolerating fences and prose.

    Candidates are tried in order: the whole reply, each fenced code block, and
    the substring from the first "{" to the last "}". The first candidate that
    ``json.loads`` accepts as an object wins.
    """
    candidates: list[str] = []
    stripped = raw.strip()
    if stripped:
        candidates.append(stripped)

    for match in FENCED_BLOCK_RE.finditer(raw):
        block = match.group(1).strip()
        if block:
            candidates.append(block)

    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        candidates.append(raw[start:end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("no JSON object could be parsed from the model output")


def validate_payload(payload: dict) -> list[str]:
    """Return a list of human-readable schema problems; an empty list means valid."""
    problems: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in payload:
            problems.append(f"missing required field '{field}'")

    topic = payload.get("topic")
    if "topic" in payload and (not isinstance(topic, str) or not topic.strip()):
        problems.append("'topic' must be a non-empty string")

    summary = payload.get("summary")
    if "summary" in payload and (not isinstance(summary, str) or not summary.strip()):
        problems.append("'summary' must be a non-empty string")

    confidence = payload.get("confidence")
    if "confidence" in payload:
        # bool is a subclass of int, so reject it explicitly.
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            problems.append("'confidence' must be a number between 0 and 1")
        elif not 0.0 <= float(confidence) <= 1.0:
            problems.append(f"'confidence' must be between 0 and 1 (got {confidence!r})")

    keywords = payload.get("keywords")
    if "keywords" in payload:
        if not isinstance(keywords, list) or not all(
            isinstance(item, str) and item.strip() for item in keywords
        ):
            problems.append("'keywords' must be an array of non-empty strings")
        elif not 2 <= len(keywords) <= 5:
            problems.append(f"'keywords' should contain 2-5 entries (got {len(keywords)})")

    extra = sorted(set(payload) - set(REQUIRED_FIELDS))
    if extra:
        print(f"[INFO] Ignoring extra field(s) returned by the model: {', '.join(extra)}")

    return problems


def parse_and_validate(raw: str) -> tuple[dict | None, list[str]]:
    """Extract and validate an object from raw model text."""
    try:
        payload = extract_json_object(raw)
    except ValueError as exc:
        return None, [str(exc)]
    return payload, validate_payload(payload)


def request_structured(primary_chain, repair_chain, text: str) -> dict | None:
    """Obtain a validated object, allowing exactly one model-driven repair."""
    raw = invoke_or_exit(primary_chain, {"input_text": text, "schema_example": SCHEMA_EXAMPLE})
    print(f"\n[raw model reply - first call]\n{raw.strip()}\n")

    payload, problems = parse_and_validate(raw)
    if payload is not None and not problems:
        return payload

    print("[repair] First reply was not valid structured output:")
    for problem in problems:
        print(f"  - {problem}")

    repaired_raw = invoke_or_exit(
        repair_chain,
        {
            "bad_output": raw,
            "problems": "\n".join(f"- {problem}" for problem in problems),
        },
    )
    print(f"\n[raw model reply - repair attempt]\n{repaired_raw.strip()}\n")

    payload, problems = parse_and_validate(repaired_raw)
    if payload is not None and not problems:
        print("[repair] The repaired reply is valid.")
        return payload

    print("[ERROR] Could not obtain valid structured output after one repair attempt:", file=sys.stderr)
    for problem in problems:
        print(f"  - {problem}", file=sys.stderr)
    return None


def main() -> int:
    """Ask for structured JSON about a short passage, then validate and print it."""
    ensure_ollama_available()

    print(f"Model : {MODEL_NAME}")
    print("Stage : structured JSON output parsing\n")

    input_text = (
        "LangChain is a framework for building applications with large language models. "
        "It provides prompt templates, output parsers, tool calling, and agent runtimes. "
        "Ollama runs open models locally, so a LangChain pipeline can work without a cloud API key."
    )
    print(f"Input text:\n{input_text}\n")

    primary_chain, repair_chain = build_chains()
    payload = request_structured(primary_chain, repair_chain, input_text)

    if payload is None:
        print("\n[FAIL] Structured JSON stage did not produce a validated object.", file=sys.stderr)
        return 1

    print("Validated JSON:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print("\nField validation:")
    for field in REQUIRED_FIELDS:
        print(f"  [OK] {field}: {type(payload[field]).__name__}")
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
