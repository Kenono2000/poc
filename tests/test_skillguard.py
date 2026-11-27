"""Unit tests for SkillGuard."""

from pathlib import Path

from skillguard.analyzer import analyze
from skillguard.scanner import parse_skill_file, scan_skills


def test_parse_and_conflict_detection(tmp_path: Path) -> None:
    global_dir = tmp_path / "global" / "my-skill"
    project_dir = tmp_path / "project" / "my-skill"
    global_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)

    (global_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Format markdown files with minimal whitespace rules.\n"
        "---\nALWAYS strip blank lines.\n",
        encoding="utf-8",
    )
    (project_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: Format markdown files with verbose whitespace rules.\n"
        "---\nALWAYS add blank lines.\n",
        encoding="utf-8",
    )

    skills = scan_skills(
        extra_roots=[("global", tmp_path / "global"), ("project", tmp_path / "project")],
        include_defaults=False,
    )
    assert len(skills) == 2

    result = analyze(skills)
    conflict_types = {c.conflict_type for c in result.conflicts}
    assert "name_collision" in conflict_types
    assert "trigger_overlap" in conflict_types
    assert "rule_contradiction" in conflict_types


def test_predict_problems(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        "---\nname: short-skill\ndescription: Too short\n---\nCheck C:\\Users\\test\\file.txt\n",
        encoding="utf-8",
    )
    node = parse_skill_file(skill_file, "project")
    assert node is not None

    result = analyze([node], token_budget=1)
    issue_types = {p.issue_type for p in result.predictions}
    assert "token_bloat" in issue_types
    assert "trigger_ambiguity" in issue_types
    assert "missing_guardrail" in issue_types
    assert "brittle_path" in issue_types
