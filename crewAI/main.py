from src.my_crew.crews.my_crews import MyCrew
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

WORKFLOW_FLAGS = {
    "ai_research": os.getenv("WORKFLOW_AI_RESEARCH", "false").lower() in ("true", "1", "yes"),
    "crewai_news": os.getenv("WORKFLOW_CREWAI_NEWS", "false").lower() in ("true", "1", "yes"),
    "relocation": os.getenv("WORKFLOW_RELOCATION", "false").lower() in ("true", "1", "yes"),
    "linkedin_jobs": os.getenv("WORKFLOW_LINKEDIN_JOBS", "false").lower() in ("true", "1", "yes"),
}

# Instantiate the crew project
my_crew_project = MyCrew()

def run_ai_research():
    if not WORKFLOW_FLAGS["ai_research"]:
        print("⚠️  AI Research workflow is disabled (WORKFLOW_AI_RESEARCH=false).")
        return
    result = my_crew_project.ai_research_crew().kickoff()
    print("\n\n=== FINAL RESULT ===\n\n")
    print(result)

def run_crewai_news():
    if not WORKFLOW_FLAGS["crewai_news"]:
        print("⚠️  CrewAI News workflow is disabled (WORKFLOW_CREWAI_NEWS=false).")
        return
    result = my_crew_project.crewai_news_crew().kickoff()
    print(result)

def run_relocation_analyzer():
    if not WORKFLOW_FLAGS["relocation"]:
        print("⚠️  Drive Relocation workflow is disabled (WORKFLOW_RELOCATION=false).")
        return
    print("\n" + "=" * 80)
    print("🚀 DRIVE RELOCATION ANALYZER")
    print("=" * 80)
    print("\n⚠️  SAFETY MODE: This tool will ONLY analyze and recommend.")
    print("⚠️  NO FILES WILL BE MOVED OR DELETED automatically.\n")
    print("📊 Starting analysis...\n")

    result = my_crew_project.relocation_crew().kickoff()

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
    if not WORKFLOW_FLAGS["linkedin_jobs"]:
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

    result = my_crew_project.linkedin_job_crew().kickoff()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"job_search_results_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(str(result))

    print("\n\n" + "=" * 80)
    print("✅ JOB SEARCH COMPLETE")
    print("=" * 80)
    print(result)
    print("=" * 80 + "\n")
    print(f"📄 Results saved to: {filename}\n")

WORKFLOWS = {
    "1": ("AI Agent Frameworks Research & Article", run_ai_research),
    "2": ("CrewAI News Research", run_crewai_news),
    "3": ("Drive Relocation Analyzer", run_relocation_analyzer),
    "4": ("LinkedIn Job Search", run_linkedin_job_search),
}


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
