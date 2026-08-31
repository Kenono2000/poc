"""Workflow 1 — AI Agent Frameworks research + article agents."""

from crewai import Agent

researcher = Agent(
    role="Senior Research Analyst",
    goal="Discover innovative developments in AI agents",
    backstory=(
        "You are an expert analyst at a leading tech think tank. "
        "Your specialty is finding cutting-edge developments in AI."
    ),
    verbose=True,
    allow_delegation=False,
)

writer = Agent(
    role="Tech Content Strategist",
    goal="Craft compelling content on tech advancements",
    backstory=(
        "You are a renowned content strategist known for making complex "
        "tech topics accessible and engaging."
    ),
    verbose=True,
    allow_delegation=False,
)