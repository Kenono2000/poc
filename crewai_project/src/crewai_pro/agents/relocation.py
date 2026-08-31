"""Workflow 3 — Drive relocation agents."""

from crewai import Agent

from crewai_pro.tools import DriveRelocationAnalyzerTool

drive_analyst = Agent(
    role="Senior Storage Analyst",
    goal="Identify safe relocation opportunities to optimize drive space",
    backstory=(
        "You are an expert storage administrator who specializes in optimizing "
        "disk space by identifying relocatable folders and files. You prioritize "
        "safety and provide clear, actionable recommendations."
    ),
    tools=[DriveRelocationAnalyzerTool()],
    verbose=True,
    allow_delegation=False,
)

relocation_specialist = Agent(
    role="Data Migration Specialist",
    goal="Provide step-by-step relocation instructions",
    backstory=(
        "You are a data migration expert who creates detailed, easy-to-follow "
        "guides for moving files and folders between drives. You always include "
        "safety checks and rollback procedures."
    ),
    verbose=True,
    allow_delegation=False,
)

report_writer = Agent(
    role="Technical Documentation Writer",
    goal="Create clear relocation guides for end users",
    backstory=(
        "You translate complex storage analysis into user-friendly guides that "
        "help non-technical users safely relocate their data."
    ),
    verbose=True,
    allow_delegation=False,
)