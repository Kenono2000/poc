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
	tasks_config = str(CONFIG_DIR / 'tasks.yaml')

	@agent
	def researcher(self) -> Agent:
		return Agent(
			role="Senior Research Analyst",
			goal="Discover innovative developments in AI agents",
			backstory="You are an expert analyst at a leading tech think tank. Your specialty is finding cutting-edge developments in AI.",
			verbose=True,
			allow_delegation=False
		)

	@agent
	def writer(self) -> Agent:
		return Agent(
			role="Tech Content Strategist",
			goal="Craft compelling content on tech advancements",
			backstory="You are a renowned content strategist known for making complex tech topics accessible and engaging.",
			verbose=True,
			allow_delegation=False
		)

	@agent
	def web_researcher(self) -> Agent:
		return Agent(
			role="Research Specialist",
			goal="Find accurate, up-to-date information using web search",
			backstory="Expert researcher with access to real-time web data",
			tools=[SerperDevTool(), WebsiteSearchTool()],
			verbose=True
		)

	@agent
	def drive_analyst(self) -> Agent:
		return Agent(
			role="Senior Storage Analyst",
			goal="Identify safe relocation opportunities to optimize drive space",
			backstory="You are an expert storage administrator who specializes in optimizing disk space by identifying relocatable folders and files. You prioritize safety and provide clear, actionable recommendations.",
			tools=[DriveRelocationAnalyzerTool()],
			verbose=True,
			allow_delegation=False
		)

	@agent
	def relocation_specialist(self) -> Agent:
		return Agent(
			role="Data Migration Specialist",
			goal="Provide step-by-step relocation instructions",
			backstory="You are a data migration expert who creates detailed, easy-to-follow guides for moving files and folders between drives. You always include safety checks and rollback procedures.",
			verbose=True,
			allow_delegation=False
		)

	@agent
	def report_writer(self) -> Agent:
		return Agent(
			role="Technical Documentation Writer",
			goal="Create clear relocation guides for end users",
			backstory="You translate complex storage analysis into user-friendly guides that help non-technical users safely relocate their data.",
			verbose=True,
			allow_delegation=False
		)

	@agent
	def job_researcher(self) -> Agent:
		return Agent(
			role="Senior Technical Job Search Agent",
			goal="Find and evaluate Principal/Staff-level AI Platform Engineering roles on LinkedIn against strict non-negotiable criteria",
			backstory="""You are a Senior Technical Job Search Agent tasked with finding and evaluating Principal/Staff-level AI Platform Engineering roles on LinkedIn.

Your mission is to identify job opportunities that match the candidate's strict, non-negotiable criteria. You must be ruthless in filtering out unsuitable roles. The candidate values their time and only wants to pursue roles that are a genuine match.

---

### Candidate Profile

**Role:** Principal AI Systems Architect
**Experience:** 20+ years distributed backend systems, 5+ years AI platform architecture

**Core Differentiators:**
- FastMCP (Model Context Protocol) for deterministic agent orchestration
- pgvector + GIN-indexed JSONB for Shift-Left in-database RBAC
- Zero-Trust data isolation for RAG pipelines
- Python/FastAPI and C#/.NET dual-stack backend expertise
- LLM observability and evaluation frameworks (Langfuse)

**Portfolio:** github.com/Kenono2000/enterprise-rag-pgvector-rbac

---

### Non-Negotiable Search Criteria (HARD GATES)

**Gate 0: Location & Work Model (HIGHEST PRIORITY - Immediate Disqualification if not met)**
- ✅ MUST be 100% Remote (US-based) OR
- ✅ MUST be Hybrid in Greater Chicago area
- ❌ IMMEDIATE DISQUALIFY: Any role requiring 2+ days onsite outside Chicago
- ❌ IMMEDIATE DISQUALIFY: Any role requiring >25% travel
- ❌ IMMEDIATE DISQUALIFY: Any role tied to a specific non-Chicago city (NYC, SF, Austin, etc.)

**Gate 1: Employment Nature & Scope (IMMEDIATE DISQUALIFICATION if violated)**
- ✅ MUST be direct-hire, permanent, in-house product/platform engineering
- ✅ MUST be Individual Contributor (IC) role with 0% people management
- ✅ MUST involve hands-on production coding and architecture
- ❌ IMMEDIATE DISQUALIFY: Consulting, agency, staff augmentation
- ❌ IMMEDIATE DISQUALIFY: Customer-facing delivery, pre-sales, post-sales
- ❌ IMMEDIATE DISQUALIFY: Forward Deployed Engineer, Solutions Architect
- ❌ IMMEDIATE DISQUALIFY: Roles with people management responsibilities

**Gate 2: Compensation Baseline**
- ✅ MUST have base salary of $140,000+ (or unlisted but likely to meet)
- ❌ IMMEDIATE DISQUALIFY: Listed base salary below $140,000

---

### Strong Indicators (Green Lights)

**Technical Stack Alignment (Priority order):**
1. **Agentic AI:** FastMCP, MCP, Model Context Protocol, agent orchestration, tool-calling
2. **RAG & Retrieval:** pgvector, vector databases, RAG pipelines, Shift-Left RBAC
3. **Backend Languages:** Python (FastAPI), C# (.NET Core), or both
4. **Distributed Systems:** Kafka, event-driven, microservices, high-throughput
5. **Observability:** Langfuse, LLM evaluation, monitoring
6. **Cloud:** AWS, Azure, or GCP
7. **Containers:** Kubernetes, Docker

**Scope Indicators:**
- Title contains: Principal, Staff, Senior Staff, IC5, Architect (and NOT "Solutions" or "Field")
- Responsibilities mention: architecture ownership, system design, hands-on coding, mentorship
- No mention of: managing people, direct reports, headcount, budget ownership

**Company Indicators:**
- Tech-forward product company (not consulting/services firm)
- Well-funded or established (public, late-stage startup, or profitable private)

---

### Disqualification Signals (Red Lights - Search for These)

**Red Flags in Job Title:**
- "Solutions Architect" (customer-facing)
- "Forward Deployed" (customer-facing)
- "Field Engineer" (customer-facing)
- "Pre-Sales" (sales-facing)
- "Customer Success" (support-facing)
- "Manager" (people management)
- "Director" (usually people management)
- "Consultant" (consulting firm)

**Red Flags in Company Description:**
- "Consulting," "Advisory," "Services," "Digital Engineering"
- "Systems Integrator," "Staffing," "Agency"
- "Professional Services"

**Red Flags in Responsibilities:**
- "Customer engagements," "client delivery," "pre-sales"
- "Billable," "utilization rate," "statement of work"
- "Manage direct reports," "headcount planning," "budget ownership"
- "Partner with clients," "customer-facing," "offshore teams"

**Red Flags in Requirements:**
- "Sales incentive" or "commission" compensation
- "Travel required" (especially >25%)
- "Onsite" or "hybrid" (outside Chicago)
- "Security clearance required" (often requires onsite)

---

### Search Strategy

1. Search LinkedIn for these titles:
   - Principal Engineer, AI Platform
   - Principal AI Architect
   - Staff Software Engineer, AI
   - Principal AI Systems Architect
   - Senior Staff Engineer, AI/ML
   - Principal Software Engineer, AI
   - IC5 Principal Engineer

2. Filter for roles posted in the last 7 days.

3. For each role, apply the Hard Gates first. If any Hard Gate fails, discard immediately.

4. If Hard Gates pass, evaluate against Green Lights and Red Flags.

5. Score each role using the rubric below.

---

### Scoring Rubric (Score out of 10)

| Dimension | Weight | Scoring Criteria |
|-----------|--------|------------------|
| **Stack Synergy** | 40% | 10/10 = FastMCP, pgvector, Python, C#, distributed systems; 7/10 = 2+ matches; 4/10 = 1 match; 0/10 = no matches |
| **Scope & Ownership** | 30% | 10/10 = Principal IC, architecture ownership, hands-on; 7/10 = Senior IC, some leadership; 0/10 = management or customer-facing |
| **Location & Remote** | 30% | 10/10 = Explicitly 100% Remote; 7/10 = Remote with occasional travel; 0/10 = Onsite or hybrid outside Chicago |

---

### Output Format

For each role, provide:

\`\`\`
### Job: [Job Title] at [Company]

**LinkedIn URL:** [URL]

**Hard Gates Check:**
- Gate 0 (Remote): ✅ PASS / ❌ FAIL
- Gate 1 (In-House IC): ✅ PASS / ❌ FAIL
- Gate 2 (Compensation): ✅ PASS / ❌ FAIL

**Scorecard:**
| Dimension | Score | Notes |
|-----------|-------|-------|
| Stack Synergy | X/10 | [Brief notes] |
| Scope & Ownership | X/10 | [Brief notes] |
| Location & Remote | X/10 | [Brief notes] |
| TOTAL | X/10 | |

**Verdict:** TIER 1 IMMEDIATE ATTACK / CONDITIONAL PURSUIT / IMMEDIATE DISQUALIFICATION

**Reason:** [1-2 sentences]

**Next Step:** [ATS Drop / Outreach to Hiring Manager / Archive]
\`\`\`

---

### Special Instructions

- Be aggressive with disqualifications. If in doubt, flag it for review.
- For roles with unlisted compensation, mark as "⚠️ Unknown" but do not automatically disqualify if the role passes Gates 0 and 1.
- For roles with "hybrid" in Chicago, mark as conditional pass with note to confirm.
- Flag roles that mention MCP, FastMCP, or Model Context Protocol—these are high priority.
- Flag roles that mention pgvector, vector databases, or Shift-Left RBAC—these are high priority.
- If a role is a clear match (score 8.0+), provide the outreach message template.

---

### Example Outreach Message Template

For Tier 1 roles:

**Subject:** [Job Title] Application – [Candidate's Niche Expertise]

Hi [Hiring Manager Name],

I just submitted my application for the [Job Title] role at [Company]. The focus on [key technical area from JD] aligns perfectly with my background in [candidate's expertise].

I specialize in [candidate's core differentiator]. Reference implementation: github.com/Kenono2000/enterprise-rag-pgvector-rbac

I would welcome a brief conversation to discuss how my expertise can accelerate [Company's] roadmap.

Best regards,
Ken Wong
Principal AI Systems Architect

---

### Begin Search

Search LinkedIn for roles matching the criteria above. Apply the Hard Gates first, then evaluate and score each role. Return results in the specified output format.
""",
			tools=[SerperDevTool(), WebsiteSearchTool()],
			verbose=True,
			allow_delegation=False
		)

	@task
	def research_task(self) -> Task:
		task = Task(
			config=self.tasks_config['research_task'],
		)
		task.agent = self.researcher()
		return task

	@task
	def writing_task(self) -> Task:
		task = Task(
			config=self.tasks_config['writing_task'],
		)
		task.agent = self.writer()
		return task

	@task
	def crewai_news_task(self) -> Task:
		task = Task(
			config=self.tasks_config['crewai_news_task'],
		)
		task.agent = self.web_researcher()
		return task

	@task
	def analysis_task(self) -> Task:
		task = Task(
			config=self.tasks_config['analysis_task'],
		)
		task.agent = self.drive_analyst()
		return task

	@task
	def guide_task(self) -> Task:
		task = Task(
			config=self.tasks_config['guide_task'],
		)
		task.agent = self.relocation_specialist()
		return task

	@task
	def summary_task(self) -> Task:
		task = Task(
			config=self.tasks_config['summary_task'],
		)
		task.agent = self.report_writer()
		return task

	@task
	def linkedin_job_task(self) -> Task:
		task = Task(
			config=self.tasks_config['linkedin_job_task'],
		)
		task.agent = self.job_researcher()
		return task

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
