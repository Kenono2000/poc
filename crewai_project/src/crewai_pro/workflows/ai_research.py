"""Workflow 1 — AI Agent Frameworks Research & Article."""

from crewai import Crew, Process, Task

from crewai_pro.agents import researcher, writer
from .base import Workflow

KEY = "ai_research"
LABEL = "AI Agent Frameworks Research & Article"
FLAG_NAME = "ai_research"


def build_crew() -> Crew:
    return Crew(
        agents=[researcher, writer],
        tasks=[
            Task(
                description=(
                    "Research the latest developments in AI agent frameworks in 2026. "
                    "Identify key players, innovations, and trends."
                ),
                expected_output="A comprehensive report with 5 key findings",
                agent=researcher,
            ),
            Task(
                description=(
                    "Using the research findings, write an engaging article about "
                    "the state of AI agents in 2026."
                ),
                expected_output="A 500-word article in markdown format",
                agent=writer,
            ),
        ],
        process=Process.sequential,
        verbose=True,
    )


def run():
    print("\n--- Running: AI Agent Frameworks Research & Article ---\n")
    result = build_crew().kickoff()
    print("\n\n=== FINAL RESULT ===\n\n")
    print(result)
    return result


ai_research_workflow = Workflow(
    key=KEY,
    label=LABEL,
    flag_name=FLAG_NAME,
    build_crew=build_crew,
    runner=run,
)
