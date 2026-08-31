"""Smoke tests that don't require API keys."""

from __future__ import annotations

import pytest

from crewai_pro import agents, workflows
from crewai_pro.config import flags
from crewai_pro.tools import DriveRelocationAnalyzerTool
from crewai_pro.workflows import REGISTRY, enabled_workflows, get_workflow


def test_all_expected_workflows_registered():
    expected = {"ai_research", "crewai_news", "relocation", "linkedin_jobs"}
    assert set(REGISTRY) == expected


def test_agents_exports_match_old_module():
    expected = {
        "researcher",
        "writer",
        "web_researcher",
        "drive_analyst",
        "relocation_specialist",
        "report_writer",
        "job_researcher",
    }
    for name in expected:
        assert hasattr(agents, name), f"missing agent export: {name}"


def test_flags_default_all_disabled(monkeypatch):
    for var in (
        "WORKFLOW_AI_RESEARCH",
        "WORKFLOW_CREWAI_NEWS",
        "WORKFLOW_RELOCATION",
        "WORKFLOW_LINKEDIN_JOBS",
    ):
        monkeypatch.delenv(var, raising=False)
    flags.cache_clear()
    f = flags()
    assert f.any_enabled() is False


def test_flags_truthy_values(monkeypatch):
    for var in ("WORKFLOW_AI_RESEARCH", "WORKFLOW_CREWAI_NEWS"):
        monkeypatch.setenv(var, "TRUE")
    flags.cache_clear()
    f = flags()
    assert f.ai_research is True
    assert f.crewai_news is True
    assert f.relocation is False
    assert f.linkedin_jobs is False


def test_enabled_workflows_respects_flags(monkeypatch):
    monkeypatch.setenv("WORKFLOW_RELOCATION", "1")
    flags.cache_clear()
    enabled = enabled_workflows()
    assert [wf.key for wf in enabled] == ["relocation"]


def test_get_workflow_unknown_raises():
    with pytest.raises(KeyError):
        get_workflow("nope")


def test_drive_tool_is_a_basetool_subclass():
    from crewai.tools import BaseTool

    assert issubclass(DriveRelocationAnalyzerTool, BaseTool)