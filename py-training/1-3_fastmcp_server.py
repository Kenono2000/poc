from fastmcp import FastMCP
import uuid
import sys
import warnings
import importlib.util
from pathlib import Path
import asyncio
import json


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

async def inspect_mcp_tool_schema():
    # Retrieve all registered tools from the FastMCP server instance
    tools = await mcp.list_tools()
    for tool in tools:
        if tool.name == "execute_account_transfer":
            print("--- FastMCP Tool Export ---")
            print(f"Tool Name: {tool.name}")
            print(f"Tool Description: {tool.description}")
            print("Tool InputSchema (JSON-RPC Protocol):")
            print(json.dumps(tool.inputSchema, indent=2))

if __name__ == "__main__":
    # 1. First, inspect the schema (Optional Debug)
    try:
        asyncio.run(inspect_mcp_tool_schema())
    except Exception as e:
        print(f"Could not inspect schema: {e}")

    # 2. Then run the server
    if "--sse" in sys.argv:
        print("Starting SSE Server on http://localhost:8000/sse")
        mcp.run(transport="sse")
    else:
        # Standard MCP run (Stdio)
        # Note: Do not run this manually in a terminal and hit 'Enter'
        mcp.run()


# fastmcp run .\1-3_fastmcp_server.py --no-banner --reload
# npx @modelcontextprotocol/inspector python 1-3_fastmcp_server.py --tool execute_account_transfer --json-schema