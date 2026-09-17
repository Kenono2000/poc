import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
import redis.asyncio as aioredis

sys.path.insert(0, str(Path(__file__).parent.parent / "py-libraries"))
from utilities import load_config

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ResiliencePipeline")

# Configuration

_, DB_DSN = load_config(str(Path(__file__).parent / ".env"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# 1. Bounded Concurrency: Maximum 10 concurrent downstream operations
MAX_CONCURRENT_TASKS = 10
task_semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

MAX_LOCK_RETRIES = 10
LOCK_RETRY_BASE_DELAY = 0.1

@asynccontextmanager
async def distributed_lock(
    redis_client: aioredis.Redis,
    lock_key: str,
    ttl_seconds: int = 5,
    max_retries: int = MAX_LOCK_RETRIES,
    retry_base_delay: float = LOCK_RETRY_BASE_DELAY,
):
    """
    Acquires a named Redis lock with an auto-expiring TTL.
    Uses an atomic NX key set with an ownership token.
    Retries with exponential backoff when the lock is contended.
    """
    token = str(uuid.uuid4())
    acquired = False
    for attempt in range(max_retries):
        try:
            logger.debug(f"Lock attempt {attempt+1}/{max_retries} for {lock_key}")
            acquired = await redis_client.set(lock_key, token, nx=True, ex=ttl_seconds)
        except aioredis.RedisError as e:
            logger.error(f"Redis infrastructure error: {e}")
            raise TimeoutError(f"Redis unavailable while acquiring lock for {lock_key}")
        
        if acquired:
            logger.debug(f"Lock acquired: {lock_key}")
            break
        
        delay = retry_base_delay * (2 ** attempt)
        logger.warning(f"Lock contention for {lock_key}. Retrying in {delay:.2f}s...")
        await asyncio.sleep(delay)

    if not acquired:
        logger.error(f"Lock exhaustion for {lock_key} after {max_retries} attempts.")
        raise TimeoutError(
            f"Could not acquire lock for {lock_key} after {max_retries} retries; resource contended."
        )
    try:
        yield token
    finally:
        # Atomic lock release via Lua script (ensures only the owner deletes the lock)
        logger.debug(f"Releasing lock: {lock_key}")
        release_script = """

            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
        """
        await redis_client.eval(release_script, 1, lock_key, token)

async def mutate_balance_worker(
    worker_id: int,
    db_pool: asyncpg.Pool,
    redis_client: aioredis.Redis,
    account_id: str,
    debit_amount_cents: int
):
    logger.info(f"Worker {worker_id:02d}: Task initiated")
    # Bound concurrent executions across the event loop
    async with task_semaphore:
        logger.debug(f"Worker {worker_id:02d}: Entered semaphore slot")
        lock_name = f"lock:account:{account_id}"
        
        try:
            # Distributed synchronization across horizontal processes
            async with distributed_lock(redis_client, lock_name, ttl_seconds=3):
                logger.info(f"Worker {worker_id:02d}: Lock secured, starting DB transaction")
                # Acquire connection from bounded asyncpg pool
                async with db_pool.acquire() as conn, conn.transaction():
                    # Read current state
                    row = await conn.fetchrow(
                        "SELECT balance_cents, version FROM account_balances WHERE account_id = $1 FOR UPDATE",
                        account_id
                    )
                    
                    if row["balance_cents"] < debit_amount_cents:
                        logger.warning(f"Worker {worker_id:02d}: Insufficient funds ({row['balance_cents']} cents)")
                        raise ValueError("Insufficient funds")
                    
                    # Atomic mutation
                    new_balance = row["balance_cents"] - debit_amount_cents
                    await conn.execute(
                        """
                        UPDATE account_balances 
                        SET balance_cents = $1, version = version + 1, updated_at = NOW()
                        WHERE account_id = $2
                        """,
                        new_balance, account_id
                    )
                    msg = f"Worker {worker_id:02d} SUCCESS: Debited {debit_amount_cents} cents. New balance: {new_balance}"
                    logger.info(msg)
                    return msg
        except (asyncpg.PostgresError, aioredis.RedisError, ValueError) as e:
            logger.error(f"Worker {worker_id:02d} FAILED: {e!s}")
            raise

async def main():
    logger.info("Starting Resilience Pipeline Simulation...")
    # Initialize bounded asyncpg pool (min 5, max 20 connections)
    try:
        db_pool = await asyncpg.create_pool(dsn=DB_DSN, min_size=5, max_size=20)
        logger.info("Connected to PostgreSQL pool.")
    except (asyncpg.PostgresError, OSError) as e:
        logger.critical(f"Failed to connect to DB: {e}")
        return

    redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)
    logger.info("Connected to Redis.")

    # Spawn 50 concurrent mutation attempts
    logger.info("Spawning 50 concurrent workers...")
    tasks = [
        mutate_balance_worker(i, db_pool, redis_client, "acc_prod_001", debit_amount_cents=100)
        for i in range(50)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analyze outcome
    successful = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    print("\n" + "="*50)
    print("FINAL PIPELINE SUMMARY")
    print("="*50)
    print(f"Total Tasks: 50 | Succeeded: {len(successful)} | Rejected/Contended: {len(failures)}")

    if failures:
        from collections import Counter
        error_types = Counter(type(f).__name__ for f in failures)
        print("\nFailure breakdown:")
        for err_type, count in error_types.most_common():
            sample = next(f for f in failures if type(f).__name__ == err_type)
            print(f"  - {err_type:15}: {count} occurrences (Sample: {sample})")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())