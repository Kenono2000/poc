"""Workflow 3 — Drive Relocation Analyzer."""

from crewai import Crew, Process, Task

from crewai_pro.agents import drive_analyst, relocation_specialist, report_writer
from crewai_pro.workflows import Workflow

KEY = "relocation"
LABEL = "Drive Relocation Analyzer"
FLAG_NAME = "relocation"


def build_crew() -> Crew:
    return Crew(
        agents=[drive_analyst, relocation_specialist, report_writer],
        tasks=[
            Task(
                description=(
                    "Use the Drive Relocation Analyzer tool to scan the C: drive and "
                    "identify folders that can be safely relocated to the D: drive. "
                    "Focus on user profile folders, game installations, development "
                    "environments, and large media files. Generate a comprehensive "
                    "analysis report."
                ),
                expected_output=(
                    "Detailed analysis of relocatable folders with sizes and methods"
                ),
                agent=drive_analyst,
            ),
            Task(
                description=(
                    "Based on the analysis, create a step-by-step relocation guide for "
                    "the top 5 recommendations. Include: what is being relocated, "
                    "estimated space savings, step-by-step instructions, safety "
                    "precautions, and rollback procedures."
                ),
                expected_output=(
                    "Detailed step-by-step relocation guide for top recommendations"
                ),
                agent=relocation_specialist,
            ),
            Task(
                description=(
                    "Create a user-friendly summary document that includes an "
                    "executive summary, total potential space savings, a quick-start "
                    "guide for easiest wins, and a safety checklist before starting."
                ),
                expected_output="User-friendly relocation guide with safety checklists",
                agent=report_writer,
            ),
        ],
        process=Process.sequential,
        verbose=True,
    )


def run():
    line = "=" * 80
    print("\n" + line)
    print("🚀 DRIVE RELOCATION ANALYZER")
    print(line)
    print("\n⚠️  SAFETY MODE: This tool will ONLY analyze and recommend.")
    print("⚠️  NO FILES WILL BE MOVED OR DELETED automatically.\n")
    print("📊 Starting analysis...\n")

    result = build_crew().kickoff()

    print("\n\n" + line)
    print("✅ ANALYSIS COMPLETE")
    print(line)
    print(result)
    print("\n📋 Check these files for detailed information:")
    print("   - drive_relocation_analysis.json")
    print("   - relocation_recommendations.csv")
    print("\n👉 Review all recommendations before relocating anything!")
    print(line + "\n")
    return result


relocation_workflow = Workflow(
    key=KEY,
    label=LABEL,
    flag_name=FLAG_NAME,
    build_crew=build_crew,
    runner=run,
)