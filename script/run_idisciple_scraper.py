import subprocess
import sys
import os

categories = [
    "identifying-skills-and-passions",
    "success-to-significance",
    "overcoming-obstacles",
    "developing-a-vision",
    "why-your-purpose-is-important",
    "what-is-your-purpose"
]

out_dir = "C:/Users/Ken Wong/Downloads/output"
history = "C:/Users/Ken Wong/Downloads/temp/idisciple_history.json"

# Ensure directories exist
os.makedirs(out_dir, exist_ok=True)
os.makedirs(os.path.dirname(history), exist_ok=True)

# Run scraper for each category
for category in categories:
    url = f"https://www.idisciple.org/categories/{category}"
    print(f"\n=== Scraping: {category} ===")
    
    cmd = [
        sys.executable,
        "idisciple_category_scraper.py",
        url,
        "--out-dir",
        out_dir,
        "--history",
        history
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"STDOUT: {result.stdout}")
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    
    if result.returncode != 0:
        print(f"Error scraping {category}, return code: {result.returncode}")

print("\n=== All categories processed ===")