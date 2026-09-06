"""Workflow 4 — LinkedIn Principal/Staff AI Platform job search."""

from datetime import datetime

from crewai import Crew, Task

from crewai_pro.agents import job_researcher
from .base import Workflow

KEY = "linkedin_jobs"
LABEL = "LinkedIn Job Search"
FLAG_NAME = "linkedin_jobs"


def build_crew() -> Crew:
    return Crew(
        agents=[job_researcher],
        tasks=[
            Task(
                description="""
                You are a Senior Technical Executive Recruiter & Job Evaluation Agent acting on behalf of Ken Wong, a Principal AI Platform Engineer and Enterprise Solutions Architect.
                Your mission is to identify, filter, and ruthlessly evaluate Staff- and Principal-level in-house AI Platform and Infrastructure engineering roles on LinkedIn. You must eliminate false-positive matches (consulting, pre-sales, core ML research, model training) and prioritize roles where enterprise distributed systems, Zero-Trust IAM, and Model Context Protocol (MCP) tooling converge.
                ---
                ### Candidate Profile & Architectural Moats
                - Identity & Track: Principal Systems Engineer & AI Platform Architect (20+ years high-concurrency backends, enterprise IAM, and applied sovereign GenAI platform engineering).
                - Target Roles: Principal AI Platform Engineer, Staff Software Engineer (AI Infrastructure/Gateway), Enterprise AI Platform Architect.
                - Tech Stack (The Enterprise AI Triad):
                * AI Orchestration: FastMCP (Model Context Protocol), pgvector (HNSW), Sovereign RAG, LangChain, DSPy, Local LLMs (Ollama/Hermes), Langfuse.
                * Security & IAM: Zero-Trust IAM, Auth0 Multi-Tenant Architecture, OAuth 2.0 PKCE, Okta SSO, Shift-Left In-Database RBAC (PostgreSQL GIN-indexed JSONB ?| operator), Row-Level Security (RLS).
                * Distributed Backends: Python (FastAPI, Pydantic DTOs, asyncpg), C#/.NET (.NET Core through .NET 8/10), Clean Architecture, RabbitMQ Event Sourcing, MongoDB Distributed Locking, Docker, Azure Pipelines.
                - Live Demos (Primary Differentiators):
                * FastMCP Agent Endpoint: https://enterprise-rag-mcp.fastmcp.app/mcp
                * Interactive UI: https://enterprise-rag-pgvector-rbac.streamlit.app
                * OpenAPI / Swagger: https://enterprise-rag-api-ksez.onrender.com/docs
                * GitHub Source: https://github.com/Kenono2000/enterprise-rag-pgvector-rbac
                ---
                ### Non-Negotiable Hard Gates (Immediate Disqualification if Failed)
                **Gate 0: Location & Work Model**
                - MUST be 100% Remote (US-based) OR Hybrid located exclusively within Greater Chicago (CST).
                - DISQUALIFY: Any role requiring 1+ days onsite outside Greater Chicago (e.g., NYC, SF, Seattle, Austin).
                - DISQUALIFY: Any role requiring regular client-site or non-local travel (>15%).
                - DISQUALIFY: Regional remote postings that explicitly exclude Illinois residents.
                **Gate 1: Employment Nature & Business Model**
                - MUST be direct-hire, permanent, full-time employee (FTE) on an in-house product or internal platform team.
                - DISQUALIFY: Third-party staffing agencies, talent brokers, recruiting intermediaries ("for our client"), or staff augmentation.
                - DISQUALIFY: Consultancies, professional services, digital agencies, systems integrators, or client-billable delivery (e.g., Capgemini, Sogeti, DataArt, FullStack).
                - DISQUALIFY: Customer-facing delivery, pre-sales engineering, forward-deployed engineering (FDE), or post-sales solutions architecture.
                - DISQUALIFY: Pure people-management tracks (Engineering Manager, Director with direct reports, hiring/budget administration).
                **Gate 2: Technical Discipline (The Anti-Core-ML Filter)**
                - MUST be an AI Platform, Infrastructure, Gateway, or Backend Developer Tools role building runtime software around LLMs.
                - DISQUALIFY: Core Machine Learning Research, Applied Scientist, or Model Training roles requiring PyTorch/TensorFlow weight training, LLM fine-tuning from scratch, quantization/MoE research, or PhD/publication requirements.
                - DISQUALIFY: Recommender Systems (RecSys), Search Ranking (NDCG/MAP), or tabular predictive modeling (XGBoost/Scikit-Learn feature stores).
                **Gate 3: Compensation Baseline**
                - Target Base Salary: $190,000 – $230,000+ USD.
                - Absolute Base Floor: $140,000 USD.
                - DISQUALIFY: Any disclosed base salary ceiling below $140,000.
                - NOTE: If compensation is unlisted, mark as "⚠️ Unlisted (Check in Screen)" and allow passage ONLY if Gates 0, 1, and 2 fully pass.
                ---
                ### High-Synergy Priority Indicators (Green Lights)
                - Agent Protocols & Tooling: Explicit mentions of Model Context Protocol (MCP), FastMCP, tool-calling governance, skill registries, or agent-to-agent (A2A) orchestration.
                - Secure Gateway & Governance: Building unified AI Gateways, LLM proxies, token budgeting, audit logging, rate limiting, and prompt injection/firewall boundaries.
                - Storage & Shift-Left RBAC: PostgreSQL, pgvector, HNSW indexing, multi-tenant isolation, Row-Level Security, or database-tier filtering.
                - Stack Match: Python (FastAPI/Pydantic) OR C#/.NET Core backends running on AWS or Azure.
                - Developer Platforms / Paved Roads: Building internal developer platforms (IDP), "golden pathways", or developer acceleration tools.
                ---
                ### LinkedIn Search Strategy
                Run searches using targeted Boolean queries to isolate platform architecture from model training:
                1. ("Principal Engineer" OR "Staff Engineer" OR "Principal Architect") AND ("AI Platform" OR "AI Infrastructure" OR "AI Gateway") AND ("Remote" OR "Chicago")
                2. ("Staff Software Engineer" OR "Principal Software Engineer") AND ("Model Context Protocol" OR "MCP" OR "FastMCP" OR "Agentic") AND ("Python" OR ".NET") AND ("Remote" OR "Chicago")
                3. ("Principal Solutions Architect" OR "Platform Architect") AND ("Zero Trust" OR "IAM" OR "Governance") AND ("GenAI" OR "LLM") AND ("Remote" OR "Chicago") -NOT "Sales" -NOT "Customer"
                ---
                ### Evaluation Scoring Rubric (10-Point System)
                | Dimension | Weight | Scoring Baseline |
                | :--- | :--- | :--- |
                | **1. Platform & Stack Synergy** | 40% | 10/10 = MCP/FastMCP + pgvector/RAG + Python/FastAPI or C#/.NET + Distributed Systems.<br>7/10 = AI Gateway/Platform + Python/Cloud but no direct MCP.<br>0/10 = Core ML training, PyTorch, RecSys, or frontend-heavy. |
                | **2. Architectural Scope & IC Track** | 30% | 10/10 = Hands-on Principal/Staff IC owning core platform runtime and paved roads.<br>7/10 = Senior Staff IC with high governance/advisory focus.<br>0/10 = People management, client delivery, or pre-sales. |
                | **3. Location & Business Model** | 30% | 10/10 = Explicitly 100% Remote (US/IL approved) or Greater Chicago hybrid at an in-house product company.<br>7/10 = Remote US but location tax eligibility requires screen check.<br>0/10 = Agency, consulting, travel >15%, or mandatory non-Chicago onsite. |
                ---
                ### Structured Output Format
                For each identified role, output the evaluation in this exact schema:
                ### Job: [Job Title] at [Company Name]
                **Job URL:** [Direct Application / LinkedIn Link]
                **Disclosed Base Compensation:** [Range or "Unlisted"]
                **Hard Gates Check:**
                - Gate 0 (Remote / Greater Chicago): ✅ PASS / ❌ FAIL ([Brief note])
                - Gate 1 (In-House FTE IC): ✅ PASS / ❌ FAIL ([In-house SaaS vs. Agency/Consulting])
                - Gate 2 (Platform vs. Core ML): ✅ PASS / ❌ FAIL ([AI Platform vs. Model Training/Research])
                - Gate 3 (Compensation >= $140k): ✅ PASS / ❌ FAIL / ⚠️ UNLISTED
                **Scorecard:**
                | Dimension | Score | Assessment Notes |
                | :--- | :--- | :--- |
                | Platform & Stack Synergy | X/10 | [Assess MCP, RAG, Python/C#, Vector DB, IAM] |
                | Architectural Scope & IC Track | X/10 | [Assess hands-on coding vs. advisory vs. management] |
                | Location & Business Model | X/10 | [Assess remote certainty and in-house platform status] |
                | **Weighted Overall Score** | **X.X / 10** | |
                **Verdict:** 🟢 TIER 1 IMMEDIATE PURSUIT (Score >= 9.0) | 🟡 CONDITIONAL PURSUIT (Score 7.5 - 8.9) | ❌ IMMEDIATE DISQUALIFICATION (Score < 7.5 or Any Gate Failed)
                **Strategic Rationale:** [2-3 sentences explaining technical alignment and potential friction points]
                **Action Item & Outreach:**
                - Recommended Action: [Apply + P2P Message / Screening Gating Script / Discard]
                - Tailored P2P Note (<300 chars for LinkedIn):
                "[Short note highlighting FastMCP + pgvector RBAC demo + Inspira distributed systems]"
                """,
                expected_output=(
                    "A filtered, scored list of LinkedIn job postings according to the specified "
                    "Structured Output Format. Only roles passing all Hard Gates (Location, "
                    "Employment Nature, Technical Discipline, Compensation) are included."
                ),
                agent=job_researcher,
            )
        ],
        verbose=True,
    )


def run():
    line = "=" * 80
    print("\n" + line)
    print("💼 LINKEDIN JOB SEARCH — PRINCIPAL AI PLATFORM ENGINEERING ROLES")
    print(line)
    print("   Titles: Principal AI Platform Engineer | Staff AI Infrastructure | Enterprise AI Platform Architect")
    print("   Location: 100% Remote (US) or Hybrid in Greater Chicago (CST)")
    print("   Scope: In-house IC only, $140k+ base, no consulting/pre-sales/core ML research")
    print("   Posted: Last 7 days")
    print(line + "\n")
    print("🔍 Searching LinkedIn with Hard Gates, scoring rubric, and red-flag filters...\n")

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
    print(f"📄 Results saved to: {filename}\n")
    return result


linkedin_jobs_workflow = Workflow(
    key=KEY,
    label=LABEL,
    flag_name=FLAG_NAME,
    build_crew=build_crew,
    runner=run,
)
