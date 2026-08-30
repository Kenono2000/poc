"""
Ollama Remote Model Health Check

Purpose:
Tests the responsiveness of all models pulled on a remote or local Ollama instance.
This script is useful for verifying that an Ollama server and its models are
operational.

Features:
- Discovers all pulled models from an Ollama server via its API.
- Sends a minimal test prompt to each model concurrently.
- Measures and reports the latency for each model's response.
- Provides a summary of which models are responding and which have failed.
- Configurable Ollama host via environment variable.

Use Case:
- Health-checking a self-hosted Ollama server.
- Verifying model availability after server setup or updates.
- Basic performance testing (latency measurement).

Required:
- A running Ollama instance (local or remote).
- `requests` library (`pip install requests`).

Configuration:
- Set the `OLLAMA_HOST` environment variable to point to your Ollama server.
  (e.g., `export OLLAMA_HOST='http://192.168.1.100:11434'`)
- If not set, it defaults to `http://localhost:11434`.
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent / "py-libraries"))
from utilities import get_ollama_host, get_timeout_seconds, get_retry_attempts

OLLAMA_HOST = get_ollama_host()

# API endpoints
TAGS_ENDPOINT = f"{OLLAMA_HOST}/api/tags"
CHAT_ENDPOINT = f"{OLLAMA_HOST}/api/chat"

# Test configuration
TEST_PROMPT = "Reply with only the word 'OK'."
MAX_TOKENS = 5
MAX_CONCURRENT_TESTS = 5  # Adjust based on your server's capacity

TIMEOUT_SECONDS = get_timeout_seconds()
RETRY_ATTEMPTS = get_retry_attempts()

# --- Functions ---------------------------------------------------------------

def get_ollama_models(source: str = "server"):
    """Fetch model names either from the Ollama server or from the cloud search page."""
    if source == "cloud-page":
        print("[1/2] Discovering cloud models from the Ollama cloud search page...")
        try:
            models = get_cloud_page_models()
            if not models:
                print("[WARN] No cloud models were discovered from the web page.")
                return []
            print(f"      Successfully discovered {len(models)} cloud models from the web page.\n")
            return models
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to fetch the Ollama cloud search page.")
            print(f"        Details: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Failed to parse cloud model list: {e}")
            sys.exit(1)

    print(f"[1/2] Fetching pulled models from {OLLAMA_HOST}...")
    try:
        response = requests.get(TAGS_ENDPOINT, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        models = [model["name"] for model in data.get("models", [])]
        if not models:
            print("[WARN] No models found on the Ollama server. Make sure you have pulled some models (e.g., `ollama pull llama3`).")
            return []
            
        print(f"      Successfully retrieved {len(models)} models.\n")
        return models
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to connect to Ollama at {OLLAMA_HOST}.")
        print(f"        Details: {e}")
        print("        Please ensure Ollama is running and OLLAMA_HOST is set correctly.")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to fetch model list: {e}")
        sys.exit(1)

def test_single_model(model_id: str):
    """Sends a minimal inference request to test a model's availability."""
    headers = {
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": TEST_PROMPT}
        ],
        "stream": False,
        "options": {
            "num_predict": MAX_TOKENS,
            "temperature": 0.1
        }
    }

    for attempt in range(1, RETRY_ATTEMPTS + 1):
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
                content = res_json.get('message', {}).get('content', '').strip()
                # Clean newlines for tidy table output
                clean_content = content.replace("\n", " ")[:30]
                return {
                    "model": model_id,
                    "status": "RESPONDED",
                    "latency": f"{latency}s",
                    "code": 200,
                    "output": clean_content
                }

            error_text = response.text
            try:
                error_text = response.json().get('error', response.text)
            except ValueError:
                pass

            if attempt < RETRY_ATTEMPTS and response.status_code in {500, 503, 504}:
                time.sleep(2)
                continue

            return {
                "model": model_id,
                "status": "FAILED",
                "latency": f"{latency}s",
                "code": response.status_code,
                "output": error_text[:100]
            }

        except requests.exceptions.Timeout:
            if attempt < RETRY_ATTEMPTS:
                time.sleep(2)
                continue
            return {
                "model": model_id,
                "status": "TIMEOUT",
                "latency": f">{TIMEOUT_SECONDS}s",
                "code": 408,
                "output": "Request timed out; model may still be loading or be unavailable"
            }
        except requests.exceptions.RequestException as e:
            return {
                "model": model_id,
                "status": "ERROR",
                "latency": "N/A",
                "code": "N/A",
                "output": str(e)[:100]
            }
        except Exception as e:
            return {
                "model": model_id,
                "status": "ERROR",
                "latency": "N/A",
                "code": "N/A",
                "output": str(e)[:100]
            }

    return {
        "model": model_id,
        "status": "TIMEOUT",
        "latency": f">{TIMEOUT_SECONDS}s",
        "code": 408,
        "output": "Request timed out; model may still be loading or be unavailable"
    }

def run_tests(models: list[str]):
    """Tests all models concurrently and prints a formatted summary."""
    if not models:
        return
        
    print(f"[2/2] Testing {len(models)} models for responsiveness (Max Threads: {MAX_CONCURRENT_TESTS})...\n")
    
    results = []
    
    # Run tests in parallel to speed up execution
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TESTS) as executor:
        future_to_model = {
            executor.submit(test_single_model, model): model for model in models
        }
        
        # Sort futures by model name for deterministic-looking output
        sorted_futures = sorted(future_to_model.keys(), key=lambda f: future_to_model[f])

        for future in as_completed(sorted_futures):
            res = future.result()
            results.append(res)
            
            # Real-time console output
            status_tag = f"[{res['status']}]".ljust(12)
            print(f"{status_tag} | Latency: {res['latency'].rjust(7)} | Model: {res['model']}")

    # --- Print Summary Report ---
    print("\n" + "="*80)
    print(" SUMMARY RESULTS")
    print("="*80)
    
    responded = sorted([r for r in results if r['status'] == 'RESPONDED'], key=lambda x: x['model'])
    failed = sorted([r for r in results if r['status'] != 'RESPONDED'], key=lambda x: x['model'])
    
    print(f"Total Tested : {len(results)}")
    print(f"Responded    : {len(responded)}")
    print(f"Failed/Error : {len(failed)}")
    print("="*80)
    
    if responded:
        print("\n✅ Working Models:")
        for r in responded:
            print(f"  • {r['model']} ({r['latency']}) -> Output: '{r['output']}'")

    if failed:
        print("\n❌ Failed/Errored Models:")
        for r in failed:
            print(f"  • {r['model']} ({r['status']} {r['code']}) -> Details: {r['output']}")

        print("\n💡 Tip: timeouts often mean the model is still loading or unavailable. Try a longer timeout, more retries, or verify the model is pulled locally.")

# --- Entry point -------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check Ollama model responsiveness")
    parser.add_argument("--host", default=None, help="Ollama server URL (for example: https://your-cloud-host)")
    parser.add_argument("--source", default="server", choices=["server", "cloud-page"], help="Where to discover model names from")
    args = parser.parse_args()

    OLLAMA_HOST = get_ollama_host(args.host)
    TAGS_ENDPOINT = f"{OLLAMA_HOST}/api/tags"
    CHAT_ENDPOINT = f"{OLLAMA_HOST}/api/chat"

    print(f"[INFO] Testing Ollama host: {OLLAMA_HOST}")
    model_list = get_ollama_models(args.source)
    if model_list:
        run_tests(model_list)