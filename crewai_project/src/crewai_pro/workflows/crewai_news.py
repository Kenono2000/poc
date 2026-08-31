"""Workflow 2 — CrewAI / multi-agent news research."""

from crewai import Crew, Task

from crewai_pro.agents import web_researcher
from crewai_pro.workflows import Workflow

KEY = "crewai_news"
LABEL = "CrewAI News Research"
FLAG_NAME = "crewai_news"


def build_crew() -> Crew:
    return Crew(
        agents=[web_researcher],
        tasks=[
            Task(
                description=(
                    "Search the web for the latest news about CrewAI and "
                    "multi-agent systems. Find 3 recent developments."
                ),
                expected_output="Summary of 3 recent developments with sources",
                agent=web_researcher,
            )
        ],
        verbose=True,
    )


def run():
    print("\n--- Running: CrewAI News Research ---\n")
    result = build_crew().kickoff()
    print(result)
    return result


crewai_news_workflow = Workflow(
    key=KEY,
    label=LABEL,
    flag_name=FLAG_NAME,
    build_crew=build_crew,
    runner=run,
)