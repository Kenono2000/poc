import os
import yaml
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from ..tools.tools import DriveRelocationAnalyzerTool
from crewai_tools import SerperDevTool, WebsiteSearchTool

# Get the path to the config directory relative to this file
CONFIG_DIR = Path(__file__).parent.parent / "config"

def load_yaml_config(config_path: str) -> dict:
	"""Load YAML configuration file and return as dictionary"""
	with open(config_path, 'r') as f:
		return yaml.safe_load(f)

@CrewBase
class MyCrew():
	"""MyCrew crew"""
	tasks_config = str(CONFIG_DIR / 'tasks.yaml')

	@agent
	def researcher(self) -> Agent:
		return Agent(
			role="Senior Research Analyst",
			goal="Discover innovative developments and emerging trends in technology",
			backstory="You are an expert analyst at a leading tech think tank. Your specialty is finding cutting-edge developments in AI and synthesizing complex information into actionable insights.",
			verbose=True,
			allow_delegation=False
		)

	@agent
	def writer(self) -> Agent:
		return Agent(
			role="Tech Content Strategist",
			goal="Craft compelling, accessible content on technical advancements",
			backstory="You are a renowned content strategist known for making complex tech topics engaging and understandable for diverse audiences.",
			verbose=True,
			allow_delegation=False
		)

	@agent
	def web_researcher(self) -> Agent:
		return Agent(
			role="Research Specialist",
			goal="Find accurate, up-to-date information using web search",
			backstory="Expert researcher with access to real-time web data. You excel at finding relevant, credible sources and summarizing findings efficiently.",
			tools=[SerperDevTool(), WebsiteSearchTool()],
			verbose=True
		)

	@agent
	def drive_analyst(self) -> Agent:
		return Agent(
			role="Senior Storage Analyst",
			goal="Identify safe data relocation opportunities to optimize storage infrastructure",
			backstory="You are an expert storage administrator who specializes in optimizing disk space by identifying relocatable folders and files. You prioritize safety and provide clear, actionable recommendations.",
			tools=[DriveRelocationAnalyzerTool()],
			verbose=True,
			allow_delegation=False
		)

	@agent
	def relocation_specialist(self) -> Agent:
		return Agent(
			role="Data Migration Specialist",
			goal="Provide step-by-step data migration instructions",
			backstory="You are a data migration expert who creates detailed, easy-to-follow guides for moving data between storage systems. You always include safety checks and rollback procedures.",
			verbose=True,
			allow_delegation=False
		)

	@agent
	def report_writer(self) -> Agent:
		return Agent(
			role="Technical Documentation Writer",
			goal="Create clear, user-friendly technical documentation for complex systems",
			backstory="You translate complex technical analysis into user-friendly guides that help non-technical users safely execute technical procedures.",
			verbose=True,
			allow_delegation=False
		)

	@agent
	def job_researcher(self) -> Agent:
		return Agent(
			role="Senior Technical Job Search Agent",
			goal="Find and evaluate senior-level engineering roles against strict criteria",
			backstory="""You are a ruthless, efficiency-obsessed job search specialist. 
			You treat the candidate's time as sacred and apply hard filtering gates before 
			any evaluation. You specialize in AI Platform Engineering roles and know the 
			difference between genuine IC architecture positions and customer-facing 
			disguised roles. You score objectively and flag disqualifiers without mercy.""",
			tools=[SerperDevTool(), WebsiteSearchTool()],
			verbose=True,
			allow_delegation=False
		)

	@task
	def research_task(self) -> Task:
		return Task(
			config=self.tasks_config,
			description="Research innovative developments in technology",
			expected_output="Detailed research findings on emerging tech trends",
			agent=self.researcher()
		)

	@task
	def writing_task(self) -> Task:
		return Task(
			config=self.tasks_config,
			description="Write compelling content on technical advancements",
			expected_output="Well-structured, engaging content for diverse audiences",
			agent=self.writer()
		)

	@task
	def crewai_news_task(self) -> Task:
		return Task(
			config=self.tasks_config,
			description="Find accurate, up-to-date information on CrewAI news",
			expected_output="Comprehensive summary of latest CrewAI developments",
			agent=self.web_researcher()
		)

	@task
	def analysis_task(self) -> Task:
		return Task(
			config=self.tasks_config,
			description="Analyze drive relocation opportunities",
			expected_output="Safe data relocation recommendations with risk assessment",
			agent=self.drive_analyst()
		)

	@task
	def guide_task(self) -> Task:
		return Task(
			config=self.tasks_config,
			description="Provide data migration instructions",
			expected_output="Step-by-step migration guide with safety checks",
			agent=self.relocation_specialist()
		)

	@task
	def summary_task(self) -> Task:
		return Task(
			config=self.tasks_config,
			description="Create technical documentation",
			expected_output="Clear, user-friendly technical guide",
			agent=self.report_writer()
		)

	@task
	def linkedin_job_task(self) -> Task:
		return Task(
			config=self.tasks_config,
			description="Find and evaluate senior-level engineering roles",
			expected_output="Scored job opportunities with detailed evaluation",
			agent=self.job_researcher()
		)

	@crew
	def ai_research_crew(self) -> Crew:
		"""Creates the AI Research crew"""
		return Crew(
			agents=[self.researcher(), self.writer()],
			tasks=[self.research_task(), self.writing_task()],
			process=Process.sequential,
			verbose=True,
		)

	@crew
	def crewai_news_crew(self) -> Crew:
		"""Creates the CrewAI News crew"""
		return Crew(
			agents=[self.web_researcher()],
			tasks=[self.crewai_news_task()],
			verbose=True,
		)

	@crew
	def relocation_crew(self) -> Crew:
		"""Creates the Relocation crew"""
		return Crew(
			agents=[self.drive_analyst, self.relocation_specialist, self.report_writer],
			tasks=[self.analysis_task(), self.guide_task(), self.summary_task()],
			process=Process.sequential,
			verbose=True,
		)

	@crew
	def linkedin_job_crew(self) -> Crew:
		"""Creates the LinkedIn Job crew"""
		return Crew(
			agents=[self.job_researcher()],
			tasks=[self.linkedin_job_task()],
			verbose=True,
		)
