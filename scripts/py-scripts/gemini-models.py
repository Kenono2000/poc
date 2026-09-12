import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MODELS_ENDPOINT = f"{BASE_URL}/models"

# Test configuration
TEST_PROMPT = "Reply with 'OK'."
MAX_TOKENS = 10
TIMEOUT_SECONDS = 10
MAX_CONCURRENT_TESTS = 5 

def verify_api_key():
    if not GOOGLE_API_KEY:
        print("[ERROR] GOOGLE_API_KEY is missing.")
        print("Please set it in your environment: export GOOGLE_API_KEY='your-api-key'")
        sys.exit(1)

def get_gemini_models():
    """Fetches the list of all available models from Gemini API."""
    params = {"key": GOOGLE_API_KEY}
    
    print("[1/2] Fetching model list from Google Gemini API...")
    try:
        response = requests.get(MODELS_ENDPOINT, params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"[ERROR] API returned status {response.status_code}")
            print(f"        Message: {response.text[:200]}")
            return []
            
        data = response.json()
        
        # Filter for models that support content generation
        models = [
            model["name"] for model in data.get("models", []) 
            if "generateContent" in model.get("supportedGenerationMethods", [])
        ]
        
        if not models:
            print("[WARNING] No models found that support 'generateContent'.")
            return []
            
        print(f"      Successfully retrieved {len(models)} models supporting 'generateContent'.\n")
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

def test_single_model(model_name):
    """Sends a minimal inference request to test model availability."""
    # model_name is usually "models/gemini-1.5-flash"
    url = f"{BASE_URL}/{model_name}:generateContent"
    params = {"key": GOOGLE_API_KEY}
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "contents": [{
            "parts": [{"text": TEST_PROMPT}]
        }],
        "generationConfig": {
            "maxOutputTokens": MAX_TOKENS,
            "temperature": 0.1
        }
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            url, 
            params=params,
            headers=headers, 
            json=payload, 
            timeout=TIMEOUT_SECONDS
        )
        latency = round(time.time() - start_time, 2)
        
        if response.status_code == 200:
            res_json = response.json()
            try:
                # Handle cases where safety filters might block the response
                if 'candidates' not in res_json or not res_json['candidates']:
                    return {
                        "model": model_name,
                        "status": "BLOCKED/EMPTY",
                        "latency": f"{latency}s",
                        "code": 200,
                        "output": "No candidates (Safety filter?)"
                    }
                
                candidate = res_json['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    content = candidate['content']['parts'][0]['text'].strip()
                    # Clean newlines for tidy table output
                    clean_content = content.replace("\n", " ")[:30] 
                    return {
                        "model": model_name,
                        "status": "RESPONDED",
                        "latency": f"{latency}s",
                        "code": 200,
                        "output": clean_content
                    }
                else:
                    finish_reason = candidate.get('finishReason', 'UNKNOWN')
                    return {
                        "model": model_name,
                        "status": f"FINISH_{finish_reason}",
                        "latency": f"{latency}s",
                        "code": 200,
                        "output": str(res_json)[:100]
                    }
            except (KeyError, IndexError):
                return {
                    "model": model_name,
                    "status": "UNEXPECTED_FORMAT",
                    "latency": f"{latency}s",
                    "code": 200,
                    "output": str(res_json)[:100]
                }
        else:
            # Attempt to extract a cleaner error message
            try:
                error_data = response.json()
                # Google often puts errors in a list or nested object
                if isinstance(error_data, list):
                    error_msg = error_data[0].get("message", str(error_data))
                else:
                    error_msg = error_data.get("error", {}).get("message", response.text)
            except:
                error_msg = response.text

            return {
                "model": model_name,
                "status": "FAILED",
                "latency": f"{latency}s",
                "code": response.status_code,
                "output": str(error_msg).replace("\n", " ")[:100]
            }
            
    except requests.exceptions.Timeout:
        return {
            "model": model_name,
            "status": "TIMEOUT",
            "latency": f">{TIMEOUT_SECONDS}s",
            "code": 408,
            "output": "Request timed out"
        }
    except (requests.exceptions.RequestException, ValueError) as e:
        return {
            "model": model_name,
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
    model_list = get_gemini_models()
    if model_list:
        run_tests(model_list)
