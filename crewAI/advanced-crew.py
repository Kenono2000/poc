from crewai import Task, Crew, Process
from .agents import web_researcher as researcher

from dotenv import load_dotenv
import os

load_dotenv()

# Tools are initialized in agents.py


# Researcher agent is now imported from .agents


# Task using the tools
research_task = Task(
    description="""Search the web for the latest news about CrewAI 
    and multi-agent systems. Find 3 recent developments.""",
    expected_output="Summary of 3 recent developments with sources",
    agent=researcher
)

crew = Crew(
    agents=[researcher],
    tasks=[research_task],
    verbose=True
)

result = crew.kickoff()
print(result)