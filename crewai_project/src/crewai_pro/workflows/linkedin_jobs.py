"""Workflow 4 — LinkedIn Principal/Staff AI Platform job search."""

from datetime import datetime

from crewai import Agent, Crew, Process, Task
from crewai_tools import SerperDevTool

from .base import Workflow

KEY = "linkedin_jobs"
LABEL = "LinkedIn Job Search"
FLAG_NAME = "linkedin_jobs"

job_discovery_scout = Agent(
    role=(
        "Frontier AI Platform & Agentic Systems Talent Scout"
    ),
    goal=(
        "Identify active, high-signal Staff and Principal level engineering opportunities "
        "in Agent Runtimes, AI Gateways, MCP Tooling, and Distributed Systems using "
        "decoupled Boolean queries."
    ),
    backstory=(
        "You are an elite technical sourcing specialist specializing in the frontier AI "
        "infrastructure and distributed systems domain. You know how to bypass recruiter "
        "fluff and target engineering-led job postings on LinkedIn, company "
        "Workday/Greenhouse/Lever portals, and technical job aggregators. You strictly hunt "
        "for individual contributor (IC) roles focusing on autonomous agent execution "
        "environments, model routing, and distributed backend platform architecture."
    ),
    tools=[SerperDevTool()],
    verbose=True,
    allow_delegation=False,
)

compliance_dedup_auditor = Agent(
    role=(
        "Recruitment Pipeline Compliance & Deduplication Auditor"
    ),
    goal=(
        "Enforce strict work-model filtering (100% remote only), deduplicate against the "
        "candidate's Google Sheet tracking tab ('apps'), and ensure no job is presented "
        "more than 3 times."
    ),
    backstory=(
        "You are an uncompromising data integrity auditor. You guarantee that the "
        "candidate's time is never wasted on previously applied companies, stale listings, "
        "or hybrid/on-site positions. You maintain an immutable registry of job appearances "
        "and reject any listing that violates location criteria or the 3-appearance ceiling."
    ),
    verbose=True,
    allow_delegation=False,
)

technical_fit_evaluator = Agent(
    role=(
        "Principal AI Systems Architect & Technical Evaluator"
    ),
    goal=(
        "Rigidly score candidate roles against Ken Wong's 20+ years of distributed systems, "
        "FastMCP servers, Zero-Trust IAM, and in-database RBAC reference architecture."
    ),
    backstory=(
        "You are a veteran distributed systems architect with over two decades of enterprise "
        "infrastructure experience. You evaluate whether a requisition is a genuine "
        "Staff/Principal platform role or just generic prompt engineering / data science. "
        "You enforce rigorous hard gates: 100% Remote, In-House FTE/C2H, Architecture vs "
        "Core ML, and Compensation >= $140,000 USD."
    ),
    verbose=True,
    allow_delegation=False,
)

executive_outreach_strategist = Agent(
    role=(
        "Executive Technical Career Strategist & Dispatcher"
    ),
    goal=(
        "Generate compelling, high-converting recruiter/hiring manager pitch notes (<300 "
        "characters for LinkedIn connection notes, plus comprehensive email templates) and "
        "dispatch the formatted report to kenono2000@gmail.com."
    ),
    backstory=(
        "You write high-impact, peer-to-peer technical outreach for Staff and Principal "
        "engineers. You never use buzzword-laden sales pitches; instead, you lead with "
        "concrete reference architectures (FastMCP gateways, pgvector RAG, zero-trust IAM "
        "boundaries) and immediate business value."
    ),
    verbose=True,
    allow_delegation=False,
)


def build_crew() -> Crew:
    return Crew(
        agents=[
            job_discovery_scout,
            compliance_dedup_auditor,
            technical_fit_evaluator,
            executive_outreach_strategist,
        ],
        tasks=[
            Task(
                description="""
STAGE 1 — DISCOVERY (job_discovery_scout)

You are a senior technical executive recruiter acting on behalf of Ken Wong, a Principal AI
Platform Engineer and Enterprise Solutions Architect. Search EXCLUSIVELY on
linkedin.com/jobs using the following targeted Boolean query. Focus ONLY on jobs posted
within the past 7 days. Exhaust the first 10 pages of results (~100 entries).

### Boolean Query (LinkedIn)
site:linkedin.com/jobs ("Principal AI Platform Engineer" OR "Principal AI Systems
Architect" OR "Staff Software Engineer" OR "Staff Platform Engineer") AND
("Model Context Protocol" OR "FastMCP" OR "MCP" OR "pgvector" OR "AI Gateway" OR "RAG")
AND ("Python" OR ".NET" OR "C#") AND ("Remote" OR "Remote US" OR "100% Remote") NOT
("Consultant" OR "Agency" OR "Staffing" OR "Pre-Sales" OR "Solutions Architect" OR
"PyTorch" OR "RecSys")

### Candidate Profile & Architectural Moats
- Identity & Track: Principal Systems Engineer & AI Platform Architect (20+ years
  high-concurrency backends, enterprise IAM, and applied sovereign GenAI platform
  engineering).
- Target Roles: Principal AI Platform Engineer, Staff Software Engineer (AI
  Infrastructure/Gateway), Enterprise AI Platform Architect.
- Tech Stack (The Enterprise AI Triad):
  * AI Orchestration: FastMCP (Model Context Protocol), pgvector (HNSW), Sovereign RAG,
    LangChain, DSPy, Local LLMs (Ollama/Hermes), Langfuse.
  * Security & IAM: Zero-Trust IAM, Auth0 Multi-Tenant Architecture, OAuth 2.0 PKCE,
    Okta SSO, Shift-Left In-Database RBAC (PostgreSQL GIN-indexed JSONB ?| operator),
    Row-Level Security (RLS).
  * Distributed Backends: Python (FastAPI, Pydantic DTOs, asyncpg), C#/.NET (.NET Core
    through .NET 8/10), Clean Architecture, RabbitMQ Event Sourcing, MongoDB Distributed
    Locking, Docker, Azure Pipelines.
- Live Demos (Primary Differentiators):
  * FastMCP Agent Endpoint: https://enterprise-rag-mcp.fastmcp.app/mcp
  * Interactive UI: https://enterprise-rag-pgvector-rbac.streamlit.app
  * OpenAPI / Swagger: https://enterprise-rag-api-ksez.onrender.com/docs
  * GitHub Source: https://github.com/Kenono2000/enterprise-rag-pgvector-rbac

### Deliverable
Return a raw JSON array (do NOT score yet) of every LinkedIn job result found, using this
schema per entry:

[
  {
    "title": "<Job Title>",
    "company": "<Company Name>",
    "job_url": "<linkedin.com/jobs/view/XXXXX>",
    "location": "<Location string from the posting>",
    "date_posted": "<Date Posted as shown on LinkedIn>",
    "compensation": "<Range or 'Unlisted'>",
    "raw_snippet": "<First 500 chars of the job description>"
  },
  ...
]

Do NOT filter or score at this stage — that is the auditor's job. Just harvest everything
the Boolean query returns within the first 10 pages.
""",
                expected_output=(
                    "A raw JSON array of all LinkedIn job results from the Boolean query "
                    "(~100 entries), each with title, company, job_url, location, "
                    "date_posted, compensation, and raw_snippet."
                ),
                agent=job_discovery_scout,
            ),
            Task(
                description="""
STAGE 2 — COMPLIANCE & DEDUP (compliance_dedup_auditor)

You receive the raw JSON array of job results from Stage 1. Your job is to enforce the
strict compliance filters and deduplicate against the tracking data.

### Hard Gates Applied
**Gate 0: Location & Work Model**
- MUST be 100% Remote (US-based) OR Hybrid located exclusively within Greater Chicago (CST).
- DISQUALIFY: Any role requiring 1+ days onsite outside Greater Chicago (e.g., NYC, SF,
  Seattle, Austin).
- DISQUALIFY: Any role requiring regular client-site or non-local travel (>15%).
- DISQUALIFY: Regional remote postings that explicitly exclude Illinois residents.

**Gate 1: Employment Nature & Business Model**
- MUST be direct-hire, permanent, full-time employee (FTE) on an in-house product or
  internal platform team.
- DISQUALIFY: Third-party staffing agencies, talent brokers, recruiting intermediaries ("for
  our client"), or staff augmentation.
- DISQUALIFY: Consultancies, professional services, digital agencies, systems integrators,
  or client-billable delivery.
- DISQUALIFY: Customer-facing delivery, pre-sales engineering, forward-deployed engineering
  (FDE), or post-sales solutions architecture.
- DISQUALIFY: Pure people-management tracks (Engineering Manager, Director with direct
  reports, hiring/budget administration).

**Dedup Registry Check**
- Query the candidate's Google Sheet "apps" tab to verify the company has NOT already been
  applied to. The sheet URL is: <INSERT_GOOGLE_SHEET_URL_HERE>.
- Maintain an immutable registry of job appearances. Reject any listing whose
  job_url or company has already appeared 3 or more times across all prior search sessions.
- If the Google Sheet URL is not yet configured, flag each entry with
  "[DEDUP-PENDING]" and note it requires manual verification.

### Recency Filter
- MUST be posted within the last 7 days.
- DISQUALIFY: Any posting older than 7 days.

### Deliverable
Return a JSON array of jobs that PASS all compliance filters, using this schema:

[
  {
    "title": "<Job Title>",
    "company": "<Company Name>",
    "job_url": "<linkedin.com/jobs/view/XXXXX>",
    "location": "<Location string>",
    "date_posted": "<Date Posted>",
    "compensation": "<Range or 'Unlisted'>",
    "raw_snippet": "<First 500 chars>",
    "dedup_status": "NEW" | "PENDING_GOOGLE_SHEET_CHECK" | "REJECTED_ALREADY_APPLIED" |
                    "REJECTED_APPEARANCE_CAP",
    "gate_rejections": ["Gate 0: <brief reason>", "Gate 1: <brief reason>"]
  },
  ...
]

Only include entries with dedup_status of "NEW" or "PENDING_GOOGLE_SHEET_CHECK".
Reject any job that fails a hard gate or exceeds the appearance ceiling.
""",
                expected_output=(
                    "A JSON array of compliant job results that passed Gates 0, 1, and 4, "
                    "deduplicated against the Google Sheet registry and 3-appearance ceiling."
                ),
                agent=compliance_dedup_auditor,
            ),
            Task(
                description="""
STAGE 3 — TECHNICAL FIT EVALUATION (technical_fit_evaluator)

You receive the filtered JSON array from Stage 2. For each job, apply the scoring rubric
and hard gates below. If ANY hard gate fails, immediately DISQUALIFY — do not score.

### Hard Gates (reconfirm)
- Gate 0 (Remote / Greater Chicago): ✅ PASS / ❌ FAIL
- Gate 1 (In-House FTE IC): ✅ PASS / ❌ FAIL
- Gate 2 (Platform vs. Core ML): ✅ PASS / ❌ FAIL
  - DISQUALIFY: Core Machine Learning Research, Applied Scientist, Model Training (PyTorch/
    TensorFlow weight training, LLM fine-tuning, quantization/MoE research, PhD/pub reqs).
  - DISQUALIFY: Recommender Systems (RecSys), Search Ranking, tabular predictive modeling.
- Gate 3 (Compensation >= $140k): ✅ PASS / ❌ FAIL / ⚠️ UNLISTED
- Gate 4 (Recency < 7 days): ✅ PASS / ❌ FAIL

### Scoring Rubric (10-Point System)
| Dimension | Weight | Scoring |
| :--- | :--- | :--- |
| Platform & Stack Synergy | 40% | 10/10 = MCP/FastMCP + pgvector/RAG + Python/FastAPI or C#/.NET + Distributed Systems.<br>7/10 = AI Gateway/Platform + Python/Cloud but no direct MCP.<br>0/10 = Core ML training, PyTorch, RecSys, frontend-heavy. |
| Architectural Scope & IC Track | 30% | 10/10 = Hands-on Principal/Staff IC owning core platform runtime and paved roads.<br>7/10 = Senior Staff IC with high governance/advisory focus.<br>0/10 = People management, client delivery, pre-sales. |
| Location & Business Model | 30% | 10/10 = Explicitly 100% Remote or Greater Chicago hybrid at in-house product company.<br>7/10 = Remote US but location tax eligibility requires screen check.<br>0/10 = Agency, consulting, travel >15%, mandatory non-Chicago onsite. |

### Output Format
For each remaining job, produce:

### Job: [Job Title] at [Company Name]
**Job URL:** [linkedin.com/jobs/view/XXXXX]
**Disclosed Base Compensation:** [Range or "Unlisted"]
**Hard Gates Check:**
- Gate 0 (Remote / Chicago): ✅ PASS / ❌ FAIL ([note])
- Gate 1 (In-House FTE IC): ✅ PASS / ❌ FAIL ([note])
- Gate 2 (Platform vs. Core ML): ✅ PASS / ❌ FAIL ([note])
- Gate 3 (Compensation >= $140k): ✅ PASS / ❌ FAIL / ⚠️ UNLISTED
- Gate 4 (Recency < 7 days): ✅ PASS / ❌ FAIL ([date])
**Scorecard:**
| Dimension | Score | Notes |
| :--- | :--- | :--- |
| Platform & Stack Synergy | X/10 | [notes] |
| Architectural Scope & IC Track | X/10 | [notes] |
| Location & Business Model | X/10 | [notes] |
| **Weighted Overall Score** | **X.X / 10** | |
**Verdict:** 🟢 TIER 1 IMMEDIATE PURSUIT (≥9.0) | 🟡 CONDITIONAL PURSUIT (7.5–8.9) | ❌ DISQUALIFIED (<7.5 or any gate failed)
**Strategic Rationale:** [2-3 sentences]

### Summary
Conclude with a ranked summary table of all Tier 1 and Conditional jobs:

| Rank | Company | Title | Score | Tier |
| :--- | :--- | :--- | :--- | :--- |
| 1 | ... | ... | 9.7 | TIER 1 |
| ... | ... | ... | ... | ... |

Jobs scoring below 7.5 or failing any hard gate are EXCLUDED from the summary.
""",
                expected_output=(
                    "A structured evaluation with scorecard, verdict, and strategic rationale "
                    "for each compliant job, plus a ranked summary table of Tier 1 and "
                    "Conditional roles."
                ),
                agent=technical_fit_evaluator,
            ),
            Task(
                description="""
STAGE 4 — OUTREACH & DISPATCH (executive_outreach_strategist)

You receive the scored evaluation from Stage 3. Your job is to generate the final outreach
report and dispatch it via email to kenono2000@gmail.com.

### Deliverables

1. **Tier 1 Outreach Pack** (for each Tier 1 role):
   - LinkedIn connection note (<300 characters): Peer-to-peer, no buzzwords. Lead with
     concrete reference architectures (FastMCP gateways, pgvector RAG, zero-trust IAM
     boundaries) and immediate business value.
   - Email template: Subject line + body (mention FastMCP agent endpoint, pgvector RBAC
     demo, GitHub source).

2. **Conditional Pursuance Notes** (for each Conditional role):
   - Brief gating script to use in initial screens.
   - Recommended follow-up angle.

3. **Dispatch Instructions**:
   Format the complete report as a single markdown document. Since the email recipient is
   kenono2000@gmail.com, provide a pre-addressed email template block at the end with:
   - To: kenono2000@gmail.com
   - Subject: "Job Search Report — [Date]"
   - Body: Executive summary (count of roles, Tier 1 highlights, any blockers).
   - Attachment references: include the ranked summary table and all outreach templates.

### Example Outreach Note Template (<300 chars)
"Hi [Name], saw the [Title] req at [Company] — built a FastMCP agent endpoint with
pgvector RBAC + zero-trust IAM boundary that could accelerate your roadmap. Open to a
15-min chat?"

### Example Email Template
**Subject:** [Job Title] — FastMCP Gateway + pgvector RBAC (Ref: enterprise-rag-pgvector-rbac)

Hi [Hiring Manager Name],

I just submitted my application for the [Job Title] role at [Company]. The focus on
[key technical area from JD] aligns perfectly with my background building sovereign
GenAI platforms at enterprise scale.

My reference implementation (github.com/Kenono2000/enterprise-rag-pgvector-rbac) ships:
- FastMCP agent endpoint: https://enterprise-rag-mcp.fastmcp.app/mcp
- pgvector + RLS-based in-database RBAC for multi-tenant isolation
- Zero-trust IAM boundary (OAuth 2.0 PKCE + Okta SSO) in-front of the LLM gateway

I'd welcome a brief conversation to discuss how this architecture can accelerate
[Company]'s AI platform roadmap.

Best regards,
Ken Wong
Principal AI Systems Architect

### Final Output
Produce the complete dispatch-ready report combining all Tier 1 outreach packs, conditional
notes, and the email template block addressed to kenono2000@gmail.com.
""",
                expected_output=(
                    "A complete, dispatch-ready markdown report: Tier 1 outreach packs with "
                    "LinkedIn notes (<300 chars) and email templates, conditional pursuance "
                    "notes, and a pre-addressed email template block for kenono2000@gmail.com."
                ),
                agent=executive_outreach_strategist,
            ),
        ],
        process=Process.sequential,
        verbose=True,
    )


def run():
    line = "=" * 80
    print("\n" + line)
    print("💼 LINKEDIN JOB SEARCH — PRINCIPAL AI PLATFORM ENGINEERING ROLES")
    print(line)
    print("   Titles: Principal AI Platform Engineer | Principal AI Systems Architect | Staff Software/Platform Engineer")
    print("   Location: 100% Remote (US)")
    print("   Tech: MCP/FastMCP, pgvector, AI Gateway, RAG, Python/.NET/C#")
    print("   Scope: In-house IC only, $140k+ base, no consulting/pre-sales/core ML research")
    print("   Recency: Posted within the last 7 days")
    print("   [Search Depth: First 10 pages / ~100 results]")
    print(line)
    print("   Agents:")
    print("   [1] job_discovery_scout        — LinkedIn Boolean search & raw harvest")
    print("   [2] compliance_dedup_auditor   — Remote gate + Google Sheet dedup + 3-cap")
    print("   [3] technical_fit_evaluator     — Scoring rubric + hard-gate disqualification")
    print("   [4] executive_outreach_strategist — Outreach templates + email to kenono2000@gmail.com")
    print(line + "\n")

    print("🔍 Launching 4-agent sequential crew (Scout → Auditor → Evaluator → Dispatcher)...\n")

    result = build_crew().kickoff()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"job_search_results_{timestamp}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(str(result))

    print("\n\n" + line)
    print("✅ JOB SEARCH COMPLETE")
    print(line)
    print(result)
    print(line + "\n")
    print(f"📄 Results saved to: {filename}")
    print("📧 Dispatch report prepared for kenono2000@gmail.com")
    print(line + "\n")
    return result


linkedin_jobs_workflow = Workflow(
    key=KEY,
    label=LABEL,
    flag_name=FLAG_NAME,
    build_crew=build_crew,
    runner=run,
)
