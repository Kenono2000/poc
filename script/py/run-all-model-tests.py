import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Define the scripts to run
SCRIPTS = [
    "nvidia-models.py",
    "gemini-models.py",
    "openai-models.py",
    "openrouter-models.py",
    "serper-models.py",
]


def run_script(script_name: str) -> None:
    script_path = SCRIPT_DIR / script_name
    print("\n" + "=" * 80)
    print(f" RUNNING: {script_name}")
    print("=" * 80)

    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        return

    try:
        # Use sys.executable to ensure we use the same python interpreter
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(SCRIPT_DIR),
            check=False,
            text=True,
        )
        if result.returncode != 0:
            print(f"\n[WARNING] {script_name} exited with code {result.returncode}")
    except (OSError, subprocess.SubprocessError) as e:
        print(f"[ERROR] Failed to execute {script_name}: {e}")

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
