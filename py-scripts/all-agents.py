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

import os
import glob
import subprocess
import sys

def run_agent_scripts():
    # Get the current directory
    current_dir = os.getcwd()
    
    # Find all files matching 'agent-*.py'
    pattern = os.path.join(current_dir, 'agent-*.py')
    agent_files = glob.glob(pattern)
    
    # Exclude the current script
    current_script = os.path.basename(__file__)
    agent_files = [f for f in agent_files if os.path.basename(f) != current_script]
    
    # Sort the files for consistent order
    agent_files.sort()
    
    print(f"Found {len(agent_files)} agent scripts to run:")
    for file in agent_files:
        print(f"  - {os.path.basename(file)}")
    
    print("\nRunning scripts...\n")
    
    # Run each script
    for file in agent_files:
        print(f"Running {os.path.basename(file)}...")
        try:
            result = subprocess.run([sys.executable, file], capture_output=True, text=True, cwd=current_dir)
            if result.returncode == 0:
                print(f"✓ {os.path.basename(file)} completed successfully")
                if result.stdout:
                    print(f"Output:\n{result.stdout}")
            else:
                print(f"✗ {os.path.basename(file)} failed with return code {result.returncode}")
                if result.stderr:
                    print(f"Error:\n{result.stderr}")
        except Exception as e:
            print(f"✗ {os.path.basename(file)} failed with exception: {e}")
        print("-" * 50)

if __name__ == "__main__":
    run_agent_scripts()