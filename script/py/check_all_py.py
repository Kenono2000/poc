"""
Parallel Python syntax checker.

Checks every ``*.py`` file under the repository root for syntax errors without
executing any of them.  Files are compiled concurrently with
``python -m py_compile``; results are printed in a fixed-width table plus a
summary line.

Read-only / permission-safe fallback
------------------------------------
``py_compile`` writes a ``__pycache__/<name>.pyc`` file next to the source.
In read-only checkouts, protected package directories, or sandboxes that deny
bytecode writes, that write fails with ``PermissionError`` even though the
source file is perfectly valid.  To avoid reporting such files as INVALID, a
failed ``py_compile`` whose error mentions a permission/read-only problem is
re-verified with the built-in ``compile(source, filename, "exec")`` (which
never touches the filesystem).  Genuine syntax errors are still reported as
INVALID, and the table notes when the in-process fallback was used.

Usage
-----
    python check_all_py.py

Exit codes
----------
    0  every discovered script is valid
    1  at least one script has a syntax error (or timed out / could not run)
"""

from __future__ import annotations

import subprocess
import sys
import time
import tokenize
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# --- Configuration ---
# Root directory to search for .py files (repository root, i.e. poc/).
ROOT_DIR = Path(__file__).resolve().parents[2]
# Scripts and directories to exclude from checking.
EXCLUDE_FILES = {Path(__file__).name, "__init__.py"}
EXCLUDE_DIRS = {".git", ".venv", "venv", "_env", "node_modules", "__pycache__"}
# Maximum time to wait for a single py_compile invocation (seconds).
TIMEOUT = 30

#: Substrings (lower-cased) that identify a bytecode-cache permission failure.
PERMISSION_MARKERS = (
    "permissionerror",
    "permission denied",
    "errno 13",
    "read-only file system",
    "read-only database",
    "access is denied",
    "operation not permitted",
)


def _relative(script_path: Path) -> str:
    """Return a POSIX-style path relative to ROOT_DIR, or the absolute path."""
    try:
        return script_path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return str(script_path)


def _is_permission_failure(stderr: str) -> bool:
    """Return True when py_compile failed because it could not write its cache."""
    lowered = (stderr or "").lower()
    return any(marker in lowered for marker in PERMISSION_MARKERS)


def _last_error_line(stderr: str, fallback: str) -> str:
    """Extract the most informative single line from stderr."""
    lines = [line.strip() for line in (stderr or "").splitlines() if line.strip()]
    return lines[-1] if lines else fallback


def compile_in_process(script_path: Path) -> str | None:
    """Compile the source with builtin ``compile`` without writing bytecode.

    Returns ``None`` when the file is syntactically valid, otherwise a
    one-line error message suitable for the results table.
    """
    try:
        with tokenize.open(script_path) as handle:
            source = handle.read()
        compile(source, str(script_path), "exec")
        return None
    except SyntaxError as exc:
        location = f"line {exc.lineno}" if exc.lineno else "unknown location"
        return f"SyntaxError: {exc.msg} ({location})"
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return f"{type(exc).__name__}: {exc}"


def run_script(script_path: Path) -> dict[str, str]:
    """Check one script; returns ``{path, status, duration, error, fallback}``."""
    label = _relative(script_path)
    start_time = time.time()

    try:
        process = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "path": label,
            "status": "TIMEOUT",
            "duration": f">{TIMEOUT}s",
            "error": f"Exceeded {TIMEOUT}s limit",
            "fallback": "",
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "path": label,
            "status": "ERROR",
            "duration": "0.00s",
            "error": str(exc),
            "fallback": "",
        }

    duration = f"{time.time() - start_time:.2f}s"

    if process.returncode == 0:
        return {
            "path": label,
            "status": "VALID",
            "duration": duration,
            "error": "",
            "fallback": "",
        }

    # py_compile failed.  Did it fail only because it could not write
    # __pycache__?  If so, verify the source in-process instead of trusting
    # the (misleading) failure.
    stderr = process.stderr or ""
    if _is_permission_failure(stderr):
        in_process_error = compile_in_process(script_path)
        if in_process_error is None:
            return {
                "path": label,
                "status": "VALID",
                "duration": duration,
                "error": "py_compile cache write denied; verified via compile()",
                "fallback": "in-process",
            }
        return {
            "path": label,
            "status": "INVALID",
            "duration": duration,
            "error": in_process_error,
            "fallback": "in-process",
        }

    return {
        "path": label,
        "status": "INVALID",
        "duration": duration,
        "error": _last_error_line(stderr, "Syntax Error"),
        "fallback": "",
    }


def main() -> int:
    """Discover scripts, check them in parallel, print the table and summary."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

    print(f"[*] Compiling Python scripts in: {ROOT_DIR}")

    scripts = sorted(
        (
            path
            for path in ROOT_DIR.rglob("*.py")
            if path.is_file()
            and path.name not in EXCLUDE_FILES
            and not any(
                part in EXCLUDE_DIRS for part in path.relative_to(ROOT_DIR).parts
            )
        ),
        key=lambda path: _relative(path),
    )

    if not scripts:
        print("No Python scripts found.")
        return 0

    print(f"Found {len(scripts)} scripts. Starting syntax check...\n")

    # ThreadPoolExecutor: py_compile runs in subprocesses, so real parallelism.
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(run_script, scripts))

    # --- Print Results Table ---
    header = f"{'STATUS':<10} | {'TIME':<10} | {'SCRIPT PATH':<60} | {'DETAIL'}"
    print(header)
    print("-" * len(header))

    counts: dict[str, int] = {}
    fallback_count = 0
    for result in sorted(results, key=lambda item: (item["status"], item["path"])):
        counts[result["status"]] = counts.get(result["status"], 0) + 1
        if result["fallback"]:
            fallback_count += 1
        print(
            f"{result['status']:<10} | {result['duration']:<10} | "
            f"{result['path']:<60} | {result['error']}"
        )

    print("-" * len(header))
    valid = counts.get("VALID", 0)
    invalid = counts.get("INVALID", 0)
    total = len(results)
    extra = total - valid - invalid
    summary = f"SUMMARY: {valid}/{total} Valid Scripts | {invalid} Syntax Errors"
    if extra:
        summary += f" | {extra} Other Errors"
    if fallback_count:
        summary += f" | {fallback_count} verified via compile() fallback"
    print(summary)

    return 0 if invalid == 0 and extra == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
