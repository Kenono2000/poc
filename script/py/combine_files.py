"""
Bundle several related text/markdown files into one or more consolidated files.

Each source file is embedded after an 80-column FILE header, which makes the
result easy to skim, paste into a prompt, or diff against a previous bundle.

Usage
-----
1. Default bundles (no arguments) -- reproduces the historical suntiq-product
   document bundles and writes them into the current directory::

       python combine_files.py

2. One bundle from explicit inputs::

       python combine_files.py README.md docs/a.md --source-dir .. --output bundle.txt
       python combine_files.py --files README.md docs/a.md --output out/bundle.txt

3. Several bundles described by a JSON manifest (inline JSON or a file path)::

       python combine_files.py --parts parts.json --source-dir .. --out-dir out
       python combine_files.py --parts '{"bundle.txt": ["a.md", "b.md"]}'

   The manifest is either a mapping ``{"<output>": ["<input>", ...]}`` or a
   list of ``{"output"|"name": ..., "files"|"inputs": [...]}`` objects.

Behaviour
---------
* Relative inputs are resolved against ``--source-dir`` (default: the current
  directory).  Missing files are marked inline in the bundle, listed per
  bundle, and counted in the final summary; they are not fatal.
* Output parent directories are created automatically; output is always UTF-8.
* Per-bundle and overall summaries report files included, missing/unreadable
  entries, and the resulting bundle size.

Exit codes
----------
    0  every requested bundle was written
    1  invalid arguments, unreadable manifest, or an output write failure
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Default bundles (used when the script is invoked with no arguments).
# Keys are output file names, values are inputs resolved against --source-dir
# (the current directory by default), matching the script's original layout.
# ---------------------------------------------------------------------------
DEFAULT_PARTS: dict[str, list[str]] = {
    "combined_part_1_core_and_labs.txt": [
        "suntiq-product/README.md",
        "suntiq-product/AGENTS.md",
        "suntiq-product/CLAUDE.md",
        "suntiq-product/docs/onboarding/README.md",
        "suntiq-product/docs/onboarding/ARCHITECTURE.md",
        "suntiq-product/docs/onboarding/TRANSITION.md",
        "suntiq-product/docs/onboarding/BACKLOG.md",
        "suntiq-product/docs/fleet/ENVIRONMENTS.md",
        "suntiq-product/docs/Homepage Breakdown.md",
        "suntiq-product/apps/www/docs/SEO_AEO_CHECKLIST.md",
        "suntiq-product/apps/www/docs/PRD.md",
        "suntiq-product/apps/www/docs/OUTBOUND_SALES_PRD.md",
        "suntiq-product/packages/ui-web/AGENTS.md",
        "suntiq-product/packages/ui-web/CLAUDE.md",
        "suntiq-product/packages/ui-tokens/AGENTS.md",
        "suntiq-product/packages/ui-tokens/CLAUDE.md",
        "suntiq-product/packages/ui-native/AGENTS.md",
        "suntiq-product/packages/ui-native/CLAUDE.md",
        "suntiq-product/labs/README.md",
        "suntiq-product/labs/ml/FINDINGS.md",
        "suntiq-product/labs/ml/argo-ml-research-repo/README.md",
        "suntiq-product/labs/ml/argo-ml-deliverable/argo-ml/README.md",
    ],
    "combined_part_2_apps.txt": [
        "suntiq-product/apps/fleet-dashboard/README.md",
        "suntiq-product/apps/fleet-dashboard/AGENTS.md",
        "suntiq-product/apps/fleet-dashboard/CLAUDE.md",
        "suntiq-product/apps/fleet-dashboard/convex/README.md",
        "suntiq-product/apps/fleet-mobile/README.md",
        "suntiq-product/apps/fleet-mobile/AGENTS.md",
        "suntiq-product/apps/fleet-mobile/CLAUDE.md",
        "suntiq-product/apps/consumer-mobile/README.md",
        "suntiq-product/apps/consumer-mobile/AGENTS.md",
        "suntiq-product/apps/consumer-mobile/CLAUDE.md",
        "suntiq-product/apps/www/README.md",
        "suntiq-product/apps/www/AGENTS.md",
        "suntiq-product/apps/www/CLAUDE.md",
        "suntiq-product/apps/ui-docs/README.md",
        "suntiq-product/apps/ui-docs/AGENTS.md",
        "suntiq-product/apps/ui-docs/CLAUDE.md",
    ],
    "combined_part_3_research_gtm.txt": [
        "suntiq-product/docs/research/suntiq-gtm-2026-08/README.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/gtm-operating-system.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/foundation-pack.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/final-direction.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/content-refresh-brief.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/gtm-validation-activation-kit.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ASSET_INDEX.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/tribunal/report.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/user-and-agent-research.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/summary.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/study-design.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/source-map.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/constraint-bundle.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/persona-detection.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/regional-operations-leader.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/peak-season-member.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/owner-finance-lead.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/integration-gatekeeper.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/fleet-maintenance-lead.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/ux/personas/dock-turnaround-manager.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/assumptions-falsifiers.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/competitor-marketing-sales.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/implicit-truths.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/consensus-blindspots-white-space.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/analysis/investor-attack.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/validation/prelaunch-product-study-plan.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/validation/pilot-experiment-plan.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/validation/external-validator.md",
        "suntiq-product/docs/research/suntiq-gtm-2026-08/validation/conversation-guide.md",
    ],
}

HEADER_WIDTH = 80


def _configure_stdout() -> None:
    """Force UTF-8 console output so paths/content never crash the terminal."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def _normalize_inputs(raw: object, context: str) -> list[str]:
    """Coerce a manifest entry into a list of input path strings."""
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list) and all(isinstance(item, str) for item in raw):
        return [str(item) for item in raw]
    raise ValueError(
        f"{context}: expected a string or a list of strings, got {type(raw).__name__}"
    )


def load_parts_manifest(raw: str) -> dict[str, list[str]]:
    """Parse ``--parts`` (inline JSON or a path to a JSON file) into bundles.

    Accepted shapes are the mapping form ``{"out.txt": ["a.md", ...]}`` and the
    list form ``[{"output": "out.txt", "files": [...]}, ...]`` (``name`` and
    ``inputs`` are accepted as aliases).
    """
    text = raw
    candidate = Path(raw)
    if "\n" not in raw and candidate.is_file():
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"cannot read parts manifest {raw!r}: {exc}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--parts is not valid JSON: {exc}") from exc

    parts: dict[str, list[str]] = {}
    if isinstance(data, dict):
        for output_name, entries in data.items():
            parts[str(output_name)] = _normalize_inputs(
                entries, f"manifest output {output_name!r}"
            )
    elif isinstance(data, list):
        for index, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f"manifest entry {index} must be an object")
            output_name = item.get("output") or item.get("name")
            if not output_name:
                raise ValueError(f"manifest entry {index} needs 'output' or 'name'")
            entries = item.get("files", item.get("inputs", []))
            parts[str(output_name)] = _normalize_inputs(
                entries, f"manifest entry {index!r}"
            )
    else:
        raise ValueError(
            f"--parts must be a JSON object or list, got {type(data).__name__}"
        )

    if not parts:
        raise ValueError("--parts described no bundles")
    return parts


def write_bundle(
    output_path: Path,
    inputs: list[str],
    source_dir: Path,
) -> dict[str, object]:
    """Write one bundle and return a small statistics record.

    Stats keys: ``output`` (Path), ``included`` (int), ``missing`` (list[str]),
    ``unreadable`` (list[str]), ``bytes`` (int).  The bundle is created even
    when every input is missing, so runs are reproducible and inspectable.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    included = 0
    missing: list[str] = []
    unreadable: list[str] = []

    with output_path.open("w", encoding="utf-8", newline="\n") as outfile:
        for raw_path in inputs:
            resolved = Path(raw_path)
            if not resolved.is_absolute():
                resolved = source_dir / resolved

            outfile.write(f"\n{'=' * HEADER_WIDTH}\n")
            outfile.write(f"FILE: {raw_path}\n")
            outfile.write(f"{'=' * HEADER_WIDTH}\n\n")

            if not resolved.is_file():
                outfile.write(
                    f"[MISSING] Input file not found: {raw_path} "
                    f"(resolved: {os.fspath(resolved)})\n"
                )
                missing.append(raw_path)
                continue

            try:
                content = resolved.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # Keep going: bundle the readable majority rather than abort.
                content = resolved.read_text(encoding="utf-8", errors="replace")
                unreadable.append(f"{raw_path} (invalid UTF-8, replaced)")
            except OSError as exc:
                outfile.write(f"[ERROR] Could not read file {raw_path}: {exc}\n")
                unreadable.append(f"{raw_path} ({exc})")
                continue

            outfile.write(content)
            if not content.endswith("\n"):
                outfile.write("\n")
            included += 1

    return {
        "output": output_path,
        "included": included,
        "missing": missing,
        "unreadable": unreadable,
        "bytes": output_path.stat().st_size,
    }


def _human_size(num_bytes: int) -> str:
    """Format a byte count as a short human-readable string."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"


def _resolve_output(output_name: str, out_dir: Path) -> Path:
    """Resolve an output name against ``--out-dir`` unless already absolute."""
    path = Path(output_name)
    return path if path.is_absolute() else out_dir / path


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Combine related text files into consolidated bundles.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Run without arguments to rebuild the default suntiq-product bundles.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Input files for a single bundle (alternative to --files).",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        action="extend",
        dest="file_inputs",
        default=None,
        metavar="FILE",
        help="Input files for a single bundle; combine with positional inputs.",
    )
    parser.add_argument(
        "--source-dir",
        default=".",
        help="Directory used to resolve relative input paths (default: current directory).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output bundle path for the --files/positional mode (required there).",
    )
    parser.add_argument(
        "--parts",
        default=None,
        help="JSON manifest (inline JSON or path to a .json file) mapping outputs to inputs.",
    )
    parser.add_argument(
        "--out-dir",
        default=".",
        help="Directory used to resolve relative output paths (default: current directory).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    _configure_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)

    source_dir = Path(args.source_dir).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    # Positional inputs and --files are merged; positional inputs come first.
    cli_inputs = list(args.files or []) + list(args.file_inputs or [])

    if args.parts is not None:
        if args.output is not None:
            parser.error("--parts and --output cannot be combined; set outputs in the manifest.")
        if cli_inputs:
            parser.error("--parts cannot be combined with input files; list them in the manifest.")
        try:
            parts = load_parts_manifest(args.parts)
        except ValueError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        using_defaults = False
    elif cli_inputs:
        if not args.output:
            parser.error("--output is required when supplying input files.")
        parts = {args.output: cli_inputs}
        using_defaults = False
    else:
        if args.output:
            parser.error("--output requires input files (positional or --files).")
        parts = {name: list(entries) for name, entries in DEFAULT_PARTS.items()}
        using_defaults = True

    if using_defaults:
        print(f"[INFO] No inputs given; rebuilding {len(parts)} default bundle(s).")
        print(f"[INFO] Inputs resolve against: {source_dir.resolve()}")

    stats: list[dict[str, object]] = []
    total_included = 0
    total_missing = 0
    total_unreadable = 0
    failures = 0

    for output_name, inputs in parts.items():
        output_path = _resolve_output(output_name, out_dir)
        try:
            record = write_bundle(output_path, inputs, source_dir)
        except OSError as exc:
            print(f"[ERROR] Could not write bundle {output_path}: {exc}", file=sys.stderr)
            failures += 1
            continue

        stats.append(record)
        included = int(record["included"])
        missing = list(record["missing"])  # type: ignore[arg-type]
        unreadable = list(record["unreadable"])  # type: ignore[arg-type]
        total_included += included
        total_missing += len(missing)
        total_unreadable += len(unreadable)

        print(f"\nBundle: {output_name}")
        print(f"  Output   : {output_path.resolve()}")
        print(
            f"  Files    : {included} included, {len(missing)} missing, "
            f"{len(unreadable)} unreadable"
        )
        print(f"  Size     : {int(record['bytes']):,} bytes ({_human_size(int(record['bytes']))})")
        for raw_path in missing:
            print(f"    [MISSING]    {raw_path}")
        for note in unreadable:
            print(f"    [UNREADABLE] {note}")

    total_bytes = sum(int(record["bytes"]) for record in stats)
    print("\n" + "=" * HEADER_WIDTH)
    print(" SUMMARY")
    print("=" * HEADER_WIDTH)
    print(f"Bundles written : {len(stats)}/{len(parts)}")
    print(f"Files included  : {total_included}")
    print(f"Files missing   : {total_missing}")
    print(f"Files unreadable: {total_unreadable}")
    print(f"Total size      : {total_bytes:,} bytes ({_human_size(total_bytes)})")
    print("=" * HEADER_WIDTH)

    if failures:
        print(f"[ERROR] {failures} bundle(s) could not be written.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
