from crewai import Agent
from .tools import DriveRelocationAnalyzerTool
from crewai_tools import SerperDevTool, WebsiteSearchTool

# --- Research Agents ---

researcher = Agent(
    role="Senior Research Analyst",
    goal="Discover innovative developments in AI agents",
    backstory="""You are an expert analyst at a leading tech think tank.
    Your specialty is finding cutting-edge developments in AI.""",
    verbose=True,
    allow_delegation=False
)

web_researcher = Agent(
    role="Research Specialist",
    goal="Find accurate, up-to-date information using web search",
    backstory="Expert researcher with access to real-time web data",
    tools=[SerperDevTool(), WebsiteSearchTool()],
    verbose=True
)

# --- Content Agents ---

writer = Agent(
    role="Tech Content Strategist",
    goal="Craft compelling content on tech advancements",
    backstory="""You are a renowned content strategist known for 
    making complex tech topics accessible and engaging.""",
    verbose=True,
    allow_delegation=False
)

report_writer = Agent(
    role="Technical Documentation Writer",
    goal="Create clear relocation guides for end users",
    backstory="""You translate complex storage analysis into user-friendly 
    guides that help non-technical users safely relocate their data.""",
    verbose=True,
    allow_delegation=False
)

# --- Specialist Agents ---

drive_analyst = Agent(
    role="Senior Storage Analyst",
    goal="Identify safe relocation opportunities to optimize drive space",
    backstory="""You are an expert storage administrator who specializes in 
    optimizing disk space by identifying relocatable folders and files. 
    You prioritize safety and provide clear, actionable recommendations.""",
    tools=[DriveRelocationAnalyzerTool()],
    verbose=True,
    allow_delegation=False
)

relocation_specialist = Agent(
    role="Data Migration Specialist",
    goal="Provide step-by-step relocation instructions",
    backstory="""You are a data migration expert who creates detailed, 
    easy-to-follow guides for moving files and folders between drives. 
    You always include safety checks and rollback procedures.""",
    verbose=True,
    allow_delegation=False
)
