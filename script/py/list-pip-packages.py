"""
Unused Python Package Detection Tool

Purpose: Identifies Python packages installed via pip that haven't been used
recently (within the specified time window). Helpful for cleaning up
unused dependencies.

Features:
- Scans installed packages using importlib.metadata
- Checks modification times of package top-level files
- Filters out packages not found in the file system
- Customizable time threshold (default: 30 days)
- Displays packages sorted by last usage date

Use Case:
- Identifying unused dependencies for removal
- Cleaning up virtual environments
- Dependency audit and maintenance
- Understanding which packages are actually used

Output:
- List of unused packages sorted by last used date
- Package names and their last access timestamps

Note: This uses file modification times as a proxy for usage,
which may not be 100% accurate for all packages.
"""

import importlib.metadata
import importlib.util
import os
import time
from datetime import datetime, timezone


def _get_package_mtime(name: str) -> float | None:
    """Return the most recent modification time among top-level package files."""
    spec = importlib.util.find_spec(name)
    if not spec or not spec.origin:
        return None
    origin = spec.origin
    if not os.path.isfile(origin):
        return None
    try:
        return os.path.getmtime(origin)
    except OSError:
        return None


def find_unused_packages(days: int = 30) -> list[tuple[str, datetime]]:
    cutoff = time.time() - days * 86400
    unused: list[tuple[str, datetime]] = []

    for dist in importlib.metadata.distributions():
        name = dist.metadata["Name"]
        mtime = _get_package_mtime(name)
        if mtime is not None and mtime < cutoff:
            unused.append((name, datetime.fromtimestamp(mtime, tz=timezone.utc)))

    return sorted(unused, key=lambda x: x[1])


if __name__ == "__main__":
    days = 30
    unused = find_unused_packages(days=days)

    print(f"Packages NOT used in the last {days} days:")
    for name, ts in unused:
        print(f"{name:30} last used: {ts}")
