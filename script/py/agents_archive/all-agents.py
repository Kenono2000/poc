#!/usr/bin/env python3
"""Stage runner - execute every LangChain agent stage in order and summarise.

Behaviour
---------
Runs ``agent-01.py`` through ``agent-06.py`` sequentially, one subprocess per
stage using ``sys.executable`` (so the runner always uses the same Python
interpreter as itself). Stage output is captured and shown whenever a stage
fails; a final SUMMARY table reports PASS/FAIL, per-stage duration and the
total wall-clock time. The process exits with status 1 if any stage failed,
so the script is usable as a CI-style smoke test.

Stages are listed explicitly (not globbed) so the intended evolution order and
the complete set are always verified. A missing stage file counts as a failure.

Environment
-----------
``AGENT_MODEL``        forwarded to the child stages (default ``gemma4:e2b``)
``OLLAMA_HOST``        forwarded to the child stages (default ``http://localhost:11434``)
``AGENT_TIMEOUT_SECONDS``  optional per-stage timeout (default 600 seconds)

Usage
-----
    python all-agents.py

Requires Python 3.11+.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# The teaching sequence: every stage adds exactly one capability.
AGENT_SCRIPTS = [f"agent-{number:02d}.py" for number in range(1, 7)]
DEFAULT_TIMEOUT_SECONDS = 600


def configure_stdio() -> None:
    """Force UTF-8 console output so child output never crashes on Windows."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def timeout_seconds() -> int:
    """Read AGENT_TIMEOUT_SECONDS, falling back to a safe default when invalid."""
    raw = os.getenv("AGENT_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        value = int(raw)
    except ValueError:
        print(f"[WARN] Invalid AGENT_TIMEOUT_SECONDS={raw!r}; using {DEFAULT_TIMEOUT_SECONDS}.")
        return DEFAULT_TIMEOUT_SECONDS
    if value <= 0:
        print(f"[WARN] AGENT_TIMEOUT_SECONDS must be positive; using {DEFAULT_TIMEOUT_SECONDS}.")
        return DEFAULT_TIMEOUT_SECONDS
    return value


def indent(text: str, prefix: str = "     ") -> str:
    """Indent captured child output so it is visually nested under its stage."""
    return "\n".join(f"{prefix}{line}" for line in text.splitlines())


def run_agent(script: Path) -> tuple[bool, float, str]:
    """Run one stage script in a subprocess.

    Returns:
        (passed, duration_seconds, failure_detail) where failure_detail is an
        empty string on success and a trimmed transcript on failure.
    """
    limit = timeout_seconds()
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")

    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(script.parent),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=limit,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        duration = time.perf_counter() - started
        return False, duration, f"Timed out after {limit} seconds."
    except (OSError, subprocess.SubprocessError) as exc:
        duration = time.perf_counter() - started
        return False, duration, f"Could not start subprocess: {type(exc).__name__}: {exc}"

    duration = time.perf_counter() - started
    if completed.returncode == 0:
        return True, duration, ""

    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    detail = "\n".join(part for part in (stdout, stderr) if part) or "(no output captured)"
    lines = detail.splitlines()
    if len(lines) > 25:
        lines = ["... (earlier output omitted) ...", *lines[-25:]]
    return False, duration, "\n".join(lines)


def print_summary(results: list[tuple[str, bool, float]]) -> int:
    """Print the final table and return the exit code for this process."""
    print("\n" + "=" * 62)
    print("SUMMARY")
    print("=" * 62)
    print(f"{'Agent':<16}{'Status':<10}{'Duration':>14}")
    print("-" * 62)
    for name, passed, duration in results:
        status = "PASS" if passed else "FAIL"
        print(f"{name:<16}{status:<10}{duration:>12.2f} s")
    print("-" * 62)

    passed_count = sum(1 for _, passed, _ in results if passed)
    failed_count = len(results) - passed_count
    total_duration = sum(duration for _, _, duration in results)
    print(
        f"Passed: {passed_count}/{len(results)}    "
        f"Failed: {failed_count}    Total: {total_duration:.2f} s"
    )

    if failed_count:
        print(f"\n[FAIL] {failed_count} agent stage(s) failed - see the output above.")
        return 1
    print("\n[PASS] Every agent stage completed successfully.")
    return 0


def main() -> int:
    """Run all stages in order and return 0 only if every stage passed."""
    configure_stdio()

    base_dir = Path(__file__).resolve().parent
    print(f"Running {len(AGENT_SCRIPTS)} agent stages from: {base_dir}\n")

    results: list[tuple[str, bool, float]] = []
    for index, name in enumerate(AGENT_SCRIPTS, start=1):
        script = base_dir / name
        print(f"[{index}/{len(AGENT_SCRIPTS)}] {name}")

        if not script.is_file():
            print("  -> FAIL (stage file is missing)")
            results.append((name, False, 0.0))
            continue

        passed, duration, detail = run_agent(script)
        status = "PASS" if passed else "FAIL"
        print(f"  -> {status} ({duration:.2f} s)")
        if detail:
            print(indent(detail))
        results.append((name, passed, duration))

    return print_summary(results)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted; remaining stages were not run.")
        raise SystemExit(130) from None
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - last-resort user-friendly failure
        print(f"[ERROR] Runner failed unexpectedly ({type(exc).__name__}: {exc}).", file=sys.stderr)
        raise SystemExit(1) from None
