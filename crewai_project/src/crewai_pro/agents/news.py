"""Workflow 2 — CrewAI / multi-agent news research agent."""

from crewai import Agent
from crewai_tools import SerperDevTool, WebsiteSearchTool

web_researcher = Agent(
    role="Research Specialist",
    goal="Find accurate, up-to-date information using web search",
    backstory="Expert researcher with access to real-time web data",
    tools=[SerperDevTool(), WebsiteSearchTool()],
    verbose=True,
)
