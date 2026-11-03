"""
Run every provider model-availability script and summarise the results.

The individual scripts (``nvidia-models.py``, ``gemini-models.py`` ...) each
call a different provider API and therefore each need their own API key.
This runner checks the required key *before* launching a script and skips it
with a clear reason when the key is absent, so a missing credential produces
one readable "skipped" line instead of a wall of authentication errors.

Configuration
-------------
Provider key mapping (see ``PROVIDER_ENV_KEYS``):

    nvidia-models.py      -> NVIDIA_API_KEY
    gemini-models.py      -> GOOGLE_API_KEY
    openai-models.py      -> OPENAI_API_KEY
    openrouter-models.py  -> OPENROUTER_API_KEY
    serper-models.py      -> SERPER_API_KEY

A ``.env`` file next to this script (or in a parent directory) is loaded
automatically when ``python-dotenv`` is installed, matching what the child
scripts themselves do.

    RUN_ALL_IGNORE_ENV=1  Run scripts even when their API key is missing
                          (useful only for deliberately testing the failure
                          path; the scripts will probably fail fast).

Behaviour
---------
* Scripts run sequentially; each one streams its own output to the console.
* A failing script never stops the run -- every script gets its turn.
* A final table reports status, duration, and a note for every script.
* Exit code is nonzero when any executed script failed or could not be found;
  skipped scripts do not fail the run.

Usage
-----
    python run-all-model-tests.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

try:  # Optional dependency: the provider scripts use it too.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is expected but not required
    pass

SCRIPT_DIR = Path(__file__).resolve().parent

#: Mapping of script name -> environment variable holding its provider key.
PROVIDER_ENV_KEYS: dict[str, str] = {
    "nvidia-models.py": "NVIDIA_API_KEY",
    "gemini-models.py": "GOOGLE_API_KEY",
    "openai-models.py": "OPENAI_API_KEY",
    "openrouter-models.py": "OPENROUTER_API_KEY",
    "serper-models.py": "SERPER_API_KEY",
}

#: Execution order (must stay stable for readable, comparable runs).
SCRIPTS: list[str] = list(PROVIDER_ENV_KEYS)

#: Truthy values accepted for RUN_ALL_IGNORE_ENV.
TRUTHY = {"1", "true", "yes", "on"}


def _configure_stdout() -> None:
    """Force UTF-8 console output so provider output never crashes the runner."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def _ignore_env_gate() -> bool:
    """True when the caller explicitly asked to bypass missing-key skips."""
    return os.getenv("RUN_ALL_IGNORE_ENV", "").strip().lower() in TRUTHY


def _missing_env_key(script_name: str) -> str | None:
    """Return the provider env var name when it is unset/blank, else None."""
    key = PROVIDER_ENV_KEYS.get(script_name)
    if not key:
        return None
    if os.getenv(key, "").strip():
        return None
    return key


def run_script(script_name: str) -> dict[str, object]:
    """Run one provider script and return its result record.

    Record keys: ``script``, ``status`` (PASSED / FAILED / SKIPPED),
    ``duration`` (seconds), ``note``.
    """
    record: dict[str, object] = {
        "script": script_name,
        "status": "SKIPPED",
        "duration": 0.0,
        "note": "",
    }
    script_path = SCRIPT_DIR / script_name

    if not script_path.is_file():
        print(f"[FAIL] Script not found: {script_path}")
        record.update(status="FAILED", note="script not found")
        return record

    missing_key = _missing_env_key(script_name)
    if missing_key and not _ignore_env_gate():
        note = f"missing {missing_key}"
        print(
            f"[SKIP] {script_name} -> {note}. "
            f"Set {missing_key} (or RUN_ALL_IGNORE_ENV=1 to force)."
        )
        record.update(status="SKIPPED", note=note)
        return record

    if missing_key:
        print(
            f"[WARN] {script_name} -> {missing_key} is missing but "
            "RUN_ALL_IGNORE_ENV is set; running anyway."
        )

    print("\n" + "=" * 80)
    print(f" RUNNING: {script_name}")
    print("=" * 80)

    started = time.time()
    try:
        # sys.executable keeps the child on the same interpreter/venv as this
        # runner; output is inherited so scripts can stream their progress.
        completed = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(SCRIPT_DIR),
            check=False,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        elapsed = time.time() - started
        print(f"[FAIL] Could not execute {script_name}: {exc}")
        record.update(status="FAILED", duration=elapsed, note=f"launch failed: {exc}")
        return record

    elapsed = time.time() - started
    if completed.returncode == 0:
        record.update(status="PASSED", duration=elapsed, note="")
    else:
        note = f"exit code {completed.returncode}"
        print(f"\n[WARN] {script_name} exited with code {completed.returncode}")
        record.update(status="FAILED", duration=elapsed, note=note)
    return record


def _print_summary(results: list[dict[str, object]], total_elapsed: float) -> None:
    """Print the final per-script status table and totals."""
    header = f"{'STATUS':<8} | {'TIME':<8} | {'SCRIPT':<24} | {'NOTE'}"
    print("\n" + "=" * 80)
    print(" SUMMARY")
    print("=" * 80)
    print(header)
    print("-" * len(header))
    for record in results:
        print(
            f"{str(record['status']):<8} | "
            f"{float(record['duration']):>6.2f}s | "
            f"{str(record['script']):<24} | {record['note']}"
        )
    print("-" * len(header))

    passed = sum(1 for record in results if record["status"] == "PASSED")
    failed = sum(1 for record in results if record["status"] == "FAILED")
    skipped = sum(1 for record in results if record["status"] == "SKIPPED")
    print(
        f"TOTALS: {passed} passed, {failed} failed, {skipped} skipped "
        f"| total duration {total_elapsed:.2f}s"
    )
    print("=" * 80)


def main() -> int:
    """Run all provider scripts; return 1 when any executed script failed."""
    _configure_stdout()
    print("Starting Bulk Model Availability Test...")
    print(f"Script directory: {SCRIPT_DIR}")
    print(f"Found {len(SCRIPTS)} test scripts to execute.")

    overall_start = time.time()
    results: list[dict[str, object]] = []
    for script_name in SCRIPTS:
        results.append(run_script(script_name))
    total_elapsed = time.time() - overall_start

    _print_summary(results, total_elapsed)

    failed = [record for record in results if record["status"] == "FAILED"]
    if failed:
        print(f"[ERROR] {len(failed)} script(s) failed: " + ", ".join(
            str(record["script"]) for record in failed
        ))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
