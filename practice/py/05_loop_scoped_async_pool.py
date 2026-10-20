"""
Pattern 5: Event-Loop-Scoped Async Client & Pool Manager
========================================================
Core Interview Point:
- Multi-threaded frameworks (like Streamlit or worker pools) create and tear down
  asyncio event loops across turns.
- Global singletons (`AsyncOpenAI`, `asyncpg.Pool`) bind to the first loop and crash
  with `RuntimeError: Event loop is closed` on subsequent turns.
- Keying clients by `asyncio.get_running_loop()` and pruning closed loops solves this permanently.
"""

import asyncio
from dataclasses import dataclass


@dataclass
class MockAsyncClient:
    loop_id: int
    closed: bool = False


class LoopScopedManager:
    """Binds async clients/pools to the active event loop and evicts closed loops."""

    def __init__(self) -> None:
        self._clients: dict[asyncio.AbstractEventLoop, MockAsyncClient] = {}

    def get_client(self) -> MockAsyncClient:
        current_loop = asyncio.get_running_loop()

        # Prune stale/closed event loops to prevent memory leaks
        stale_loops = [lp for lp in self._clients if lp.is_closed()]
        for lp in stale_loops:
            del self._clients[lp]

        if current_loop not in self._clients:
            self._clients[current_loop] = MockAsyncClient(loop_id=id(current_loop))

        return self._clients[current_loop]


async def worker_turn(manager: LoopScopedManager, turn: int) -> int:
    client = manager.get_client()
    await asyncio.sleep(0.01)
    print(f"Turn {turn}: Bound safely to active loop {client.loop_id} (active cached loops={len(manager._clients)})")
    return client.loop_id


if __name__ == "__main__":
    manager = LoopScopedManager()

    # Each asyncio.run() creates a brand-new event loop and closes it on exit
    loop1 = asyncio.run(worker_turn(manager, turn=1))
    loop2 = asyncio.run(worker_turn(manager, turn=2))

    print(f"Loop recycled cleanly across turns: {loop1 != loop2} (Cached loops remaining: {len(manager._clients)})")
