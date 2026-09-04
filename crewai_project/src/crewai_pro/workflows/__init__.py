"""Workflow definitions.

Each module exposes:

* `KEY`          — short id used by the CLI ("ai_research", "relocation", ...)
* `LABEL`        — human-readable name shown in the menu
* `FLAG_NAME`    — attribute name on `WorkflowFlags`
* `build_crew()` — returns the configured `crewai.Crew`
* `run()`        — kicks off the crew and returns the raw result

Workflows whose flag is `False` still expose the builders, but `run()` raises
`WorkflowDisabled` so the CLI can show a friendly message.
"""

from __future__ import annotations

from typing import Callable

from .base import REGISTRY, Workflow, WorkflowDisabled, enabled_workflows, get_workflow
from .ai_research import ai_research_workflow
from .crewai_news import crewai_news_workflow
from .linkedin_jobs import linkedin_jobs_workflow
from .relocation import relocation_workflow

__all__ = [
    "REGISTRY",
    "Workflow",
    "WorkflowDisabled",
    "enabled_workflows",
    "get_workflow",
    "ai_research_workflow",
    "crewai_news_workflow",
    "relocation_workflow",
    "linkedin_jobs_workflow",
]
