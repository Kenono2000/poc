"""
List installed pip packages as a sorted, human-readable inventory.

Purpose
-------
Print every package installed in the *current* Python environment (the
interpreter running this script) together with its version, sorted
alphabetically so two environments can be compared with a simple diff.

Why it works this way
---------------------
* Pip is invoked as ``sys.executable -m pip list`` so the report always
  describes the interpreter executing this script.  This works inside a
  virtualenv even when ``pip`` is not on ``PATH`` and avoids accidentally
  querying a different Python installation.
* ``--format=json`` is parsed instead of scraping pip's table output, which
  keeps the code resilient to pip's column formatting changes.
* Every failure mode (pip missing, non-zero exit, unparsable JSON, timeout) is
  reported clearly on stderr and produces exit code 1 so callers can tell the
  difference between "no packages" and "could not ask pip".

Usage
-----
    python list-pip-packages.py

Output
------
    Installed packages (42):
    ----------------------------------------
    anyio                     4.4.0
    certifi                   2024.7.4
    ...
    ----------------------------------------
    Total: 42 package(s) in C:\\src\\.venv\\Scripts\\python.exe

Exit codes
----------
    0  package list printed successfully (possibly empty)
    1  pip could not be queried or returned unusable data
"""

from __future__ import annotations

import json
import subprocess
import sys

#: Safety net so a hung pip invocation cannot block the caller forever.
PIP_TIMEOUT_SECONDS = 120


def _configure_stdout() -> None:
    """Force UTF-8 output so unusual package names never crash the console."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def list_installed_packages(
    timeout: int = PIP_TIMEOUT_SECONDS,
) -> list[tuple[str, str]]:
    """Return ``[(name, version), ...]`` for every package pip reports.

    Packages are sorted alphabetically (case-insensitively) so output is
    stable across platforms and pip versions.

    Raises
    ------
    RuntimeError
        If pip cannot be executed, returns a non-zero exit code, or emits
        data that is not the expected JSON list.
    """
    command = [sys.executable, "-m", "pip", "list", "--format=json"]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"pip list timed out after {timeout}s") from exc
    except OSError as exc:  # interpreter missing or subprocess plumbing broken
        raise RuntimeError(f"failed to start pip: {exc}") from exc

    if completed.returncode != 0:
        stderr_lines = (completed.stderr or "").strip().splitlines()
        detail = stderr_lines[-1] if stderr_lines else "no error output"
        raise RuntimeError(f"pip list exited with code {completed.returncode}: {detail}")

    try:
        payload = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"pip list returned invalid JSON: {exc}") from exc

    if not isinstance(payload, list):
        raise RuntimeError(
            f"unexpected pip JSON payload type: {type(payload).__name__}"
        )

    packages: list[tuple[str, str]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        if not name:
            continue
        version = str(entry.get("version") or "").strip() or "unknown"
        packages.append((name, version))

    packages.sort(key=lambda item: (item[0].lower(), item[0]))
    return packages


def main() -> int:
    """Print the sorted package inventory; return the process exit code."""
    _configure_stdout()

    try:
        packages = list_installed_packages()
    except RuntimeError as exc:
        print(f"[ERROR] Could not list pip packages: {exc}", file=sys.stderr)
        print(
            "        Hint: run "
            f"\"{sys.executable} -m pip list --format=json\" directly to reproduce.",
            file=sys.stderr,
        )
        return 1

    if not packages:
        print("[WARNING] pip reported no installed packages for this interpreter.")
        return 0

    name_width = max(len(name) for name, _ in packages)
    separator = "-" * min(max(name_width + 12, 40), 100)

    print(f"Installed packages ({len(packages)}):")
    print(separator)
    for name, version in packages:
        print(f"{name:<{name_width}}  {version}")
    print(separator)
    print(f"Total: {len(packages)} package(s) in {sys.executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
