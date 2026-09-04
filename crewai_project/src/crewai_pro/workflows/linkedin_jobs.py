"""Workflow 4 - LinkedIn Principal/Staff AI Platform job search."""

from datetime import datetime

from crewai import Crew, Task

from crewai_pro.agents import job_researcher
from crewai_pro.agents.jobs import JOB_SEARCH_BACKSTORY
from crewai_pro.workflows import Workflow

KEY = "linkedin_jobs"
LABEL = "LinkedIn Job Search"
FLAG_NAME = "linkedin_jobs"


def build_crew() -> Crew:
    return Crew(
        agents=[job_researcher],
        tasks=[
            Task(
                description=JOB_SEARCH_BACKSTORY,
                expected_output=(
                    "A filtered, scored list of LinkedIn job postings with Hard Gates "
                    "check, scorecard, verdict, and next steps for each role. Only "
                    "roles passing all Hard Gates are included."
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
    print(
        "   Titles: Principal AI Architect | Staff AI Engineer | "
        "Principal AI Systems Architect | IC5 Principal Engineer"
    )
    print("   Location: 100% Remote (US) or Hybrid in Greater Chicago")
    print("   Scope: In-house IC only, $140k+ base, no consulting/customer-facing")
    print("   Posted: Last 7 days")
    print(line + "\n")
    print("🔍 Searching LinkedIn with Hard Gates, scoring rubric, and red-flag filters...\n")

    result = build_crew().kickoff()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"job_search_results_{timestamp}.txt"
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
