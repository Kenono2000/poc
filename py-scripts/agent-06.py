"""
LangChain Agent with Safe Calculator Tool (LangChain 1.x Edition)

Purpose: Demonstrates a production-grade agent that safely evaluates mathematical 
expressions using AST (Abstract Syntax Tree) parsing to prevent code injection.

Features:
- ChatOllama model (gemma4:e2b)
- Safe calculator using AST parsing (not eval())
- Support for: +, -, *, /, **, and parentheses
- LangChain 1.x create_agent framework (replaces legacy AgentExecutor)
- Tool definition using @tool decorator
- Protection against arbitrary code execution

Required: Ollama running with gemma4:e2b model
"""

# --- Imports (Updated for LangChain 1.x) -----------------------------------
import ast
import operator

import langchain
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain.agents import create_agent  # The v1.x standard

# Top-level model name used by this script
MODEL_NAME = "gemma4:e2b"

# --- Safe AST evaluator ----------------------------------------------------
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.expr) -> float:
    """Recursively evaluate an AST node using only allowed operators."""
    match node:
        case ast.Constant(value=v) if isinstance(v, int | float):
            return v
        case ast.BinOp(left=left, op=op, right=right) if type(op) in SAFE_OPERATORS:
            return SAFE_OPERATORS[type(op)](_safe_eval(left), _safe_eval(right))
        case ast.UnaryOp(op=op, operand=operand) if type(op) in SAFE_OPERATORS:
            return SAFE_OPERATORS[type(op)](_safe_eval(operand))
        case _:
            raise ValueError(f"Unsupported expression: {ast.dump(node)}")


# --- Tool definition -------------------------------------------------------
@tool
def calculator_tool(expression: str) -> str:
    """Evaluate a mathematical expression safely.
    Supports: +, -, *, /, ** and parentheses.
    Example input: '0.15 * 450'
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _safe_eval(tree.body)
        return str(result)
    except (ValueError, ZeroDivisionError, SyntaxError) as e:
        return f"Error evaluating expression: {e}"


# --- Agent construction (LangChain 1.x) ------------------------------------
def build_agent(model_name: str = MODEL_NAME):
    """Construct and return a LangChain 1.x agent with the calculator tool."""
    llm = ChatOllama(model=model_name)
    tools = [calculator_tool]

    # Define the system prompt for the agent
    system_prompt = (
        "You are a helpful assistant that can evaluate mathematical expressions "
        "safely using the provided calculator tool. Always use the calculator tool "
        "for any math calculations."
    )

    # Create the agent using the new LangChain 1.x create_agent function
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt  # <-- FIXED: Correct parameter name
    )

    return agent


# --- Entry point -----------------------------------------------------------
def main():
    print(f"Using LangChain version: {langchain.__version__}")
    agent = build_agent()
    
    # In LangChain 1.x, agents are invoked with a "messages" key
    result = agent.invoke({"messages": [("user", "What is 15% of 450?")]})
    
    # The final answer is the content of the last message in the response
    final_answer = result["messages"][-1].content
    print(f"\nFinal Answer: {final_answer}")


if __name__ == "__main__":
    main()