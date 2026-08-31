from crewai import Task
from crewai.agent import Agent

# Example: Define tasks here
def ai_research_task(agent: Agent):
    return Task(
        description="Research the latest developments in AI agent frameworks in 2026. Identify key players, innovations, and trends.",
        expected_output="A comprehensive report with 5 key findings",
        agent=agent,
    )
