"""Shared utilities for testing OpenAI-compatible chat completion endpoints."""

from __future__ import annotations

import random
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

import requests

TRANSIENT_STATUS_CODES = (429, 500, 502, 503, 504)


def test_chat_model(
    chat_endpoint: str,
    api_key: str,
    model_id: str,
    prompt: str = "Reply with 'OK'.",
    max_tokens: int = 10,
    timeout_seconds: int = 15,
    retries: int = 1,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Send a minimal chat completion request to test model availability."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }

    last_error = "Unknown error"
    for attempt in range(retries + 1):
        start_time = time.time()
        try:
            response = requests.post(
                chat_endpoint,
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
            )
            latency = round(time.time() - start_time, 2)

            if response.status_code in TRANSIENT_STATUS_CODES and attempt < retries:
                time.sleep(1 + random.random())  # noqa: S311
                continue

            if response.status_code == 200:
                res_json = response.json()
                content = (
                    res_json.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                return {
                    "model": model_id,
                    "status": "SUCCESS",
                    "latency": latency,
                    "response": content,
                }

            return {
                "model": model_id,
                "status": f"HTTP {response.status_code}",
                "latency": latency,
                "error": response.text[:200],
            }
        except requests.exceptions.Timeout:
            last_error = "Request timed out"
        except requests.exceptions.RequestException as exc:
            last_error = str(exc)
        except (KeyError, ValueError, TypeError) as exc:
            last_error = f"Invalid response format: {exc}"

        if attempt < retries:
            time.sleep(1)

    return {
        "model": model_id,
        "status": "ERROR",
        "latency": 0.0,
        "error": last_error,
    }


def run_concurrent_model_tests(
    models: list[str],
    test_fn: Callable[[str], dict[str, Any]],
    max_workers: int = 5,
    test_limit: int | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Run model tests concurrently and group results by status."""
    targets = models[:test_limit] if test_limit else models
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    print(f"[2/2] Testing {len(targets)} model(s) with {max_workers} worker(s)...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(test_fn, m): m for m in targets}
        for future in as_completed(futures):
            result = future.result()
            status = result.get("status", "ERROR")
            grouped[status].append(result)
            if status == "SUCCESS":
                print(f"  [OK] {result['model']} ({result['latency']}s)")
            else:
                print(
                    f"  [FAIL] {result['model']} -> {status}: "
                    f"{result.get('error', '')}"
                )

    print(
        f"\nSummary: {len(grouped.get('SUCCESS', []))} succeeded, "
        f"{len(targets) - len(grouped.get('SUCCESS', []))} failed."
    )
    return dict(grouped)
