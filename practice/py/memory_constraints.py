"""
Memory Constraints:
Processing multi-gigabyte directory dumps using generators and streaming parsers
without loading the entire dataset into memory.

Demonstrates:
1. Streaming JSON array parsing / chunked generator pipeline (pure standard library generator fallback + optional ijson support).
2. Streaming JSONL / Line-delimited JSON with lazy generators.
3. Constant O(1) memory batching / windowing over high-volume identity records.
4. Memory usage profiling via tracemalloc.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import tracemalloc
from dataclasses import dataclass
from typing import Any, Dict, Generator, Iterable, Iterator, List, Optional

# Attempt to import ijson if available in the environment; fallback gracefully
try:
    import ijson  # type: ignore
    HAS_IJSON = True
except ImportError:
    HAS_IJSON = False


@dataclass(frozen=True)
class StreamedDirectoryRecord:
    account_id: str
    upn: str
    department: str
    roles: List[str]
    is_active: bool


def stream_json_array_records(file_obj: io.TextIOBase) -> Generator[Dict[str, Any], None, None]:
    """
    Memory-efficient stream parser for a large top-level JSON array of objects `[ {...}, {...} ]`
    without loading the multi-gigabyte file into memory.

    If `ijson` is installed, uses `ijson.items(file_obj, 'item')`.
    Otherwise, uses an incremental buffer tokenizer reading chunks of text.
    """
    if HAS_IJSON:
        # ijson provides C-backend or Python-backend incremental JSON event parsing
        for record in ijson.items(file_obj, "item"):
            yield record
        return

    # Fallback incremental chunked JSON parser for large arrays
    decoder = json.JSONDecoder()
    buffer = ""
    chunk_size = 64 * 1024  # 64 KB chunk size

    # Find the opening '[' bracket
    while True:
        chunk = file_obj.read(chunk_size)
        if not chunk:
            return
        buffer += chunk
        start_idx = buffer.find("[")
        if start_idx != -1:
            buffer = buffer[start_idx + 1 :]
            break

    while True:
        buffer = buffer.lstrip(" \r\n\t,")
        if not buffer:
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            buffer = buffer.lstrip(" \r\n\t,")

        if buffer.startswith("]"):
            break

        try:
            record, end_idx = decoder.raw_decode(buffer)
            yield record
            buffer = buffer[end_idx:]
        except json.JSONDecodeError:
            # Need more bytes into buffer to complete next JSON object
            chunk = file_obj.read(chunk_size)
            if not chunk:
                break
            buffer += chunk


def stream_jsonl_records(file_obj: io.TextIOBase) -> Generator[Dict[str, Any], None, None]:
    """
    Streams a multi-gigabyte line-delimited JSON (JSONL) directory dump line-by-line.
    Memory complexity: O(size_of_single_line), not O(file_size).
    """
    for line in file_obj:
        line_clean = line.strip()
        if line_clean:
            yield json.loads(line_clean)


def chunked_pipeline(
    records: Iterator[Dict[str, Any]],
    batch_size: int = 1000,
) -> Generator[List[StreamedDirectoryRecord], None, None]:
    """
    Lazy batching generator: takes an iterator/generator of raw dicts and yields
    fixed-size typed batches to downstream sinks (e.g. bulk DB insert or worker queues).
    """
    batch: List[StreamedDirectoryRecord] = []
    for raw in records:
        record = StreamedDirectoryRecord(
            account_id=raw["id"],
            upn=raw["upn"],
            department=raw.get("department", "unknown"),
            roles=raw.get("roles", []),
            is_active=raw.get("active", True),
        )
        batch.append(record)

        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


def generate_mock_large_dump(file_path: str, count: int = 25000) -> None:
    """Helper to generate a mock directory dump file formatted as a large JSON array."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i in range(count):
            record = {
                "id": f"acc-{i:07d}",
                "upn": f"user_{i:07d}@corp.internal",
                "department": "Engineering" if i % 2 == 0 else "SecOps",
                "roles": ["member", "cloud-operator"] if i % 5 == 0 else ["member"],
                "active": i % 100 != 0,
            }
            line = json.dumps(record)
            if i < count - 1:
                line += ","
            f.write(f"  {line}\n")
        f.write("]\n")


def run_benchmark():
    print(f"Streaming Engine Status: {'ijson (installed)' if HAS_IJSON else 'standard library chunked parser'}")

    with tempfile.TemporaryDirectory() as tmpdir:
        sample_path = os.path.join(tmpdir, "large_directory_dump.json")
        total_records = 30000
        batch_size = 5000

        print(f"Generating synthetic directory dump with {total_records:,} records...")
        generate_mock_large_dump(sample_path, count=total_records)
        file_size_mb = os.path.getsize(sample_path) / (1024 * 1024)
        print(f"Dataset generated: {file_size_mb:.2f} MB on disk.")

        print("\nStarting memory-constrained streaming pipeline...")
        tracemalloc.start()

        total_batches = 0
        total_streamed = 0
        active_users_count = 0

        with open(sample_path, "r", encoding="utf-8") as f:
            raw_stream = stream_json_array_records(f)
            batched_stream = chunked_pipeline(raw_stream, batch_size=batch_size)

            for batch in batched_stream:
                total_batches += 1
                total_streamed += len(batch)
                active_users_count += sum(1 for u in batch if u.is_active)

                # Process batch in bounded memory, then allow batch to be garbage collected
                del batch

        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        print("\n--- Pipeline Execution Metrics ---")
        print(f"Total records streamed : {total_streamed:,}")
        print(f"Total batches processed: {total_batches}")
        print(f"Active users counted   : {active_users_count:,}")
        print(f"Peak RAM allocated     : {peak_mem / (1024 * 1024):.2f} MB")
        print(f"Current RAM remaining  : {current_mem / (1024 * 1024):.2f} MB")
        print(f"Dataset-to-RAM Ratio   : {file_size_mb / (peak_mem / (1024 * 1024)):.1f}x compression over in-memory loading")


if __name__ == "__main__":
    run_benchmark()