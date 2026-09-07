"""Workflow 4 — LinkedIn Principal/Staff AI Platform job search."""

from datetime import datetime

from crewai import Agent, Crew, Task
from crewai_tools import SerperDevTool

from .base import Workflow

KEY = "linkedin_jobs"
LABEL = "LinkedIn Job Search"
FLAG_NAME = "linkedin_jobs"

job_researcher = Agent(
    role="Senior Technical Job Search Agent",
    goal=(
        "Find and evaluate Principal/Staff-level AI Platform Engineering roles "
        "exclusively on LinkedIn against strict non-negotiable criteria"
    ),
    backstory=(
        "You are a rigorous technical recruiter who evaluates roles for Ken Wong, "
        "a Principal AI Systems Architect. Search ONLY on LinkedIn for job postings. "
        "Apply every hard gate in the task, discard weak matches, and return only "
        "evidence-backed evaluations with direct LinkedIn URLs."
    ),
    tools=[SerperDevTool()],
    verbose=True,
)


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
                - Absolute Base Floor: $140,000 USD.
                - DISQUALIFY: Any disclosed base salary ceiling below $140,000.
                - NOTE: If compensation is unlisted, mark as "⚠️ Unlisted (Check in Screen)" and allow passage ONLY if Gates 0, 1, and 2 fully pass.
                **Gate 4: Recency (Freshness)**
                - MUST be posted within the last 7 days.
                - DISQUALIFY: Any posting older than 7 days.
                ---
                ### High-Synergy Priority Indicators (Green Lights)
                - Agent Protocols & Tooling: Explicit mentions of Model Context Protocol (MCP), FastMCP, tool-calling governance, skill registries, or agent-to-agent (A2A) orchestration.
                - Secure Gateway & Governance: Building unified AI Gateways, LLM proxies, token budgeting, audit logging, rate limiting, and prompt injection/firewall boundaries.
                - Storage & Shift-Left RBAC: PostgreSQL, pgvector, HNSW indexing, multi-tenant isolation, Row-Level Security, or database-tier filtering.
                - Stack Match: Python (FastAPI/Pydantic) OR C#/.NET Core backends running on AWS or Azure.
                - Developer Platforms / Paved Roads: Building internal developer platforms (IDP), "golden pathways", or developer acceleration tools.
                ---
                                ### LinkedIn-Only Search Strategy
                                Search EXCLUSIVELY on linkedin.com/jobs using this specific targeted Boolean query. Focus ONLY on jobs posted within the past week (last 7 days). Go through the first 10 pages of results (approximately 100 results) to ensure thorough coverage:
                                1. site:linkedin.com/jobs ("Principal AI Platform Engineer" OR "Principal AI Systems Architect" OR "Staff Software Engineer" OR "Staff Platform Engineer") AND ("Model Context Protocol" OR "FastMCP" OR "MCP" OR "pgvector" OR "AI Gateway" OR "RAG") AND ("Python" OR ".NET" OR "C#") AND ("Remote" OR "Remote US" OR "100% Remote") NOT ("Consultant" OR "Agency" OR "Staffing" OR "Pre-Sales" OR "Solutions Architect" OR "PyTorch" OR "RecSys")


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
                **Job URL:** [Direct LinkedIn Job Posting URL - must be linkedin.com/jobs/view/XXXXX]
                **Disclosed Base Compensation:** [Range or "Unlisted"]
                **Hard Gates Check:**
                - Gate 0 (Remote / Greater Chicago): ✅ PASS / ❌ FAIL ([Brief note])
                - Gate 1 (In-House FTE IC): ✅ PASS / ❌ FAIL ([In-house SaaS vs. Agency/Consulting])
                                - Gate 2 (Platform vs. Core ML): ✅ PASS / ❌ FAIL ([AI Platform vs. Model Training/Research])
                - Gate 3 (Compensation >= $140k): ✅ PASS / ❌ FAIL / ⚠️ UNLISTED
                - Gate 4 (Recency < 7 days): ✅ PASS / ❌ FAIL ([Date Posted])
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
                                ### Special Instructions
                - SEARCH ONLY LINKEDIN. Use the specific query provided in the strategy section.
                                - THOROUGHNESS: You must exhaustively search through the first 10 pages of results (approx. 100 entries) to ensure no matching roles are missed.
                - RECENCY: Ensure you are looking at the "Date Posted" field on LinkedIn. Only include jobs from the last 7 days.
                - Extract the direct LinkedIn job URL (linkedin.com/jobs/view/XXXXX format) from each result.


                - Be aggressive with disqualifications. If a role is a "Core ML" trap (PyTorch/Model Training) or a "Consulting" trap, kill it immediately.
                - For roles with unlisted compensation, mark Gate 3 as "⚠️ UNKNOWN" but do not automatically disqualify if the role passes Gates 0, 1, and 2 and looks like a Principal/Staff level role.
                - Flag roles that explicitly mention MCP, FastMCP, AI Gateway, or Identity for AI Agents—these are absolute gold mines.
                - If a role is a clear match (score 8.0+), provide the tailored outreach message template.

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
                                expected_output=(
                    "A filtered, scored list of LinkedIn job postings according to the specified "
                    "Structured Output Format. Only roles passing all Hard Gates (Location, "
                    "Employment Nature, Technical Discipline, Compensation, and Recency < 7 days) "
                    "are included."
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
    print("   Titles: Principal AI Platform Engineer | Principal AI Systems Architect | Staff Software/Platform Engineer")
    print("   Location: 100% Remote (US)")
    print("   Tech: MCP/FastMCP, pgvector, AI Gateway, RAG, Python/.NET/C#")
    print("   Scope: In-house IC only, $140k+ base, no consulting/pre-sales/core ML research")
    print("   Recency: Posted within the last 7 days")
    print("   [Search Depth: First 10 pages / ~100 results]")

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
