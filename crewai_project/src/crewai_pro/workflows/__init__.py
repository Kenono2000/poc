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

from crewai_pro.config import flags
from crewai_pro.workflows.ai_research import ai_research_workflow
from crewai_pro.workflows.crewai_news import crewai_news_workflow
from crewai_pro.workflows.linkedin_jobs import linkedin_jobs_workflow
from crewai_pro.workflows.relocation import relocation_workflow

REGISTRY: dict[str, "Workflow"] = {}


class WorkflowDisabled(RuntimeError):
    """Raised when a workflow is invoked while its flag is False."""


class Workflow:
    def __init__(
        self,
        key: str,
        label: str,
        flag_name: str,
        build_crew: Callable,
        runner: Callable[[], object],
    ) -> None:
        self.key = key
        self.label = label
        self.flag_name = flag_name
        self._build_crew = build_crew
        self._runner = runner
        REGISTRY[key] = self

    @property
    def enabled(self) -> bool:
        return getattr(flags(), self.flag_name)

    def build(self):
        return self._build_crew()

    def run(self):
        if not self.enabled:
            raise WorkflowDisabled(
                f"Workflow '{self.label}' is disabled "
                f"(WORKFLOW_{self.flag_name.upper()}=false)."
            )
        return self._runner()


for _wf in (
    ai_research_workflow,
    crewai_news_workflow,
    relocation_workflow,
    linkedin_jobs_workflow,
):
    pass  # construction registers them in REGISTRY


def enabled_workflows() -> list[Workflow]:
    return [wf for wf in REGISTRY.values() if wf.enabled]


def get_workflow(key: str) -> Workflow:
    wf = REGISTRY.get(key)
    if wf is None:
        raise KeyError(f"Unknown workflow '{key}'. Known: {list(REGISTRY)}")
    return wf


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