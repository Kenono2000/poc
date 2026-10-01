# Async I/O & Concurrency: Expect to design or code thread-safe or asyncio-based worker pools querying mock LDAP/IAM endpoints.

import asyncio
import random
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass(frozen=True)
class UserIdentity:
    username: str
    dn: str
    groups: List[str]
    roles: List[str]

class MockIamLdapClient:
    """Simulates an asynchronous LDAP/IAM directory service client."""

    _MOCK_DIRECTORY: Dict[str, Dict[str, List[str]]] = {
        "alice": {
            "groups": ["engineering", "secops"],
            "roles": ["admin", "viewer"],
        },
        "bob": {
            "groups": ["product", "analytics"],
            "roles": ["editor"],
        },
        "charlie": {
            "groups": ["engineering"],
            "roles": ["viewer"],
        },
        "david": {
            "groups": ["it-support"],
            "roles": ["operator"],
        },
    }

    async def query_user(self, username: str) -> Optional[UserIdentity]:
        # Simulate network latency to LDAP/IAM endpoint (50ms - 150ms)
        await asyncio.sleep(random.uniform(0.05, 0.15))

        data = self._MOCK_DIRECTORY.get(username)
        if not data:
            return None

        return UserIdentity(
            username=username,
            dn=f"uid={username},ou=users,dc=corp,dc=internal",
            groups=data["groups"],
            roles=data["roles"],
        )

class DirectoryLookupWorkerPool:
    """
    Asyncio-based worker pool for querying directory endpoints.

    Uses an asyncio.Queue for work distribution, a fixed number of workers
    to bound concurrency, and an asyncio.Lock for thread/task-safe shared metrics.
    """

    def __init__(self, client: MockIamLdapClient, num_workers: int = 3):
        self.client = client
        self.num_workers = num_workers
        # An asynchronous FIFO (First-In, First-Out) queue for producer-consumer coordination.
        # Type hint `[str]` indicates it holds string usernames (checked by mypy/IDE, not runtime).
        # Unbounded capacity by default (maxsize=0).
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.results: Dict[str, Optional[UserIdentity]] = {}
        self._lock = asyncio.Lock()
        self._processed_count = 0

    async def _worker(self, worker_id: int):
        while True:
            username = await self.queue.get()
            try:
                identity = await self.client.query_user(username)

                # Safe access to shared results / metrics
                async with self._lock:
                    self.results[username] = identity
                    self._processed_count += 1
                    status = f"found {identity.roles}" if identity else "NOT_FOUND"
                    print(f"[Worker {worker_id}] Queried {username:<8} -> {status}")
            except Exception as exc:
                print(f"[Worker {worker_id}] Error querying {username}: {exc}")
            finally:
                self.queue.task_done()

    async def process_users(self, usernames: List[str]) -> Dict[str, Optional[UserIdentity]]:
        # 1. PRODUCER: Enqueue tasks
        # Feeds items into the queue one-by-one so background workers can pick them up.
        # `await put()` non-blockingly enqueues the item (pauses/yields if queue reached maxsize).
        for username in usernames:
            await self.queue.put(username)

        # 2. SPAWN BOUNDED POOL OF WORKERS:
        # Caps concurrency at `self.num_workers` to prevent overwhelming resources / API limits.
        # `asyncio.create_task` schedules `self._worker` on the event loop immediately in the background
        # without blocking execution here. Stored in a list for lifecycle management (cancellation/gather).
        workers = [
            asyncio.create_task(self._worker(worker_id=i))
            for i in range(self.num_workers)
        ]

        # 3. SYNCHRONIZATION:
        # Wait until all queued queries are completed (all put() items have a matching task_done())
        await self.queue.join()

        # 4. GRACEFUL SHUTDOWN & CLEANUP:
        # Workers run infinite `while True:` loops waiting on `queue.get()`. Without cancelling them,
        # `asyncio.gather` would block forever.
        # Calling `worker.cancel()` injects `asyncio.CancelledError` into each worker at its current
        # await point, breaking the loop while allowing finally/cleanup blocks to run.
        for worker in workers:
            worker.cancel()

        # `*workers`: Unpacks the worker list as positional arguments.
        # `return_exceptions=True`: Treats `asyncio.CancelledError` (and other exceptions) as return values
        # rather than raising them, guaranteeing all workers cleanly exit before proceeding.
        await asyncio.gather(*workers, return_exceptions=True)

        return self.results

async def main():
    client = MockIamLdapClient()
    pool = DirectoryLookupWorkerPool(client=client, num_workers=3)

    users_to_query = [
        "alice",
        "bob",
        "unknown_user",
        "charlie",
        "david",
        "eve_nonexistent",
    ]

    print(f"Submitting {len(users_to_query)} lookup requests across {pool.num_workers} workers...")
    results = await pool.process_users(users_to_query)

    print("\nSummary of results:")
    for username, identity in results.items():
        if identity:
            print(f"  {username}: DN={identity.dn} | Roles={identity.roles}")
        else:
            print(f"  {username}: Directory record not found")

if __name__ == "__main__":
    asyncio.run(main())
