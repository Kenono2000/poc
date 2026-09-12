import os
import sys
import time
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
BASE_URL = "https://openrouter.ai/api/v1"
MODELS_ENDPOINT = f"{BASE_URL}/models"
CHAT_ENDPOINT = f"{BASE_URL}/chat/completions"

TEST_PROMPT = "Reply with 'OK'."
MAX_TOKENS = 10
TIMEOUT_SECONDS = 20
MAX_CONCURRENT_TESTS = 3
TEST_LIMIT = 50
FREE_ONLY = True  # Only test free models


def get_openrouter_models(free_only=False):
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    print("[1/2] Fetching model list from OpenRouter API...")
    try:
        response = requests.get(MODELS_ENDPOINT, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        models = []
        for m in data.get("data", []):
            if free_only:
                pricing = m.get("pricing", {})
                if pricing.get("prompt") != "0" or pricing.get("completion") != "0":
                    continue
            models.append(m["id"])
        
        print(f"      Retrieved {len(models)} models"
              f"{' (free only)' if free_only else ''}.\n")
        return models
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch model list: {e}")
        return []


def test_single_model(model_id, retries=1):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo",
        "X-Title": "Model Tester Script",
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": TEST_PROMPT}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.1,
    }

    last_error = None
    for attempt in range(retries + 1):
        start_time = time.time()
        try:
            response = requests.post(
                CHAT_ENDPOINT, headers=headers, json=payload,
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
                    content = res_json["choices"][0]["message"].get("content")
                    if content is None:
                        content = ""
                    content = content.strip()
                    clean_content = content.replace("\n", " ")[:50]
                    return {
                        "model": model_id,
                        "status": "RESPONDED",
                        "latency": latency,
                        "code": 200,
                        "output": clean_content,
                    }
                except (KeyError, IndexError):
                    return {
                        "model": model_id,
                        "status": "UNEXPECTED_FORMAT",
                        "latency": latency,
                        "code": 200,
                        "output": str(res_json)[:100],
                    }

            try:
                error_data = response.json()
                error_msg = error_data.get("error", {}).get("message", response.text)
            except (ValueError, KeyError):
                error_msg = response.text

            return {
                "model": model_id,
                "status": "FAILED",
                "latency": latency,
                "code": response.status_code,
                "output": str(error_msg).replace("\n", " ")[:100],
            }

        except requests.exceptions.Timeout:
            last_error = {
                "model": model_id, "status": "TIMEOUT",
                "latency": TIMEOUT_SECONDS, "code": 408,
                "output": "Request timed out",
            }
        except requests.exceptions.RequestException as e:
            last_error = {
                "model": model_id, "status": "ERROR",
                "latency": None, "code": "N/A",
                "output": str(e)[:80],
            }

    return last_error


def run_tests(models, limit=TEST_LIMIT):
    if len(models) > limit:
        print(f"[INFO] Limiting test to {limit} of {len(models)} models.\n")
        models_to_test = models[:limit]
    else:
        models_to_test = models

    print(f"[2/2] Testing {len(models_to_test)} models "
          f"(threads: {MAX_CONCURRENT_TESTS})...\n")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TESTS) as executor:
        future_to_model = {
            executor.submit(test_single_model, m): m for m in models_to_test
        }
        for future in as_completed(future_to_model):
            res = future.result()
            results.append(res)
            if res["status"] == "RESPONDED":
                print(f"[RESPONDED]  | {res['latency']:>5.2f}s | {res['model']}")

    # Summary
    responded = [r for r in results if r["status"] == "RESPONDED"]
    failed = [r for r in results if r["status"] != "RESPONDED"]

    print("\n" + "=" * 80)
    print(" SUMMARY")
    print("=" * 80)
    print(f"Total    : {len(results)}")
    print(f"Responded: {len(responded)}")
    print(f"Failed   : {len(failed)}")
    print("=" * 80)

    if responded:
        print("\n✅ Working Models:")
        for r in sorted(responded, key=lambda x: x["latency"]):
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
    if not OPENROUTER_API_KEY:
        print("[ERROR] OPENROUTER_API_KEY is missing.")
        sys.exit(1)
    model_list = get_openrouter_models(free_only=FREE_ONLY)
    if model_list:
        run_tests(model_list)