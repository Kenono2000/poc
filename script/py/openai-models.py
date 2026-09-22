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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
BASE_URL = "https://api.openai.com/v1"
MODELS_ENDPOINT = f"{BASE_URL}/models"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"

# Test configuration
TEST_PROMPT = "Reply with 'OK'."
MAX_TOKENS = 10
TIMEOUT_SECONDS = 15
MAX_CONCURRENT_TESTS = 5 
TEST_LIMIT = 50


def get_openai_models():
    """Fetches the list of all available models from OpenAI API."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    print("[1/2] Fetching model list from OpenAI API...")
    try:
        response = requests.get(MODELS_ENDPOINT, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[ERROR] API returned status {response.status_code}")
            print(f"        Message: {response.text[:200]}")
            return []
            
        data = response.json()
        
        # Parse model IDs from standard OpenAI response format
        models = [model["id"] for model in data.get("data", [])]
        
        # Sort to put GPT models first for better visibility
        models.sort(key=lambda x: (not x.startswith("gpt"), x))
        
        if not models:
            print("[WARNING] No models found in the API response.")
            return []
            
        print(f"      Successfully retrieved {len(models)} models.\n")
        return models
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch model list: {e}")
        return []
    except (KeyError, ValueError, TypeError) as e:
        print(f"[ERROR] Failed to parse model list: {e}")
        return []


def test_single_model(model_id, retries=1):
    """Sends a minimal inference request to test model availability."""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": TEST_PROMPT}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.1
    }
    
    last_error = None
    for attempt in range(retries + 1):
        start_time = time.time()
        try:
            response = requests.post(
                CHAT_ENDPOINT, 
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
                try:
                    content = res_json['choices'][0]['message'].get('content')
                    if content is None:
                        content = ""
                    content = content.strip()
                    # Clean newlines for tidy table output
                    clean_content = content.replace("\n", " ")[:50] 
                    return {
                        "model": model_id,
                        "status": "RESPONDED",
                        "latency": latency,
                        "code": 200,
                        "output": clean_content
                    }
                except (KeyError, IndexError):
                    return {
                        "model": model_id,
                        "status": "UNEXPECTED_FORMAT",
                        "latency": latency,
                        "code": 200,
                        "output": str(res_json)[:100]
                    }
            else:
                # Attempt to extract a cleaner error message
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", response.text)
                except:
                    error_msg = response.text

                return {
                    "model": model_id,
                    "status": "FAILED",
                    "latency": latency,
                    "code": response.status_code,
                    "output": str(error_msg).replace("\n", " ")[:100]
                }
                
        except requests.exceptions.Timeout:
            last_error = {
                "model": model_id,
                "status": "TIMEOUT",
                "latency": TIMEOUT_SECONDS,
                "code": 408,
                "output": "Request timed out"
            }
        except (requests.exceptions.RequestException, ValueError) as e:
            last_error = {
                "model": model_id,
                "status": "ERROR",
                "latency": None,
                "code": "N/A",
                "output": str(e)[:80]
            }
            
    return last_error


def run_tests(models, limit=TEST_LIMIT):
    """Tests all models concurrently and prints formatted summary."""
    if len(models) > limit:
        print(f"[INFO] Limiting test to {limit} of {len(models)} models.\n")
        models_to_test = models[:limit]
    else:
        models_to_test = models

    print(f"[2/2] Testing {len(models_to_test)} models (threads: {MAX_CONCURRENT_TESTS})...\n")
    
    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TESTS) as executor:
        future_to_model = {
            executor.submit(test_single_model, model): model for model in models_to_test
        }
        
        for future in as_completed(future_to_model):
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
        print("\n✅ Working Models:")
        for r in sorted(responded, key=lambda x: x['latency']):
            print(f"  • {r['model']:<55} {r['latency']:>5.2f}s  → {r['output']}")
    
    if failed:
        print("\n❌ Failure Summary (grouped by error):")
        grouped = defaultdict(list)
        for r in failed:
            key = f"{r['code']}: {r['output'][:60]}"
            grouped[key].append(r["model"])
        
        for err, model_list in list(grouped.items())[:10]:
            sample = ", ".join(model_list[:3])
            more = f" (+{len(model_list) - 3} more)" if len(model_list) > 3 else ""
            print(f"  • [{len(model_list)}] {err}")
            print(f"      e.g. {sample}{more}")


if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("[ERROR] OPENAI_API_KEY is missing.")
        sys.exit(1)
    model_list = get_openai_models()
    if model_list:
        run_tests(model_list)
