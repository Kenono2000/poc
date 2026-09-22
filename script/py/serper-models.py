import os
import sys
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

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
TIMEOUT_SECONDS = 15
MAX_CONCURRENT_TESTS = 3


def test_single_endpoint(search_type, retries=1):
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
    
    last_error = None
    for attempt in range(retries + 1):
        start_time = time.time()
        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=TIMEOUT_SECONDS
            )
            latency = round(time.time() - start_time, 2)

            # Retry on transient errors
            if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1 + random.random())
                continue
            
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
                        "latency": latency,
                        "code": 200,
                        "output": f"Found {result_count} results"
                    }
                except:
                    return {
                        "model": search_type,
                        "status": "RESPONDED",
                        "latency": latency,
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
                    "latency": latency,
                    "code": response.status_code,
                    "output": str(error_msg).replace("\n", " ")[:100]
                }
                
        except requests.exceptions.Timeout:
            last_error = {
                "model": search_type,
                "status": "TIMEOUT",
                "latency": TIMEOUT_SECONDS,
                "code": 408,
                "output": "Request timed out"
            }
        except (requests.exceptions.RequestException, ValueError) as e:
            last_error = {
                "model": search_type,
                "status": "ERROR",
                "latency": None,
                "code": "N/A",
                "output": str(e)[:80]
            }
            
    return last_error


def run_tests(engines):
    """Tests all endpoints concurrently and prints formatted summary."""
    print(f"Testing {len(engines)} Serper search engines (threads: {MAX_CONCURRENT_TESTS})...\n")
    
    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TESTS) as executor:
        future_to_engine = {
            executor.submit(test_single_endpoint, engine): engine for engine in engines
        }
        
        for future in as_completed(future_to_engine):
            res = future.result()
            results.append(res)
            
            # Real-time console output - ONLY for working models
            if res['status'] == 'RESPONDED':
                print(f"[RESPONDED]  | {res['latency']:>5.2f}s | {res['model']}")

    # Print Summary Report
    print("\n" + "="*80)
    print(" SUMMARY")
    print("="*80)
    
    responded = [r for r in results if r['status'] == 'RESPONDED']
    failed = [r for r in results if r['status'] != 'RESPONDED']
    
    print(f"Total    : {len(results)}")
    print(f"Responded: {len(responded)}")
    print(f"Failed   : {len(failed)}")
    print("="*80)
    
    if responded:
        print("\n✅ Working Engines:")
        for r in sorted(responded, key=lambda x: x['latency']):
            print(f"  • {r['model']:<20} {r['latency']:>5.2f}s  → {r['output']}")
    
    if failed:
        print("\n❌ Failure Summary (grouped by error):")
        grouped = defaultdict(list)
        for r in failed:
            key = f"{r['code']}: {r['output'][:60]}"
            grouped[key].append(r["model"])
        
        for err, engine_list in list(grouped.items())[:10]:
            sample = ", ".join(engine_list[:3])
            more = f" (+{len(engine_list) - 3} more)" if len(engine_list) > 3 else ""
            print(f"  • [{len(engine_list)}] {err}")
            print(f"      e.g. {sample}{more}")


if __name__ == "__main__":
    if not SERPER_API_KEY:
        print("[ERROR] SERPER_API_KEY is missing.")
        sys.exit(1)
    run_tests(SEARCH_TYPES)
