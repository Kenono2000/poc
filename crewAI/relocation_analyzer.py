import os
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, ClassVar
from crewai import Task, Crew, Process
from .agents import drive_analyst, relocation_specialist, report_writer
from .tools import DriveRelocationAnalyzerTool

from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Custom Tool moved to tools.py



# Agents are now imported from .agents


# ============================================================
# TASKS
# ============================================================

analysis_task = Task(
    description="""Use the Drive Relocation Analyzer tool to scan the C: drive 
    and identify folders that can be safely relocated to the D: drive.
    Focus on user profile folders, game installations, development environments, 
    and large media files. Generate a comprehensive analysis report.""",
    expected_output="Detailed analysis of relocatable folders with sizes and methods",
    agent=drive_analyst
)

guide_task = Task(
    description="""Based on the analysis, create a step-by-step relocation guide 
    for the top 5 recommendations. Include: what is being relocated, estimated 
    space savings, step-by-step instructions, safety precautions, and rollback procedures.""",
    expected_output="Detailed step-by-step relocation guide for top recommendations",
    agent=relocation_specialist
)

summary_task = Task(
    description="""Create a user-friendly summary document that includes an executive 
    summary, total potential space savings, a quick-start guide for easiest wins, 
    and a safety checklist before starting.""",
    expected_output="User-friendly relocation guide with safety checklists",
    agent=report_writer
)

# ============================================================
# CREATE AND RUN CREW
# ============================================================

crew = Crew(
    agents=[drive_analyst, relocation_specialist, report_writer],
    tasks=[analysis_task, guide_task, summary_task],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 DRIVE RELOCATION ANALYZER")
    print("=" * 80)
    print("\n⚠️  SAFETY MODE: This tool will ONLY analyze and recommend.")
    print("⚠️  NO FILES WILL BE MOVED OR DELETED automatically.\n")
    print("📊 Starting analysis...\n")
    
    result = crew.kickoff()
    
    print("\n\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    print(result)
    print("\n📋 Check these files for detailed information:")
    print("   - drive_relocation_analysis.json")
    print("   - relocation_recommendations.csv")
    print("\n👉 Review all recommendations before relocating anything!")
    print("=" * 80 + "\n")