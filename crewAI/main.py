from crewai import Task, Crew, Process
from .agents import researcher, writer
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Agents are now imported from .agents


# Define Task 1: Research
research_task = Task(
    description="""Research the latest developments in AI agent frameworks 
    in 2026. Identify key players, innovations, and trends.""",
    expected_output="A comprehensive report with 5 key findings",
    agent=researcher
)

# Define Task 2: Write Article
writing_task = Task(
    description="""Using the research findings, write an engaging article 
    about the state of AI agents in 2026.""",
    expected_output="A 500-word article in markdown format",
    agent=writer
)

# Create the Crew
crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, writing_task],
    process=Process.sequential,
    verbose=True
)

# Run the crew
if __name__ == "__main__":
    result = crew.kickoff()
    print("\n\n=== FINAL RESULT ===\n\n")
    print(result)