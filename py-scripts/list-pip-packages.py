"""
Unused Python Package Detection Tool

Purpose: Identifies Python packages installed via pip that haven't been used
recently (within the specified time window). Helpful for cleaning up
unused dependencies.

Features:
- Scans all installed packages using importlib.metadata
- Checks timestamps of Python files for last access time
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
from datetime import datetime

days = 30
cutoff = time.time() - days * 86400

unused = []

for dist in importlib.metadata.distributions():
    name = dist.metadata["Name"]

    try:
        spec = importlib.util.find_spec(name)
        if not spec or not spec.origin:
            continue

        path = spec.origin
        if not os.path.exists(path):
            continue

        # Scan .py and .pyc timestamps
        timestamps = []
        for root, dirs, files in os.walk(os.path.dirname(path)):
            for f in files:
                if f.endswith((".py", ".pyc")):
                    timestamps.append(os.path.getmtime(os.path.join(root, f)))

        if not timestamps:
            continue

        last_used = max(timestamps)

        if last_used < cutoff:
            unused.append((name, datetime.fromtimestamp(last_used)))

    except Exception:
        pass

print("Packages NOT used in the last", days, "days:")
for name, ts in sorted(unused, key=lambda x: x[1]):
    print(f"{name:30} last used: {ts}")
