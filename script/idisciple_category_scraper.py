import sys
import os
import json
import time
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

def get_chrome_driver():
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    return webdriver.Chrome(service=ChromeService(), options=chrome_options)

def load_existing_history(history_path):
    if os.path.exists(history_path):
        try:
            with open(history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}

def save_history(history_path, history):
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)

def extract_category_data(driver, category_name, out_dir):
    url = f"https://www.idisciple.org/categories/{category_name}"
    driver.get(url)
    
    # Wait for page to load - look for main content
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(2)  # Small buffer for dynamic content
    except TimeoutException:
        print(f"Timeout loading category page: {category_name}")
        return None
    
    # Extract title/h1
    try:
        title_element = driver.find_element(By.TAG_NAME, "h1")
        title = title_element.text.strip()
    except NoSuchElementException:
        title = category_name.replace("-", " ").title()
    
    # Try to find category description or content
    try:
        # Look for main content area
        content = driver.find_element(By.CSS_SELECTOR, "main, .content, .category-description, .description")
        description = content.text.strip()[:500] if content else ""
    except NoSuchElementException:
        description = ""
    
    # Create output filename
    safe_name = category_name.replace("-", "_")
    output_file = os.path.join(out_dir, f"{safe_name}.json")
    
    data = {
        "category": category_name,
        "url": url,
        "title": title,
        "description": description,
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z")
    }
    
    # Write to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Scraped: {category_name} -> {output_file}")
    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: python idisciple_category_scraper.py <category_url> [--out-dir <dir>] [--history <path>]")
        sys.exit(1)
    
    # Parse arguments - collect all category URLs (first arg or remaining args)
    category_urls = []
    
    # First positional argument could be a category URL
    if sys.argv[1].startswith("https://"):
        category_urls.append(sys.argv[1])
        arg_idx = 2
    else:
        arg_idx = 1
    
    # Parse remaining arguments as category URLs or options
    out_dir = "C:/Users/Ken Wong/Downloads/output"
    history_path = "C:/Users/Ken Wong/Downloads/temp/idisciple_history.json"
    
    i = arg_idx
    while i < len(sys.argv):
        if sys.argv[i] == "--out-dir" and i + 1 < len(sys.argv):
            out_dir = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--history" and i + 1 < len(sys.argv):
            history_path = sys.argv[i + 1]
            i += 2
        else:
            # Treat remaining positional args as category URLs
            if sys.argv[i].startswith("https://"):
                category_urls.append(sys.argv[i])
            i += 1
    
    if not category_urls:
        print("Usage: python idisciple_category_scraper.py <category_url> [--out-dir <dir>] [--history <path>]")
        sys.exit(1)
    
    # Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)
    
    # Load existing history
    history = load_existing_history(history_path)
    
    # Initialize driver
    driver = get_chrome_driver()
    
    try:
        for category_url in category_urls:
            # Extract category name from URL
            category_name = category_url.rstrip("/").split("/")[-1]
            
            # Skip if already scraped
            if category_name in history:
                print(f"Skipping {category_name} - already scraped")
                continue
            
            try:
                extract_category_data(driver, category_name, out_dir)
            except Exception as e:
                print(f"Error scraping {category_name}: {e}")
            
            # Update history after each category
            history[category_name] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            save_history(history_path, history)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()