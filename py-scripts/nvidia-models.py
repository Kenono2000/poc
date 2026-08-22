import os
import sys
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
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
        response.raise_for_status()
        data = response.json()
        
        # Parse model IDs from standard OpenAI-compatible response format
        models = [model["id"] for model in data.get("data", [])]
        print(f"      Successfully retrieved {len(models)} models.\n")
        return models
    except Exception as e:
        print(f"[ERROR] Failed to fetch model list: {e}")
        sys.exit(1)

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
            return {
                "model": model_id,
                "status": "FAILED",
                "latency": f"{latency}s",
                "code": response.status_code,
                "output": response.text[:50]
            }
            
    except requests.exceptions.Timeout:
        return {
            "model": model_id,
            "status": "TIMEOUT",
            "latency": f">{TIMEOUT_SECONDS}s",
            "code": 408,
            "output": "Request timed out"
        }
    except Exception as e:
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

if __name__ == "__main__":
    verify_api_key()
    model_list = get_nvidia_models()
    if model_list:
        run_tests(model_list)