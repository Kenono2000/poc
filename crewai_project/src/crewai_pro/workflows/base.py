"""Base workflow classes and registry."""

from __future__ import annotations

from typing import Callable
from crewai_pro.config import flags

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


def enabled_workflows() -> list[Workflow]:
    return [wf for wf in REGISTRY.values() if wf.enabled]


def get_workflow(key: str) -> Workflow:
    wf = REGISTRY.get(key)
    if wf is None:
        raise KeyError(f"Unknown workflow '{key}'. Known: {list(REGISTRY)}")
    return wf
