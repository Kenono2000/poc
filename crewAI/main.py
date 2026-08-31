from crewai import Task, Crew, Process
from agents import (
    researcher,
    writer,
    web_researcher,
    drive_analyst,
    relocation_specialist,
    report_writer,
)
import os
from dotenv import load_dotenv

load_dotenv()

WORKFLOW_FLAGS = {
    "ai_research": os.getenv("WORKFLOW_AI_RESEARCH", "false").lower() in ("true", "1", "yes"),
    "crewai_news": os.getenv("WORKFLOW_CREWAI_NEWS", "false").lower() in ("true", "1", "yes"),
    "relocation": os.getenv("WORKFLOW_RELOCATION", "false").lower() in ("true", "1", "yes"),
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


WORKFLOWS = {}

if WORKFLOW_FLAGS["ai_research"]:
    WORKFLOWS["1"] = ("AI Agent Frameworks Research & Article", run_ai_research)

if WORKFLOW_FLAGS["crewai_news"]:
    WORKFLOWS["2"] = ("CrewAI News Research", run_crewai_news)

if WORKFLOW_FLAGS["relocation"]:
    WORKFLOWS["3"] = ("Drive Relocation Analyzer", run_relocation_analyzer)


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
