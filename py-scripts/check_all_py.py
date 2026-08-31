import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# --- Configuration ---
# Root directory to search for .py files
ROOT_DIR = Path(__file__).parent.parent  # Points to 'poc/' if this script is in 'poc/py-scripts/'
# Scripts to exclude from running
EXCLUDE_FILES = {Path(__file__).name, "__init__.py"}
# Maximum time to wait for a script (seconds)
TIMEOUT = 30

def run_script(script_path: Path):
    """Checks if a python script compiles without running it."""
    start_time = time.time()
    try:
        # Use 'python -m py_compile' to check for syntax errors without executing
        process = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script_path)],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False
        )
        duration = time.time() - start_time
        
        if process.returncode == 0:
            return {
                "path": str(script_path.relative_to(ROOT_DIR.parent)),
                "status": "VALID",
                "duration": f"{duration:.2f}s",
                "error": ""
            }
        else:
            # Extract the actual error message (usually the last few lines of stderr)
            err_lines = process.stderr.strip().split('\n')
            err_msg = err_lines[-1] if err_lines else "Syntax Error"
            return {
                "path": str(script_path.relative_to(ROOT_DIR.parent)),
                "status": "INVALID",
                "duration": f"{duration:.2f}s",
                "error": err_msg
            }

            
    except subprocess.TimeoutExpired:
        return {
            "path": str(script_path.relative_to(ROOT_DIR.parent)),
            "status": "TIMEOUT",
            "duration": f">{TIMEOUT}s",
            "error": f"Exceeded {TIMEOUT}s limit"
        }
    except (OSError, subprocess.SubprocessError) as e:
        return {
            "path": str(script_path.relative_to(ROOT_DIR.parent)),
            "status": "ERROR",
            "duration": "0.00s",
            "error": str(e)
        }

def main():
    print(f"🔍 Compiling Python scripts in: {ROOT_DIR.resolve()}")
    
    # Collect all .py files recursively
    scripts = [
        p for p in ROOT_DIR.rglob("*.py") 
        if p.is_file() and p.name not in EXCLUDE_FILES
    ]
    
    if not scripts:
        print("No Python scripts found.")
        return

    print(f"Found {len(scripts)} scripts. Starting syntax check...\n")
    
    # Using ThreadPoolExecutor for concurrent compilation check
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(run_script, scripts))

    # --- Print Results Table ---
    header = f"{'STATUS':<10} | {'TIME':<10} | {'SCRIPT PATH':<60} | {'SYNTAX ERROR'}"
    print(header)
    print("-" * len(header))
    
    valid = 0
    for r in sorted(results, key=lambda x: x['status'], reverse=True):
        if r['status'] == "VALID":
            valid += 1
        
        print(f"{r['status']:<10} | {r['duration']:<10} | {r['path']:<60} | {r['error']}")

    print("-" * len(header))
    print(f"SUMMARY: {valid}/{len(results)} Valid Scripts | {len(results)-valid} Syntax Errors")


if __name__ == "__main__":
    main()
