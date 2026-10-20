"""
Pattern 4: Idempotent SHA-256 Ingestion & Resilient Batching
============================================================
Core Interview Point:
- 64KB streaming SHA-256 hashing avoids loading large PDFs into RAM and enables O(1)
  change detection (skip unchanged files, purge & re-index modified files).
- Batch slicing + exponential backoff protects embedding APIs from 429 rate limits.
"""

import hashlib
import io
import time
from typing import Iterator, TypeVar

T = TypeVar("T")


def compute_stream_sha256(stream: io.BufferedReader | io.BytesIO, block_size: int = 65536) -> str:
    """Compute SHA-256 in 64KB blocks with O(1) memory footprint."""
    hasher = hashlib.sha256()
    while chunk := stream.read(block_size):
        hasher.update(chunk)
    return hasher.hexdigest()


def batch_slice(items: list[T], batch_size: int = 64) -> Iterator[list[T]]:
    """Yield fixed-size batches to prevent token/payload limit spikes."""
    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]


class IdempotentIngestor:
    def __init__(self) -> None:
        self.db_hashes: dict[str, str] = {}  # filename -> sha256

    def ingest(self, filename: str, content: bytes, force: bool = False) -> str:
        file_hash = compute_stream_sha256(io.BytesIO(content))
        existing_hash = self.db_hashes.get(filename)

        if not force and existing_hash == file_hash:
            return "SKIPPED (Unchanged SHA-256)"

        action = "RE-INDEXED (Purged stale chunks)" if existing_hash else "INDEXED (New document)"
        self.db_hashes[filename] = file_hash
        return f"{action} [hash={file_hash[:10]}...]"


def call_with_backoff(fn, max_attempts: int = 3, base_delay: float = 0.05):
    """Minimal exponential backoff retry wrapper for transient 429/503 API errors."""
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except RuntimeError as exc:
            if attempt == max_attempts:
                raise
            time.sleep(base_delay * (2 ** (attempt - 1)))
            print(f"  [Retry {attempt}/{max_attempts}] Recovered from transient error: {exc}")


if __name__ == "__main__":
    ingestor = IdempotentIngestor()
    print("1st Run :", ingestor.ingest("policy.md", b"v1 content"))
    print("2nd Run :", ingestor.ingest("policy.md", b"v1 content"))
    print("3rd Run :", ingestor.ingest("policy.md", b"v2 updated content"))

    attempts = 0
    def flaky_embed_api():
        global attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("HTTP 429 Too Many Requests")
        return [[0.1, 0.2]]

    print("Backoff :", call_with_backoff(flaky_embed_api))
