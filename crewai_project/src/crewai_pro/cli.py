"""Command-line entry point.

Usage:
    crewai-pro              # interactive REPL over enabled workflows
    crewai-pro --list       # list enabled workflows with their key
    crewai-pro --run KEY    # run a single workflow non-interactively
    crewai-pro --all        # run every enabled workflow in sequence
"""

from __future__ import annotations

import argparse
import sys

from crewai_pro.config import flags
from crewai_pro.workflows import REGISTRY, WorkflowDisabled, enabled_workflows, get_workflow


def _print_menu(workflows) -> None:
    print("\n" + "=" * 60)
    print("  CrewAI Combined Workflows")
    print("=" * 60)
    for i, wf in enumerate(workflows, 1):
        print(f"  [{i}] {wf.label}  (key: {wf.key})")
    print("  [q] Quit")
    print("=" * 60)


def _interactive(workflows) -> int:
    if not workflows:
        print("❌ No workflows enabled. Set at least one WORKFLOW_* env var to 'true'.")
        return 0

    while True:
        _print_menu(workflows)
        choice = input("Select a workflow: ").strip().lower()
        if choice == "q":
            print("Goodbye!")
            return 0
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(workflows):
                try:
                    workflows[idx].run()
                except WorkflowDisabled as exc:
                    print(f"⚠️  {exc}")
                except Exception as exc:
                    print(f"❌ Workflow failed: {exc}")
                continue
        # Also accept the workflow key directly
        if choice in REGISTRY:
            try:
                get_workflow(choice).run()
            except WorkflowDisabled as exc:
                print(f"⚠️  {exc}")
            except Exception as exc:
                print(f"❌ Workflow failed: {exc}")
            continue
        print("Invalid selection. Please try again.")


def _run_all(workflows) -> int:
    rc = 0
    for wf in workflows:
        try:
            wf.run()
        except WorkflowDisabled as exc:
            print(f"⚠️  {exc}")
        except Exception as exc:
            print(f"❌ Workflow '{wf.label}' failed: {exc}")
            rc = 1
    return rc


def _run_one(key: str) -> int:
    try:
        wf = get_workflow(key)
    except KeyError as exc:
        print(f"❌ {exc}")
        return 1
    if not wf.enabled:
        print(f"⚠️  Workflow '{wf.label}' is disabled.")
        return 1
    try:
        wf.run()
    except Exception as exc:
        print(f"❌ Workflow failed: {exc}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crewai-pro",
        description="Run enabled CrewAI workflows from a single CLI.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--list", action="store_true", help="List enabled workflows and exit.")
    group.add_argument("--run", metavar="KEY", help="Run a single workflow by key.")
    group.add_argument("--all", action="store_true", help="Run every enabled workflow in order.")
    args = parser.parse_args(argv)

    f = flags()
    enabled = enabled_workflows()

    if args.list:
        if not enabled:
            print("No workflows enabled.")
        for wf in enabled:
            print(f"{wf.key:<14} {wf.label}")
        return 0

    if args.run:
        return _run_one(args.run)

    if args.all:
        return _run_all(enabled)

    return _interactive(enabled)


if __name__ == "__main__":
    sys.exit(main())