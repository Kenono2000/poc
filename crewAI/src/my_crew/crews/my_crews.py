import os
from pathlib import Path
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from ..tools.tools import DriveRelocationAnalyzerTool
from crewai_tools import SerperDevTool, WebsiteSearchTool

# Get the path to the config directory relative to this file
CONFIG_DIR = Path(__file__).parent.parent / "config"

@CrewBase
class MyCrew():
	"""MyCrew crew"""
	agents_config = str(CONFIG_DIR / 'agents.yaml')
	tasks_config = str(CONFIG_DIR / 'tasks.yaml')

	@agent
	def researcher(self) -> Agent:
		return Agent(
			config=self.agents_config['researcher'],
			verbose=True
		)

	@agent
	def writer(self) -> Agent:
		return Agent(
			config=self.agents_config['writer'],
			verbose=True
		)

	@agent
	def web_researcher(self) -> Agent:
		return Agent(
			config=self.agents_config['web_researcher'],
			tools=[SerperDevTool(), WebsiteSearchTool()],
			verbose=True
		)

	@agent
	def drive_analyst(self) -> Agent:
		return Agent(
			config=self.agents_config['drive_analyst'],
			tools=[DriveRelocationAnalyzerTool()],
			verbose=True
		)

	@agent
	def relocation_specialist(self) -> Agent:
		return Agent(
			config=self.agents_config['relocation_specialist'],
			verbose=True
		)

	@agent
	def report_writer(self) -> Agent:
		return Agent(
			config=self.agents_config['report_writer'],
			verbose=True
		)

	@agent
	def job_researcher(self) -> Agent:
		return Agent(
			config=self.agents_config['job_researcher'],
			tools=[SerperDevTool(), WebsiteSearchTool()],
			verbose=True
		)

	@task
	def research_task(self) -> Task:
		return Task(
			config=self.tasks_config['research_task'],
		)

	@task
	def writing_task(self) -> Task:
		return Task(
			config=self.tasks_config['writing_task'],
		)

	@task
	def crewai_news_task(self) -> Task:
		return Task(
			config=self.tasks_config['crewai_news_task'],
		)

	@task
	def analysis_task(self) -> Task:
		return Task(
			config=self.tasks_config['analysis_task'],
		)

	@task
	def guide_task(self) -> Task:
		return Task(
			config=self.tasks_config['guide_task'],
		)

	@task
	def summary_task(self) -> Task:
		return Task(
			config=self.tasks_config['summary_task'],
		)

	@task
	def linkedin_job_task(self) -> Task:
		return Task(
			config=self.tasks_config['linkedin_job_task'],
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
			agents=[self.drive_analyst(), self.relocation_specialist(), self.report_writer()],
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
