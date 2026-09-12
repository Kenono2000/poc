import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
BASE_URL = "https://integrate.api.nvidia.com/v1"

MODELS_ENDPOINT = f"{BASE_URL}/models"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"

# Test configuration
TEST_PROMPT = "Reply with 'OK'."
MAX_TOKENS = 10
TIMEOUT_SECONDS = 10
MAX_CONCURRENT_TESTS = 5  # Prevents hitting rate limits during bulk test

def verify_api_key():
    if not NVIDIA_API_KEY or not NVIDIA_API_KEY.startswith("nvapi-"):
        print("[ERROR] NVIDIA_API_KEY is missing or invalid.")
        print("Please set it in your environment: export NVIDIA_API_KEY='nvapi-...'")
        sys.exit(1)

def get_nvidia_models():
    """Fetches the list of all available models from NVIDIA API Catalog."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json"
    }
    
    print("[1/2] Fetching model catalog from NVIDIA API...")
    try:
        response = requests.get(MODELS_ENDPOINT, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[ERROR] API returned status {response.status_code}")
            print(f"        Message: {response.text[:200]}")
            return []
            
        data = response.json()
        
        # Parse model IDs from standard OpenAI-compatible response format
        models = [model["id"] for model in data.get("data", [])]
        
        if not models:
            print("[WARNING] No models found in the API response.")
            return []
            
        print(f"      Successfully retrieved {len(models)} models.\n")
        return models
    except requests.exceptions.Timeout:
        print("[ERROR] Request to fetch models timed out.")
        return []
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection error occurred. Check your internet or API endpoint.")
        return []
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch model list: {e}")
        return []
    except (KeyError, ValueError, TypeError) as e:
        print(f"[ERROR] Failed to parse model list: {e}")
        return []

def test_single_model(model_id):
    """Sends a minimal inference request to test model availability."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": TEST_PROMPT}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.1
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            CHAT_ENDPOINT, 
            headers=headers, 
            json=payload, 
            timeout=TIMEOUT_SECONDS
        )
        latency = round(time.time() - start_time, 2)
        
        if response.status_code == 200:
            res_json = response.json()
            content = res_json['choices'][0]['message']['content'].strip()
            # Clean newlines for tidy table output
            clean_content = content.replace("\n", " ")[:30] 
            return {
                "model": model_id,
                "status": "RESPONDED",
                "latency": f"{latency}s",
                "code": 200,
                "output": clean_content
            }
        else:
            # Attempt to extract a cleaner error message
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", error_data.get("message", response.text))
            except:
                error_msg = response.text

            return {
                "model": model_id,
                "status": "FAILED",
                "latency": f"{latency}s",
                "code": response.status_code,
                "output": str(error_msg).replace("\n", " ")[:100]
            }
            
    except requests.exceptions.Timeout:
        return {
            "model": model_id,
            "status": "TIMEOUT",
            "latency": f">{TIMEOUT_SECONDS}s",
            "code": 408,
            "output": "Request timed out"
        }
    except (requests.exceptions.RequestException, ValueError) as e:
        return {
            "model": model_id,
            "status": "ERROR",
            "latency": "N/A",
            "code": "N/A",
            "output": str(e)[:50]
        }

def run_tests(models):
    """Tests all models concurrently and prints formatted summary."""
    print(f"[2/2] Testing {len(models)} models for responsiveness (Max Threads: {MAX_CONCURRENT_TESTS})...\n")
    
    results = []
    
    # Run tests in parallel to speed up execution
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TESTS) as executor:
        future_to_model = {
            executor.submit(test_single_model, model): model for model in models
        }
        
        for future in as_completed(future_to_model):
            res = future.result()
            results.append(res)
            
            # Real-time console output
            status_tag = f"[{res['status']}]".ljust(12)
            print(f"{status_tag} | Latency: {res['latency'].rjust(6)} | Model: {res['model']}")

    # Print Summary Report
    print("\n" + "="*80)
    print(" SUMMARY RESULTS")
    print("="*80)
    
    responded = [r for r in results if r['status'] == 'RESPONDED']
    failed = [r for r in results if r['status'] != 'RESPONDED']
    
    print(f"Total Tested : {len(results)}")
    print(f"Responded    : {len(responded)}")
    print(f"Failed/Error : {len(failed)}")
    print("="*80)
    
    if responded:
        print("\nWorking Models:")
        for r in sorted(responded, key=lambda x: x['model']):
            print(f"  • {r['model']} ({r['latency']}) -> Output: {r['output']}")
    
    if failed:
        print("\nTop Failed Models (Sample):")
        # Show unique error messages to avoid spam
        unique_errors = {}
        for r in failed:
            err_key = f"{r['code']}: {r['output']}"
            if err_key not in unique_errors:
                unique_errors[err_key] = r['model']
        
        for err, model in list(unique_errors.items())[:5]:
            print(f"  • {model} -> Error {err}")

if __name__ == "__main__":
    verify_api_key()
    model_list = get_nvidia_models()
    if model_list:
        run_tests(model_list)