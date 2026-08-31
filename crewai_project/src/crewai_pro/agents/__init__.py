"""Agent definitions, grouped by workflow.

All workflow agents are re-exported here for backward-compatible imports:

    from crewai_pro.agents import researcher, job_researcher, ...
"""

from crewai_pro.agents.jobs import job_researcher
from crewai_pro.agents.news import web_researcher
from crewai_pro.agents.relocation import (
    drive_analyst,
    relocation_specialist,
    report_writer,
)
from crewai_pro.agents.research import researcher, writer

__all__ = [
    "researcher",
    "writer",
    "web_researcher",
    "drive_analyst",
    "relocation_specialist",
    "report_writer",
    "job_researcher",
]