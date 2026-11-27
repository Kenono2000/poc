"""Skill discovery and SKILL.md parser."""

import re
from pathlib import Path

import yaml

from skillguard.models import Scope, SkillNode

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
IMPERATIVE_RE = re.compile(r"\b(ALWAYS|NEVER|MUST|DO NOT|REQUIRED)\b.*", re.IGNORECASE)
HARDCODED_PATH_RE = re.compile(r"(?:[A-Za-z]:\\[^\s`\"']+)|(?:/Users/[^\s`\"']+)|(?:/home/[^\s`\"']+)")
NEGATIVE_GUARDRAIL_RE = re.compile(r"\b(don't use|do not use|not for|avoid using|skip when)\b", re.IGNORECASE)


def estimate_tokens(text: str) -> int:
    """Roughly estimate token count (~4 chars per token)."""
    return max(1, len(text) // 4)


def parse_skill_file(path: Path, scope: Scope) -> SkillNode | None:
    """Parse a SKILL.md file into a SkillNode."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    match = FRONTMATTER_RE.match(raw)
    if match:
        fm_raw, body = match.group(1), match.group(2)
        try:
            fm = yaml.safe_load(fm_raw) or {}
        except yaml.YAMLError:
            fm = {}
    else:
        fm = {}
        body = raw

    name = str(fm.get("name") or path.parent.name)
    description = str(fm.get("description") or "").strip()
    imperatives = [m.group(0).strip() for m in IMPERATIVE_RE.finditer(body)]
    hardcoded_paths = HARDCODED_PATH_RE.findall(body)
    has_guardrail = bool(NEGATIVE_GUARDRAIL_RE.search(description))

    return SkillNode(
        id=f"{scope}:{name}",
        name=name,
        scope=scope,
        path=str(path),
        description=description,
        body=body,
        token_count=estimate_tokens(raw),
        imperatives=imperatives[:20],
        has_negative_guardrail=has_guardrail,
        hardcoded_paths=list(set(hardcoded_paths))[:10],
    )


def default_skill_roots(project_dir: Path | None = None) -> list[tuple[Scope, Path]]:
    """Return standard global and project skill directories."""
    home = Path.home()
    roots: list[tuple[Scope, Path]] = [
        ("global", home / ".gemini" / "config" / "skills"),
        ("global", home / ".agents" / "skills"),
    ]
    if project_dir:
        roots.extend(
            [
                ("project", project_dir / ".agent" / "skills"),
                ("project", project_dir / ".gemini" / "skills"),
            ]
        )
    return roots


def scan_skills(
    project_dir: Path | None = None,
    extra_roots: list[tuple[Scope, Path]] | None = None,
    include_defaults: bool = True,
) -> list[SkillNode]:
    """Discover and parse all SKILL.md files across configured roots."""
    roots = default_skill_roots(project_dir) if include_defaults else []
    if extra_roots:
        roots.extend(extra_roots)

    skills: list[SkillNode] = []
    seen_paths: set[Path] = set()

    for scope, root in roots:
        if not root.exists() or not root.is_dir():
            continue
        for skill_file in root.rglob("SKILL.md"):
            resolved = skill_file.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            node = parse_skill_file(resolved, scope)
            if node:
                skills.append(node)

    return sorted(skills, key=lambda s: (s.scope, s.name.lower()))
