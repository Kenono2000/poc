from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool, WebsiteSearchTool
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize tools
search_tool = SerperDevTool()  # Requires SERPER_API_KEY in .env
web_tool = WebsiteSearchTool()

# Research Agent with tools
researcher = Agent(
    role="Research Specialist",
    goal="Find accurate, up-to-date information using web search",
    backstory="Expert researcher with access to real-time web data",
    tools=[search_tool, web_tool],
    verbose=True
)

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