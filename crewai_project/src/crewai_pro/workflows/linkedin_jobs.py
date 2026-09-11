"""Workflow 4 — LinkedIn Principal/Staff AI Platform job search."""

from datetime import datetime, timezone

from crewai import Agent, Crew, Process, Task
from crewai_tools import ScrapeWebsiteTool, SerperDevTool

from crewai_pro.tools import EmailDispatchTool, GoogleSheetsTrackerTool

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
    tools=[SerperDevTool(), ScrapeWebsiteTool()],
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
    tools=[GoogleSheetsTrackerTool()],
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
    tools=[EmailDispatchTool()],
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
Platform Engineer and Enterprise Solutions Architect. Search live job sources, prioritizing
open ATS portals (Greenhouse, Lever, Ashby, Workable, JazzHR) and company career pages where
job specs and salary disclosures are fully public and indexable, plus linkedin.com/jobs. Use
the following decoupled Google Boolean query. Focus ONLY on jobs posted or reposted within the
past 30 days, prioritizing the last 24–48 hours. When high-signal protocol or runtime terms
are present, do not add a programming-language filter; allow Python, Go, Java, C#, and
TypeScript.

### Target ATS Portals
Prefer results from these indexable job boards; they surface the full posting
text and salary band so the auditor and evaluator can apply the hard gates:
- site:boards.greenhouse.io
- site:jobs.lever.co
- site:jobs.ashbyhq.com
- site:workable.com
- site:jazzhr.com
- careers pages of FAANG+ and high-growth AI infra companies

### Boolean Query (Google-native, no NOT-grouping)
("Staff" OR "Principal") AND ("Software Engineer" OR "Platform Engineer"
OR "AI Architect") AND ("Model Context Protocol" OR "FastMCP" OR "MCP"
OR "Agentic" OR "AI Gateway" OR "Agent Runtime") AND ("100% Remote"
OR "Remote US") -Consultant -Agency -Staffing -Recruiter -"Pre-Sales"
-On-site -Onsite -"In-office" -"In office" -Contractor -Vendor

### Scraping Protocol
After harvesting the SERP, for every ATS/career-page job link:
1. Call ScrapeWebsiteTool on the job URL.
2. Extract the full description, work model (remote/hybrid/onsite),
   employment type (FTE / C2H / contractor), posting date, and any
   disclosed compensation/salary band.
3. Fold those values into the JSON entry's raw_snippet and compensation
   fields so downstream gates have source evidence.

When high-signal protocol or runtime terms are present, do not add a programming-language
filter; allow Python, Go, Java, C#, and TypeScript.

### Candidate Profile & Architectural Moats
- Identity & Track: Principal Systems Engineer & AI Platform Architect (20+ years
  high-concurrency backends, enterprise IAM, and applied sovereign GenAI platform
  engineering).
- Target Roles: Staff / Principal Software Engineer, Staff / Principal Platform Engineer,
  Principal AI Systems Architect.
- Tech Stack (The Enterprise AI Triad):
  * AI Orchestration: FastMCP (Model Context Protocol), pgvector (HNSW), Sovereign RAG,
    LangChain, DSPy, Local LLMs (Ollama/Hermes), Langfuse.
  * Security & IAM: Zero-Trust IAM, Auth0 Multi-Tenant Architecture, OAuth 2.0 PKCE,
    Okta SSO, Shift-Left In-Database RBAC (PostgreSQL GIN-indexed JSONB ?| operator),
    Row-Level Security (RLS).
  * Distributed Backends: Python (FastAPI, Pydantic DTOs, asyncpg), C#/.NET (.NET Core
    through .NET 8/10), Clean Architecture, RabbitMQ Event Sourcing, MongoDB Distributed
    Locking, Docker, Azure Pipelines.
- Reference Implementation (always include in outreach):
  https://github.com/Kenono2000/enterprise-rag-pgvector-rbac

### Deliverable
Return a raw JSON array (do NOT score yet) of every job result found from the
Boolean query, using this schema per entry. The job_url may be a LinkedIn URL or
any ATS/career-page URL harvested via the Scraping Protocol above.

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

Do NOT filter or score at this stage — that is the auditor's job. Capture source evidence
for work model, employment type, compensation, and posting date whenever available.
""",
                 expected_output=(
                     "A raw JSON array of all job results from the ATS-targeting Boolean "
                     "query (~100 entries), each with title, company, job_url, location, "
                     "date_posted, compensation, and raw_snippet (enriched with scraped "
                     "full-description evidence)."
                 ),
                agent=job_discovery_scout,
            ),
            Task(
                description="""
STAGE 2 — COMPLIANCE & DEDUP (compliance_dedup_auditor)

You receive the raw JSON array of job results from Stage 1. Your job is to enforce the
strict compliance filters and deduplicate against the tracking data.

### Hard Gates Applied (all are mandatory)
**Gate 0: Location & Work Model**
- MUST be 100% Remote in the US/Americas OR located in Greater Chicago.
- DISQUALIFY any mandatory onsite or hybrid requirement outside Greater Chicago, and any
  posting that explicitly excludes Illinois residents from a remote role.

**Gate 1: Employment Nature & Business Model**
- MUST be direct-hire permanent FTE or contract-to-hire (C2H) IC on an in-house product or
  internal platform team.
- DISQUALIFY: Third-party staffing agencies, talent brokers, recruiting intermediaries ("for
  our client"), or staff augmentation.
- DISQUALIFY: Consultancies, professional services, digital agencies, systems integrators,
  or client-billable delivery.
- DISQUALIFY: Customer-facing delivery, pre-sales, forward-deployed engineering, or
  post-sales solutions architecture.
- DISQUALIFY: Pure people-management tracks.

**Gate 2: Technical Focus**
- MUST center on core platform engineering, agent runtimes, AI gateways, distributed
  systems, or developer infrastructure.
- DISQUALIFY pure statistical data science or prompt-only engineering.

**Gate 3: Compensation**
- MUST disclose or provide verified market base salary of at least $140,000 USD. Unlisted
  compensation is not a pass and must be rejected.

**Dedup Registry Check**
- Before presenting any role, call GoogleSheetsTrackerTool with spreadsheet_id
  `1TVBZTkj5cHt2nMXt5aQPtu8f8u0bf2E29ilCKviBLUk` and tab `apps`. Extract every
  existing company name and applied title; reject any role from an existing
  company immediately.
- Maintain an immutable per-job appearance registry across updates. Reject any job
  that has appeared 3 or more times and permanently retire it. Never return a job
  more than 3 times.
- If the Google Sheets tracker cannot be read (credentials missing or sheet
  inaccessible), treat it as a hard BLOCKER: return no roles and report the blocker.
  Do not use a PENDING status as a substitute for deduplication.

### Recency Filter
- MUST be posted or reposted within the last 30 days.
- DISQUALIFY: Any posting older than 30 days or with no reliable recency evidence.

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
    "dedup_status": "NEW" | "REJECTED_ALREADY_APPLIED" |
                    "REJECTED_APPEARANCE_CAP",
    "gate_rejections": ["Gate 0: <brief reason>", "Gate 1: <brief reason>"]
  },
  ...
]

Only include entries with dedup_status of "NEW". Reject any job that fails a hard gate,
belongs to an existing company, or exceeds the appearance ceiling.
""",
                expected_output=(
                    "A JSON array of compliant job results that passed all five hard gates, "
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
- Gate 0 (100% Remote US/Americas or Greater Chicago): ✅ PASS / ❌ FAIL
- Gate 1 (In-House FTE IC): ✅ PASS / ❌ FAIL
- Gate 2 (Platform vs. Core ML): ✅ PASS / ❌ FAIL
  - DISQUALIFY: Core Machine Learning Research, Applied Scientist, Model Training (PyTorch/
    TensorFlow weight training, LLM fine-tuning, quantization/MoE research, PhD/pub reqs).
  - DISQUALIFY: Recommender Systems (RecSys), Search Ranking, tabular predictive modeling.
- Gate 3 (Disclosed/verified base >= $140k): ✅ PASS / ❌ FAIL
- Gate 4 (Posted/reposted within 30 days): ✅ PASS / ❌ FAIL

### Scoring Rubric (10-Point System)
| Dimension | Weight | Scoring |
| :--- | :--- | :--- |
| Platform & Stack Synergy | 40% | 10/10 = MCP/FastMCP + pgvector/RAG + Python/FastAPI or C#/.NET + Distributed Systems.<br>7/10 = AI Gateway/Platform + Python/Cloud but no direct MCP.<br>0/10 = Core ML training, PyTorch, RecSys, frontend-heavy. |
| Architectural Scope & IC Track | 30% | 10/10 = Hands-on Principal/Staff IC owning core platform runtime and paved roads.<br>7/10 = Senior Staff IC with high governance/advisory focus.<br>0/10 = People management, client delivery, pre-sales. |
| Location & Business Model | 20% | 10/10 = Explicitly 100% Remote US/Americas or Greater Chicago at an in-house product company.<br>7/10 = Remote scope needs minor verification.<br>0/10 = Agency, consulting, or mandatory non-Chicago onsite. |
| Compensation & Stage | 10% | 10/10 = Base is $170k–$260k+ with credible equity/stage.<br>7/10 = Base is $140k–$169k or equity/stage is unclear. |

### Output Format
For each remaining job, produce:

### Job: [Job Title] at [Company Name]
**Job URL:** [linkedin.com/jobs/view/XXXXX]
**Disclosed Base Compensation:** [Range or "Unlisted"]
**Hard Gates Check:**
- Gate 0 (Remote US/Americas or Greater Chicago): ✅ PASS / ❌ FAIL ([note])
- Gate 1 (In-House FTE IC): ✅ PASS / ❌ FAIL ([note])
- Gate 2 (Platform vs. Core ML): ✅ PASS / ❌ FAIL ([note])
- Gate 3 (Disclosed/verified base >= $140k): ✅ PASS / ❌ FAIL ([note])
- Gate 4 (Posted/reposted within 30 days): ✅ PASS / ❌ FAIL ([date])
**Scorecard:**
| Dimension | Score | Notes |
| :--- | :--- | :--- |
| Platform & Stack Synergy | X/10 | [notes] |
| Architectural Scope & IC Track | X/10 | [notes] |
| Location & Business Model | X/10 | [notes] |
| Compensation & Stage | X/10 | [notes] |
| **Weighted Overall Score** | **X.X / 10** | |
**Verdict:** 🟢 TIER 1 IMMEDIATE PURSUIT (≥9.0) | 🟡 TIER 2 TRACKING PIPELINE (8.0–8.9) | ❌ DISQUALIFIED (<8.0 or any gate failed)
**Strategic Rationale:** [2-3 sentences]

### Summary
Conclude with a ranked summary table of all Tier 1 and Tier 2 jobs:

| Rank | Company | Title | Score | Tier |
| :--- | :--- | :--- | :--- | :--- |
| 1 | ... | ... | 9.7 | TIER 1 |
| ... | ... | ... | ... | ... |

Jobs scoring below 8.0 or failing any hard gate are EXCLUDED from the summary.
""",
                expected_output=(
                    "A structured evaluation with scorecard, verdict, and strategic rationale "
                    "for each compliant job, plus a ranked summary table of Tier 1 and "
                    "Tier 2 roles."
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
   - Tailored hiring-manager email: subject + body highlighting Ken's 20+ years of
     distributed systems experience and always linking
     https://github.com/Kenono2000/enterprise-rag-pgvector-rbac.

2. **Tier 2 Tracking Notes** (for each Tier 2 role):
   - Brief gating script to use in initial screens.
   - Recommended follow-up angle.

3. **Email Dispatch**:
   Dispatch the formatted digest directly to kenono2000@gmail.com by invoking
   the EmailDispatchTool. Build both a plain-text and a rich-HTML version that
   contain identical information. Construct the message with:
    - To: kenono2000@gmail.com
    - Subject: "Job Search Report — [Date]"
    - Body: Executive summary (count of roles, Tier 1 highlights, any blockers).
    - Body: executive summary, ranked summary table, all outreach templates,
      and blockers.
   Call EmailDispatchTool(recipient=..., subject=..., text_body=...,
   html_body=...) to perform the actual send. If SMTP credentials are missing
   or the send fails, report the blocker explicitly rather than claiming it was
   sent.

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

My reference implementation is https://github.com/Kenono2000/enterprise-rag-pgvector-rbac.
It demonstrates FastMCP tooling, pgvector/RLS-based RBAC for tenant isolation, and
zero-trust IAM boundaries in front of an AI gateway.

I'd welcome a brief conversation to discuss how this architecture can accelerate
[Company]'s AI platform roadmap.

Best regards,
Ken Wong
Principal AI Systems Architect

### Final Output
Produce the complete dispatch-ready report combining all Tier 1 outreach packs, Tier 2
tracking notes, and both plain-text and rich-HTML email blocks addressed to
kenono2000@gmail.com. If actual email dispatch is unavailable, state that explicitly as a
blocker instead of claiming it was sent.
""",
                expected_output=(
                    "A complete, dispatch-ready markdown report: Tier 1 outreach packs with "
                    "LinkedIn notes (<300 chars), hiring-manager emails, Tier 2 notes, and "
                    "matching plain-text and rich-HTML email digest blocks addressed to "
                    "kenono2000@gmail.com."
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
    print("   Recency: Posted or reposted within the last 30 days")
    print("   [Search Depth: First 10 pages / ~100 results]")
    print(line)
    print("   Agents:")
    print("   [1] job_discovery_scout        — ATS Boolean search + ScrapeWebsiteTool harvest")
    print("   [2] compliance_dedup_auditor   — Remote gate + Google Sheets dedup + 3-cap")
    print("   [3] technical_fit_evaluator     — Scoring rubric + hard-gate disqualification")
    print("   [4] executive_outreach_strategist — Outreach templates + EmailDispatchTool dispatch")
    print(line + "\n")

    print("🔍 Launching 4-agent sequential crew (Scout → Auditor → Evaluator → Dispatcher)...\n")

    result = build_crew().kickoff()

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
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
