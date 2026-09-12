import asyncio
import random
import logging
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import asyncpg

load_dotenv()


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class BoundedAgentRuntime:
    def __init__(
        self,
        db_dsn: str,
        max_concurrent_agents: int = 10,
        pool_min: int = 5,
        pool_max: int = 20
    ):
        self.db_dsn = db_dsn
        self.pool_min = pool_min
        self.pool_max = pool_max
        # 1. Bounded Concurrency: Gate the event loop executions
        self.semaphore = asyncio.Semaphore(max_concurrent_agents)
        self.db_pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initializes stateful, bounded connection pool."""
        self.db_pool = await asyncpg.create_pool(
            dsn=self.db_dsn,
            min_size=self.pool_min,
            max_size=self.pool_max,
            command_timeout=10.0,
            max_inactive_connection_lifetime=300.0
        )
        logging.info(f"Initialized asyncpg pool: min={self.pool_min}, max={self.pool_max}")

    async def close(self):
        if self.db_pool:
            await self.db_pool.close()
            logging.info("Connection pool closed cleanly.")

    async def call_llm_with_jittered_backoff(
        self, 
        prompt: str, 
        max_retries: int = 4, 
        base_delay: float = 0.5, 
        max_delay: float = 8.0
    ) -> str:
        """Simulates an LLM API call with Decorrelated Jitter Exponential Backoff."""
        for attempt in range(max_retries):
            try:
                # Simulate potential HTTP 429 under load
                if random.random() < 0.25:
                    raise ConnectionResetError("HTTP 429: Rate limit reached (TPM/RPM exceeded)")
                
                # Successful response simulation
                return f"Grounded response for prompt hash: {hash(prompt)}"
            
            except ConnectionResetError as err:
                if attempt == max_retries - 1:
                    logging.error(f"Exhausted retries on LLM Gateway: {err}")
                    raise err
                
                # Full Jitter: Sleep = uniform(0, min(max_delay, base_delay * 2^attempt))
                backoff_limit = min(max_delay, base_delay * (2 ** attempt))
                sleep_time = random.uniform(0.1, backoff_limit)
                
                logging.warning(
                    f"LLM Rate Limited (429). Attempt {attempt + 1}/{max_retries}. "
                    f"Applying jittered backoff: sleeping {sleep_time:.2f}s"
                )
                await asyncio.sleep(sleep_time)

        raise RuntimeError("LLM retry loop completed without a response")

    async def execute_agent_job(self, agent_id: str, prompt: str) -> Dict[str, Any]:
        """Runs an individual agent job bounded by concurrency gates and connection pools."""
        # Gate 1: Bounded Concurrency Execution (prevents worker starvation)
        async with self.semaphore:
            # Step 1: Upstream Model Call with Jittered Exponential Backoff
            llm_result = await self.call_llm_with_jittered_backoff(prompt)

            # Gate 2: Bounded Database Connection Acquisition
            async with self.db_pool.acquire() as conn:
                # Execute transactional query within connection scope
                row = await conn.fetchrow(
                    """
                    SELECT id, content 
                    FROM document_embeddings 
                    WHERE allowed_roles ?| $1::text[] 
                    LIMIT 1;
                    """,
                    ["engineering", "admin"]
                )
                
                return {
                    "agent_id": agent_id,
                    "status": "COMPLETED",
                    "result": llm_result,
                    "matched_doc": row["id"] if row else None
                }

async def main():
    # Configuration from environment or defaults
    DB_DSN = os.getenv("DATABASE_URL")

    
    # Initialize runtime with bounded concurrency
    runtime = BoundedAgentRuntime(
        db_dsn=DB_DSN,
        max_concurrent_agents=5,
        pool_min=2,
        pool_max=10
    )

    try:
        logging.info("Starting Bounded Agent Runtime demo...")
        await runtime.initialize()

        # Simulate a burst of 15 concurrent agent jobs
        prompts = [f"Analyze security report {i}" for i in range(1, 16)]
        tasks = [runtime.execute_agent_job(f"agent-{i:03}", p) for i, p in enumerate(prompts)]

        logging.info(f"Scheduling {len(tasks)} concurrent agent jobs (throttled by semaphore)...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                logging.error(f"Job failed: {res}")
            else:
                logging.info(f"Job {res['agent_id']} finished. Result hash: {hash(res['result'])}")
        
    except Exception as e:
        logging.critical(f"Failed to run demo: {e}")
    finally:
        await runtime.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass