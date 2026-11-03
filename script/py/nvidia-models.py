"""
NVIDIA API Catalog model availability probe.

Fetches the model catalog exposed by NVIDIA's OpenAI-compatible endpoint
(``https://integrate.api.nvidia.com/v1``) and sends a tiny chat completion to
each model to find out which ones actually respond.

Why the OpenAI SDK
------------------
NVIDIA's endpoint speaks the OpenAI wire format, so the official ``openai``
client handles authentication, timeouts, and typed errors for us instead of
hand-rolled ``requests`` calls.  The SDK is pointed at NVIDIA's ``base_url``
and uses ``NVIDIA_API_KEY`` from the environment (a local ``.env`` file is
loaded automatically when present).

Configuration
-------------
    NVIDIA_API_KEY  required; API key for integrate.api.nvidia.com
    TEST_LIMIT      optional cap on how many models are probed (default 50)

Output
------
* Real-time lines for models that responded.
* A summary with totals, working models sorted by latency, and failures
  grouped by error message.

Exit codes
----------
    0  the catalog was listed and the probe finished (working or not);
       some models failing is normal for an aggregator catalog
    1  missing API key, or the catalog could not be listed
"""

from __future__ import annotations

import os
import random
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    OpenAIError,
)

# Load environment variables from .env file (no-op when absent).
load_dotenv()

# --- Configuration ---------------------------------------------------------
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").strip()
BASE_URL = "https://integrate.api.nvidia.com/v1"

# Test configuration
TEST_PROMPT = "Reply with 'OK'."
MAX_TOKENS = 10
TIMEOUT_SECONDS = 15.0
MAX_CONCURRENT_TESTS = 5
TEST_LIMIT = 50

#: HTTP statuses worth retrying; provider catalogs frequently rate-limit.
TRANSIENT_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
#: Extra attempts after the initial one, per model.
MAX_RETRIES = 2
#: Base backoff in seconds (jitter is added on top).
RETRY_BACKOFF_SECONDS = 1.0


def build_client(api_key: str = NVIDIA_API_KEY) -> OpenAI:
    """Create the OpenAI-compatible client for NVIDIA's endpoint.

    ``max_retries=0`` because this script implements its own retry policy so
    that retries stay visible per model and transient failures are grouped in
    the summary.
    """
    return OpenAI(
        base_url=BASE_URL,
        api_key=api_key,
        timeout=TIMEOUT_SECONDS,
        max_retries=0,
    )


def get_nvidia_models(client: OpenAI) -> list[str]:
    """Fetch the sorted, de-duplicated list of model ids from the catalog."""
    print("[1/2] Fetching model catalog from NVIDIA API...")
    try:
        model_ids = sorted(
            {
                model_id
                for model in client.models.list()
                if (model_id := getattr(model, "id", None))
            }
        )
    except APITimeoutError as exc:
        print(f"[ERROR] Model catalog request timed out: {exc}")
        return []
    except APIStatusError as exc:
        print(f"[ERROR] API returned status {exc.status_code}: {exc.message}")
        return []
    except APIConnectionError as exc:
        print(f"[ERROR] Could not reach the NVIDIA API: {exc}")
        return []
    except OpenAIError as exc:
        print(f"[ERROR] Failed to fetch model list: {exc}")
        return []

    if not model_ids:
        print("[WARNING] No models found in the API response.")
        return []

    print(f"      Successfully retrieved {len(model_ids)} models.\n")
    return model_ids


def _result(
    model_id: str,
    status: str,
    latency: float | None,
    code: int | str | None,
    output: str,
) -> dict[str, object]:
    """Build one uniform result record."""
    return {
        "model": model_id,
        "status": status,
        "latency": latency,
        "code": code,
        "output": output,
    }


def test_single_model(
    model_id: str,
    client: OpenAI,
    retries: int = MAX_RETRIES,
) -> dict[str, object]:
    """Send a minimal chat completion to ``model_id`` to test availability.

    Transient failures (timeouts, connection errors, 429/5xx) are retried with
    jittered backoff; the returned record always has the same shape so the
    summary can group failures uniformly.
    """
    last_error: dict[str, object] = _result(
        model_id, "ERROR", None, "N/A", "No attempt was made"
    )

    for attempt in range(retries + 1):
        start_time = time.time()
        try:
            completion = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": TEST_PROMPT}],
                max_tokens=MAX_TOKENS,
                temperature=0.1,
            )
            latency = round(time.time() - start_time, 2)

            try:
                content = completion.choices[0].message.content or ""
            except (IndexError, AttributeError, TypeError):
                return _result(
                    model_id,
                    "UNEXPECTED_FORMAT",
                    latency,
                    200,
                    repr(completion)[:100],
                )

            clean_content = str(content).strip().replace("\n", " ")[:50]
            return _result(model_id, "RESPONDED", latency, 200, clean_content)

        except APITimeoutError:
            latency = round(time.time() - start_time, 2)
            last_error = _result(
                model_id, "TIMEOUT", latency, 408, f"Request timed out after {TIMEOUT_SECONDS:.0f}s"
            )
        except APIStatusError as exc:
            latency = round(time.time() - start_time, 2)
            status_code = exc.status_code
            message = str(getattr(exc, "message", None) or exc).replace("\n", " ")[:100]
            last_error = _result(model_id, "FAILED", latency, status_code, message)
            if status_code not in TRANSIENT_STATUS_CODES:
                return last_error
        except APIConnectionError as exc:
            latency = round(time.time() - start_time, 2)
            last_error = _result(model_id, "ERROR", latency, "N/A", str(exc)[:80])
        except OpenAIError as exc:
            latency = round(time.time() - start_time, 2)
            return _result(model_id, "ERROR", latency, "N/A", str(exc)[:80])

        # Retry only when attempts remain and the failure was transient.
        if attempt < retries:
            time.sleep(RETRY_BACKOFF_SECONDS + random.random())

    return last_error


def run_tests(models: list[str], client: OpenAI, limit: int = TEST_LIMIT) -> None:
    """Probe all models concurrently and print the summary report."""
    if len(models) > limit:
        print(f"[INFO] Limiting test to {limit} of {len(models)} models.\n")
        models_to_test = models[:limit]
    else:
        models_to_test = models

    print(
        f"[2/2] Testing {len(models_to_test)} models "
        f"(threads: {MAX_CONCURRENT_TESTS})...\n"
    )

    results: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TESTS) as executor:
        future_to_model = {
            executor.submit(test_single_model, model_id, client): model_id
            for model_id in models_to_test
        }
        for future in as_completed(future_to_model):
            result = future.result()
            results.append(result)
            # Real-time console output - only for models that worked.
            if result["status"] == "RESPONDED":
                print(f"[RESPONDED]  | {float(result['latency']):>5.2f}s | {result['model']}")

    # --- Print Summary Report ---
    print("\n" + "=" * 80)
    print(" SUMMARY")
    print("=" * 80)

    responded = [r for r in results if r["status"] == "RESPONDED"]
    failed = [r for r in results if r["status"] != "RESPONDED"]

    print(f"Total    : {len(results)}")
    print(f"Responded: {len(responded)}")
    print(f"Failed   : {len(failed)}")
    print("=" * 80)

    if responded:
        print("\n[OK] Working Models:")
        for result in sorted(responded, key=lambda item: float(item["latency"])):
            print(
                f"  - {result['model']:<55} {float(result['latency']):>5.2f}s"
                f"  -> {result['output']}"
            )

    if failed:
        print("\n[FAIL] Failure Summary (grouped by error):")
        grouped: dict[str, list[str]] = defaultdict(list)
        for result in failed:
            key = f"{result['code']}: {str(result['output'])[:60]}"
            grouped[key].append(str(result["model"]))

        for error, model_list in list(grouped.items())[:10]:
            sample = ", ".join(model_list[:3])
            more = f" (+{len(model_list) - 3} more)" if len(model_list) > 3 else ""
            print(f"  - [{len(model_list)}] {error}")
            print(f"      e.g. {sample}{more}")


def main() -> int:
    """Entry point; validates configuration and runs the probe."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

    if not NVIDIA_API_KEY:
        print("[ERROR] NVIDIA_API_KEY is missing. Set it or add it to a .env file.")
        return 1

    try:
        client = build_client()
        model_list = get_nvidia_models(client)
        if not model_list:
            print("[ERROR] Could not retrieve any models; aborting.")
            return 1
        run_tests(model_list, client)
    except OpenAIError as exc:
        print(f"[ERROR] NVIDIA client setup failed: {exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
