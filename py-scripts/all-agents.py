"""
All-Agents Test Runner

Purpose: Automatically discovers and runs all agent-*.py scripts in sequence.
This is useful for testing all agent implementations or running demonstrations.

Features:
- Dynamically discovers all agent-*.py files in current directory
- Runs each script as a subprocess
- Captures output and error messages
- Provides clear feedback on success/failure
- Excludes the runner script itself
- Maintains consistent execution order (alphabetically sorted)

Use Case:
- Testing all agent implementations in one command
- Verification that all agents run without errors
- Demonstration of all agent capabilities
- Automated testing pipeline for agent scripts

Output:
- Console output from each script
- Success/failure status for each agent
- Error messages if any agent fails
"""

import glob
import subprocess
import sys
from pathlib import Path


def run_agent_scripts():
    current_dir = Path(__file__).parent.resolve()
    
    pattern = str(current_dir / "agent-*.py")
    agent_files = [Path(p) for p in glob.glob(pattern)]
    
    current_script = Path(__file__).name
    agent_files = [f for f in agent_files if f.name != current_script]
    
    agent_files.sort(key=lambda p: p.name)
    
    print(f"Found {len(agent_files)} agent scripts to run:")
    for file in agent_files:
        print(f"  - {file.name}")
    
    print("\nRunning scripts...\n")
    
    for file in agent_files:
        print(f"Running {file.name}...")
        try:
            result = subprocess.run(
                [sys.executable, str(file)],
                capture_output=True,
                text=True,
                cwd=str(current_dir),
                check=False
            )
            if result.returncode == 0:
                print(f"✓ {file.name} completed successfully")
                if result.stdout:
                    print(f"Output:\n{result.stdout}")
            else:
                print(f"✗ {file.name} failed with return code {result.returncode}")
                if result.stderr:
                    print(f"Error:\n{result.stderr}")
        except (OSError, subprocess.SubprocessError) as e:
            print(f"✗ {file.name} failed with exception: {e}")
        print("-" * 50)


if __name__ == "__main__":
    run_agent_scripts()