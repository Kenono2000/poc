import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()
BASE_URL = "https://google.serper.dev"

# Serper doesn't have a "models" endpoint like LLM providers.
# Instead, we test the various search "engines" or endpoints it provides.
SEARCH_TYPES = [
    "search",
    "images",
    "news",
    "places",
    "videos",
    "scholar",
    "maps"
]

# Test configuration
TEST_QUERY = "test"
TIMEOUT_SECONDS = 10
MAX_CONCURRENT_TESTS = 3

def verify_api_key():
    if not SERPER_API_KEY:
        print("[ERROR] SERPER_API_KEY is missing.")
        print("Please set it in your .env file or environment: export SERPER_API_KEY='your-key'")
        sys.exit(1)

def test_single_endpoint(search_type):
    """Sends a minimal search request to test endpoint availability."""
    url = f"{BASE_URL}/{search_type}"
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "q": TEST_QUERY,
        "num": 1
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            url, 
            headers=headers, 
            json=payload, 
            timeout=TIMEOUT_SECONDS
        )
        latency = round(time.time() - start_time, 2)
        
        if response.status_code == 200:
            res_json = response.json()
            # Try to get a snippet of result
            try:
                if search_type == "places":
                    result_count = len(res_json.get("places", []))
                else:
                    result_count = len(res_json.get("organic", res_json.get("images", res_json.get("news", []))))
                
                return {
                    "model": search_type,
                    "status": "RESPONDED",
                    "latency": f"{latency}s",
                    "code": 200,
                    "output": f"Found {result_count} results"
                }
            except:
                return {
                    "model": search_type,
                    "status": "RESPONDED",
                    "latency": f"{latency}s",
                    "code": 200,
                    "output": "Success (Generic)"
                }
        else:
            # Attempt to extract a cleaner error message
            try:
                error_data = response.json()
                error_msg = error_data.get("message", response.text)
            except:
                error_msg = response.text

            return {
                "model": search_type,
                "status": "FAILED",
                "latency": f"{latency}s",
                "code": response.status_code,
                "output": str(error_msg).replace("\n", " ")[:100]
            }
            
    except requests.exceptions.Timeout:
        return {
            "model": search_type,
            "status": "TIMEOUT",
            "latency": f">{TIMEOUT_SECONDS}s",
            "code": 408,
            "output": "Request timed out"
        }
    except (requests.exceptions.RequestException, ValueError) as e:
        return {
            "model": search_type,
            "status": "ERROR",
            "latency": "N/A",
            "code": "N/A",
            "output": str(e)[:50]
        }

def run_tests(engines):
    """Tests all endpoints concurrently and prints formatted summary."""
    print(f"Testing {len(engines)} Serper search engines for responsiveness...\n")
    
    results = []
    
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TESTS) as executor:
        future_to_engine = {
            executor.submit(test_single_endpoint, engine): engine for engine in engines
        }
        
        for future in as_completed(future_to_engine):
            res = future.result()
            results.append(res)
            
            # Real-time console output
            status_tag = f"[{res['status']}]".ljust(12)
            print(f"{status_tag} | Latency: {res['latency'].rjust(6)} | Engine: {res['model']}")

    # Print Summary Report
    print("\n" + "="*80)
    print(" SERPER SUMMARY RESULTS")
    print("="*80)
    
    responded = [r for r in results if r['status'] == 'RESPONDED']
    failed = [r for r in results if r['status'] != 'RESPONDED']
    
    print(f"Total Tested : {len(results)}")
    print(f"Responded    : {len(responded)}")
    print(f"Failed/Error : {len(failed)}")
    print("="*80)
    
    if responded:
        print("\nWorking Engines:")
        for r in sorted(responded, key=lambda x: x['model']):
            print(f"  • {r['model']} ({r['latency']}) -> {r['output']}")
    
    if failed:
        print("\nFailed Engines:")
        for r in failed:
            print(f"  • {r['model']} -> Error {r['code']}: {r['output']}")

if __name__ == "__main__":
    verify_api_key()
    run_tests(SEARCH_TYPES)
