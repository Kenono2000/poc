Here is a comprehensive `README.md` summarizing the troubleshooting, environment setup, and LangChain v1.x migration knowledge from our session. 

```markdown
# LangChain Safe Calculator Agent

## Overview
This repository contains notes, troubleshooting guides, and production-ready code for building a LangChain-based AI agent. The primary example (`agent-06.py`) demonstrates a ReAct agent equipped with a **Safe Calculator Tool** that uses Abstract Syntax Tree (AST) parsing to evaluate mathematical expressions securely, preventing arbitrary code execution.

---

## 🛠️ Environment Setup & Best Practices

### 1. Python Version
- **Recommended:** Python 3.11 or 3.12.
- **Avoid:** Preview/Beta versions (e.g., Python 3.14) as they often cause pathing issues in virtual environments and lack full library support.

### 2. Virtual Environments (Crucial)
Always use virtual environments to prevent global package conflicts (e.g., `packaging` version mismatches between `langchainhub` and other tools).

**Create and activate a venv (Windows PowerShell):**
```powershell
# 1. Create using a specific, stable Python executable (Avoid generic 'python' if broken)
& "C:\Users\Ken Wong\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv

# 2. Activate
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install langchain langchain-core langchain-ollama langchainhub
```

---

## 🔍 Checking LangChain Versions

Because the LangChain ecosystem is split into multiple packages, it's important to check versions correctly.

**Inside Python:**
```python
import langchain
import langchain_core
print(f"langchain: {langchain.__version__}")
print(f"langchain-core: {langchain_core.__version__}")
```

**In Terminal:**
```bash
pip show langchain
# or to see all ecosystem packages:
pip list | Select-String langchain
```

---

## 🚀 LangChain Version Migration: 0.x vs 1.x

LangChain underwent a massive architectural overhaul in version 1.0. If you are upgrading or starting fresh, be aware of these critical changes:

| Feature | LangChain 0.x (Legacy) | LangChain 1.x (Current) |
| :--- | :--- | :--- |
| **Agent Factory** | `create_react_agent` | `create_agent` |
| **Execution Loop** | `AgentExecutor` (Explicit wrapper) | Built directly into `create_agent` |
| **Prompting** | `hub.pull("hwchase17/react")` | Pass `system_prompt="..."` directly |
| **Input Format** | `{"input": "query"}` | `{"messages": [("user", "query")]}` |
| **Output Format** | `result["output"]` | `result["messages"][-1].content` |

### The Modern `create_agent` Syntax (v1.x)
```python
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

@tool
def my_tool(query: str) -> str:
    """Tool description."""
    return "result"

llm = ChatOllama(model="gemma4:e2b")

# Note: The parameter is 'system_prompt', not 'prompt'
agent = create_agent(
    model=llm,
    tools=[my_tool],
    system_prompt="You are a helpful assistant." 
)

# Invocation uses the 'messages' key
result = agent.invoke({"messages": [("user", "Hello")]})
print(result["messages"][-1].content)
```

---

## 🛡️ The Safe Calculator Tool (AST Parsing)
Standard Python `eval()` is highly dangerous for AI agents because an LLM can be tricked into executing malicious system commands. This project uses an AST-based evaluator that:
1. Parses the math expression into an Abstract Syntax Tree.
2. Recursively evaluates only whitelisted nodes (`ast.Add`, `ast.Mult`, `ast.Constant`, etc.).
3. Rejects any unsupported operations (like function calls or variable lookups) with a `ValueError`.

---

## 🐛 Troubleshooting Guide

### 1. `ImportError: cannot import name 'AgentExecutor'`
**Cause:** You are running LangChain v1.x, where `AgentExecutor` has been completely removed.
**Fix:** Refactor your code to use `create_agent` from `langchain.agents` and remove the `AgentExecutor` wrapper.

### 2. `TypeError: create_agent() got an unexpected keyword argument 'prompt'`
**Cause:** The `create_agent` function in v1.x does not use `prompt` or `SystemMessage` for the persona.
**Fix:** Use the `system_prompt` parameter and pass a plain string.
```python
agent = create_agent(model=llm, tools=tools, system_prompt="Your instructions here")
```

### 3. `did not find executable at ... pythoncore-3.14-64`
**Cause:** Your virtual environment was created with a preview Python version that was later uninstalled or moved.
**Fix:** Delete the broken `.venv` folder and recreate it using the explicit path to your stable Python 3.11 executable (see Environment Setup).

### 4. `pip dependency resolver` warnings (e.g., `packaging` conflicts)
**Cause:** Two packages require different versions of a shared dependency (e.g., `langchainhub` downgrading `packaging` which another tool like `hermes-agent` strictly requires).
**Fix:** Isolate your LangChain projects in their own virtual environments so their dependencies don't clash with your global system packages.
```

### How to use this:
1. Create a new file named `README.md` in your project directory.
2. Paste the contents above into the file.
3. Save it! This will serve as a perfect reference guide for your future LangChain projects.