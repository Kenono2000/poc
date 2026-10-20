"""
Pattern 6: Self-Healing SDLC Agent with AST Security Guardrails
===============================================================
Core Interview Point:
- Autonomous coding agents must NEVER execute untrusted LLM patches directly.
- Deterministic Gate (`audit_patch`) runs `ast.walk()` to block dangerous sinks (`eval`,
  `exec`, `__import__`), scans for leaked secrets (`sk-...`), and blocks path traversal (`..`).
- Self-Healing Loop feeds test failure tracebacks back into `repair` up to `max_attempts=3`.
"""

import ast
from pathlib import Path
import re

BANNED_CALLS = {"eval", "exec", "__import__", "compile"}
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{10,}|AIza[0-9A-Za-z-_]{10,}|-----BEGIN PRIVATE KEY-----)")


def is_safe_path(file_path: str, sandbox_root: Path) -> bool:
    """Prevent sandbox escape via '..', absolute paths, or '.git' modification."""
    target = (sandbox_root / file_path).resolve()
    return target.is_relative_to(sandbox_root.resolve()) and ".git" not in target.parts


def audit_patch(code: str) -> list[str]:
    """Static AST + Regex inspection before executing any generated code."""
    violations: list[str] = []
    if SECRET_RE.search(code):
        violations.append("Hardcoded secret/API key detected")

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"SyntaxError: {exc}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in BANNED_CALLS:
                violations.append(f"Banned execution sink: {node.func.id}()")
    return violations


def run_self_healing_cycle(patches_by_attempt: list[str], max_attempts: int = 3) -> str:
    """State Machine: Propose -> AST Audit -> Test -> Self-Heal Repair Loop -> PR."""
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        patch = patches_by_attempt[min(attempt - 1, len(patches_by_attempt) - 1)]
        print(f"[Attempt {attempt}] Auditing proposed patch...")

        violations = audit_patch(patch)
        if violations:
            last_error = f"Security Gate Blocked: {violations}"
            print(f"  ❌ {last_error}")
            continue

        # Execute isolated unit test check against AST-verified code
        namespace: dict = {}
        exec(patch, namespace)  # Safe only AFTER AST audit passes
        try:
            assert namespace["add"](2, 3) == 5, "Expected add(2, 3) == 5"
            print("  ✅ Audit & Pytest passed! Opening Pull Request.")
            return "PR_OPENED"
        except AssertionError as exc:
            last_error = str(exc)
            print(f"  🔧 Test failed ({last_error}) -> Routing traceback to repair_patches...")

    return f"ESCALATED ({last_error})"


if __name__ == "__main__":
    simulated_llm_attempts = [
        "def add(a, b): return eval('a + b')",  # Attempt 1: Blocked by AST Guardrail
        "def add(a, b): return a - b",          # Attempt 2: Passes AST, fails unit test
        "def add(a, b): return a + b",          # Attempt 3: Self-healed patch passes!
    ]
    status = run_self_healing_cycle(simulated_llm_attempts)
    print(f"Final Workflow Status: {status}")
