"""Centralised configuration: env loading + workflow flags."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _flag(name: str, default: str = "false") -> bool:
    raw = os.getenv(name, default)
    return raw.strip().lower() in ("true", "1", "yes", "on")


@dataclass(frozen=True)
class WorkflowFlags:
    ai_research: bool
    crewai_news: bool
    relocation: bool
    linkedin_jobs: bool

    def as_dict(self) -> dict[str, bool]:
        return {
            "ai_research": self.ai_research,
            "crewai_news": self.crewai_news,
            "relocation": self.relocation,
            "linkedin_jobs": self.linkedin_jobs,
        }

    def any_enabled(self) -> bool:
        return any(self.as_dict().values())


@lru_cache(maxsize=1)
def flags() -> WorkflowFlags:
    return WorkflowFlags(
        ai_research=_flag("WORKFLOW_AI_RESEARCH"),
        crewai_news=_flag("WORKFLOW_CREWAI_NEWS"),
        relocation=_flag("WORKFLOW_RELOCATION"),
        linkedin_jobs=_flag("WORKFLOW_LINKEDIN_JOBS"),
    )