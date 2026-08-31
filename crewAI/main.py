from crewai import Task, Crew, Process
from agents import (
    researcher,
    writer,
    web_researcher,
    drive_analyst,
    relocation_specialist,
    report_writer,
    job_researcher,
)
import os
from dotenv import load_dotenv

load_dotenv()

WORKFLOW_FLAGS = {
    "ai_research": os.getenv("WORKFLOW_AI_RESEARCH", "false").lower() in ("true", "1", "yes"),
    "crewai_news": os.getenv("WORKFLOW_CREWAI_NEWS", "false").lower() in ("true", "1", "yes"),
    "relocation": os.getenv("WORKFLOW_RELOCATION", "false").lower() in ("true", "1", "yes"),
    "linkedin_jobs": os.getenv("WORKFLOW_LINKEDIN_JOBS", "false").lower() in ("true", "1", "yes"),
}

# ============================================================
# WORKFLOW 1: AI Agent Frameworks Research & Article
# ============================================================

if WORKFLOW_FLAGS["ai_research"]:
    ai_research_task = Task(
        description="""Research the latest developments in AI agent frameworks 
        in 2026. Identify key players, innovations, and trends.""",
        expected_output="A comprehensive report with 5 key findings",
        agent=researcher,
    )

    ai_writing_task = Task(
        description="""Using the research findings, write an engaging article 
        about the state of AI agents in 2026.""",
        expected_output="A 500-word article in markdown format",
        agent=writer,
    )

    ai_crew = Crew(
        agents=[researcher, writer],
        tasks=[ai_research_task, ai_writing_task],
        process=Process.sequential,
        verbose=True,
    )
else:
    ai_crew = None


# ============================================================
# WORKFLOW 2: CrewAI News Research
# ============================================================

if WORKFLOW_FLAGS["crewai_news"]:
    crewai_research_task = Task(
        description="""Search the web for the latest news about CrewAI 
        and multi-agent systems. Find 3 recent developments.""",
        expected_output="Summary of 3 recent developments with sources",
        agent=web_researcher,
    )

    crewai_news_crew = Crew(
        agents=[web_researcher],
        tasks=[crewai_research_task],
        verbose=True,
    )
else:
    crewai_news_crew = None


# ============================================================
# WORKFLOW 3: Drive Relocation Analyzer
# ============================================================

if WORKFLOW_FLAGS["relocation"]:
    analysis_task = Task(
        description="""Use the Drive Relocation Analyzer tool to scan the C: drive 
        and identify folders that can be safely relocated to the D: drive.
        Focus on user profile folders, game installations, development environments, 
        and large media files. Generate a comprehensive analysis report.""",
        expected_output="Detailed analysis of relocatable folders with sizes and methods",
        agent=drive_analyst,
    )

    guide_task = Task(
        description="""Based on the analysis, create a step-by-step relocation guide 
        for the top 5 recommendations. Include: what is being relocated, estimated 
        space savings, step-by-step instructions, safety precautions, and rollback procedures.""",
        expected_output="Detailed step-by-step relocation guide for top recommendations",
        agent=relocation_specialist,
    )

    summary_task = Task(
        description="""Create a user-friendly summary document that includes an executive 
        summary, total potential space savings, a quick-start guide for easiest wins, 
        and a safety checklist before starting.""",
        expected_output="User-friendly relocation guide with safety checklists",
        agent=report_writer,
    )

    relocation_crew = Crew(
        agents=[drive_analyst, relocation_specialist, report_writer],
        tasks=[analysis_task, guide_task, summary_task],
        process=Process.sequential,
        verbose=True,
    )
else:
    relocation_crew = None


# ============================================================
# WORKFLOW 4: LinkedIn Job Search
# ============================================================

if WORKFLOW_FLAGS["linkedin_jobs"]:
    linkedin_job_task = Task(
        description="""
        You are a Senior Technical Job Search Agent tasked with finding and evaluating Principal/Staff-level AI Platform Engineering roles on LinkedIn.

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

        ```
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
        ```

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
        expected_output="A filtered, scored list of LinkedIn job postings with Hard Gates check, scorecard, verdict, and next steps for each role. Only roles passing all Hard Gates are included.",
        agent=job_researcher,
    )

    linkedin_job_crew = Crew(
        agents=[job_researcher],
        tasks=[linkedin_job_task],
        verbose=True,
    )
else:
    linkedin_job_crew = None


def run_ai_research():
    if ai_crew is None:
        print("⚠️  AI Research workflow is disabled (WORKFLOW_AI_RESEARCH=false).")
        return
    result = ai_crew.kickoff()
    print("\n\n=== FINAL RESULT ===\n\n")
    print(result)


def run_crewai_news():
    if crewai_news_crew is None:
        print("⚠️  CrewAI News workflow is disabled (WORKFLOW_CREWAI_NEWS=false).")
        return
    result = crewai_news_crew.kickoff()
    print(result)


def run_relocation_analyzer():
    if relocation_crew is None:
        print("⚠️  Drive Relocation workflow is disabled (WORKFLOW_RELOCATION=false).")
        return
    print("\n" + "=" * 80)
    print("🚀 DRIVE RELOCATION ANALYZER")
    print("=" * 80)
    print("\n⚠️  SAFETY MODE: This tool will ONLY analyze and recommend.")
    print("⚠️  NO FILES WILL BE MOVED OR DELETED automatically.\n")
    print("📊 Starting analysis...\n")

    result = relocation_crew.kickoff()

    print("\n\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    print(result)
    print("\n📋 Check these files for detailed information:")
    print("   - drive_relocation_analysis.json")
    print("   - relocation_recommendations.csv")
    print("\n👉 Review all recommendations before relocating anything!")
    print("=" * 80 + "\n")


def run_linkedin_job_search():
    if linkedin_job_crew is None:
        print("⚠️  LinkedIn Job Search workflow is disabled (WORKFLOW_LINKEDIN_JOBS=false).")
        return
    print("\n" + "=" * 80)
    print("💼 LINKEDIN JOB SEARCH — PRINCIPAL AI PLATFORM ENGINEERING ROLES")
    print("=" * 80)
    print("   Titles: Principal AI Architect | Staff AI Engineer | Principal AI Systems Architect | IC5 Principal Engineer")
    print("   Location: 100% Remote (US) or Hybrid in Greater Chicago")
    print("   Scope: In-house IC only, $140k+ base, no consulting/customer-facing")
    print("   Posted: Last 7 days")
    print("=" * 80 + "\n")
    print("🔍 Searching LinkedIn with Hard Gates, scoring rubric, and red-flag filters...\n")

    result = linkedin_job_crew.kickoff()

    print("\n\n" + "=" * 80)
    print("✅ JOB SEARCH COMPLETE")
    print("=" * 80)
    print(result)
    print("=" * 80 + "\n")


WORKFLOWS = {}

if WORKFLOW_FLAGS["ai_research"]:
    WORKFLOWS["1"] = ("AI Agent Frameworks Research & Article", run_ai_research)

if WORKFLOW_FLAGS["crewai_news"]:
    WORKFLOWS["2"] = ("CrewAI News Research", run_crewai_news)

if WORKFLOW_FLAGS["relocation"]:
    WORKFLOWS["3"] = ("Drive Relocation Analyzer", run_relocation_analyzer)

if WORKFLOW_FLAGS["linkedin_jobs"]:
    WORKFLOWS["4"] = ("LinkedIn Job Search", run_linkedin_job_search)


def print_menu():
    print("\n" + "=" * 60)
    print("  CrewAI Combined Workflows")
    print("=" * 60)
    for key, (label, _) in WORKFLOWS.items():
        status = "ON" if _is_enabled(label) else "OFF"
        print(f"  [{key}] {label} ({status})")
    print(f"  [q] Quit")
    print("=" * 60)


def _is_enabled(label):
    flag_map = {
        "AI Agent Frameworks Research & Article": "ai_research",
        "CrewAI News Research": "crewai_news",
        "Drive Relocation Analyzer": "relocation",
        "LinkedIn Job Search": "linkedin_jobs",
    }
    return WORKFLOW_FLAGS.get(flag_map.get(label, ""), True)


if __name__ == "__main__":
    if not WORKFLOWS:
        print("❌ All workflows are disabled. Set at least one WORKFLOW_* env var to 'true'.")
        exit(0)

    while True:
        print_menu()
        choice = input("Select a workflow: ").strip().lower()

        if choice == "q":
            print("Goodbye!")
            break

        if choice in WORKFLOWS:
            label, func = WORKFLOWS[choice]
            print(f"\n--- Running: {label} ---\n")
            func()
        else:
            print("Invalid selection. Please try again.")
