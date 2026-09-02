from fastmcp import FastMCP
import uuid
import sys
import warnings
import importlib.util
from pathlib import Path

# Suppress Pydantic settings warning
warnings.filterwarnings("ignore", message="Field 'lifespan' has an incomplete definition")

# Dynamic import for file starting with number/hyphen
def load_contracts():
    path = Path(__file__).parent / "1-3_contracts.py"
    spec = importlib.util.spec_from_file_location("contracts", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

contracts = load_contracts()
TransactionTransferRequest = contracts.TransactionTransferRequest
TransactionTransferResponse = contracts.TransactionTransferResponse

# Initialize FastMCP Server
mcp = FastMCP("Enterprise-Financial-Agent-Gateway")


mcp = FastMCP("Enterprise-Financial-Agent-Gateway")

@mcp.tool()
async def execute_account_transfer(
    payload: TransactionTransferRequest
) -> TransactionTransferResponse:
    """
    Executes an audited account-to-account transfer within hard transactional boundaries.
    Parameters are deterministically validated before entering this handler.
    """
    # 1. Deterministic Contract Guaranteed
    tx_id = f"tx_{uuid.uuid4().hex[:12]}"
    
    # 2. Simulated Transactional Backend Logic
    # In production: Redis TTL Lock -> PostgreSQL RLS / ACID Mutation
    flat_fee_cents = 25
    
    return TransactionTransferResponse(
        transaction_id=tx_id,
        status="COMMITTED",
        debited_cents=payload.amount_cents + flat_fee_cents,
        fee_cents=flat_fee_cents,
        authorized=True
    )

if __name__ == "__main__":
    # Check if we want to run in dev mode or SSE
    if "--sse" in sys.argv:
        print("Starting SSE Server on http://localhost:8000/sse")
        mcp.run(transport="sse")
    else:
        # Standard MCP run (Stdio)
        # Note: Do not run this manually in a terminal and hit 'Enter'
        mcp.run()