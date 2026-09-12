import subprocess
import sys
import os

# Define the scripts to run
SCRIPTS = [
    "nvidia-models.py",
    "gemini-models.py",
    "openai-models.py",
    "openrouter-models.py",
    "serper-models.py"
]

def run_script(script_path):
    print("\n" + "="*80)
    print(f" RUNNING: {script_path}")
    print("="*80)
    
    if not os.path.exists(script_path):
        print(f"[ERROR] Script not found: {script_path}")
        return

    try:
        # Use sys.executable to ensure we use the same python interpreter
        result = subprocess.run(
            [sys.executable, script_path],
            check=False,
            text=True
        )
        if result.returncode != 0:
            print(f"\n[WARNING] {script_path} exited with code {result.returncode}")
    except Exception as e:
        print(f"[ERROR] Failed to execute {script_path}: {e}")

def main():
    print("Starting Bulk Model Availability Test...")
    print(f"Found {len(SCRIPTS)} test scripts to execute.")
    
    for script in SCRIPTS:
        run_script(script)
    
    print("\n" + "="*80)
    print(" ALL TESTS COMPLETED")
    print("="*80)

if __name__ == "__main__":
    main()
