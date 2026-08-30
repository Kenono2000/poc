"""
Multi-Turn Conversational Agent with Memory and Multiple Tools

Purpose: Demonstrates a stateful agent that remembers conversation history
and has access to multiple tools (calculator and knowledge base).

Features:
- Local Ollama LLM (llama3.2:3b)
- Conversation memory using manual chat history tracking
- Multiple tools: calculator and knowledge_base lookup
- ReAct-style reasoning with tool selection
- Session-based memory management
- Multi-turn conversation support

Use Case:
- Building chatbots that remember context across messages
- Agents that can decide between multiple tools
- Educational/fact lookup combined with calculation
- Testing stateful agent behavior

Required: Ollama running with llama3.2:3b model
"""

import sys
from pathlib import Path
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

sys.path.insert(0, str(Path(__file__).parent.parent / "py-libraries"))
from utilities import safe_calculate as calculator

# Top-level model name used by this script
model = "gemma4:e2b"

# Import the Ollama LLM wrapper, prompt builder with chat memory support,
# output parser for plain strings, and message classes for chat history.

# Step 1: Load the local model instance.
# The model name is stored in the top-level variable above.
llm = OllamaLLM(model=model)

# Tool 2: Knowledge base lookup function.
def knowledge_base(query: str) -> str:
    """Return information from a small local knowledge base."""
    kb = {
        "python": "Python is a beginner-friendly programming language widely used in AI and data science.",
        "ai agent": "An AI agent is a program that uses a language model to reason and take actions.",
        "ollama": "Ollama is a tool for running language models locally on your computer.",
    }
    for key in kb:
        if key in query.lower():
            return kb[key]
    return "No information found for that query."

# Register tool names to function handlers so the agent can call them.
TOOLS = {
    "calculator": calculator,
    "knowledge_base": knowledge_base,
}

# Step 2: Build the ReAct-style prompt template.
# The system instruction defines the agent's behavior and the required output format.
# MessagesPlaceholder allows past conversation history to be injected as memory.
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant with access to tools and memory of the conversation.

You have access to the following tools:
- calculator: Evaluates a basic math expression. Input should be a valid Python math expression.
- knowledge_base: Looks up information from a local knowledge base. Input should be a search query.

Use this format:

Thought: Reason about what to do
Action: <tool_name>  (must be one of: calculator, knowledge_base)
Action Input: <input to the tool>
Observation: <tool result>
... (repeat as needed)
Thought: I now know the final answer
Final Answer: <your answer>

If you already know the answer without using a tool, go straight to Final Answer.
"""),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
])

# Step 3: Create the LangChain pipeline.
# This sends the formatted prompt to the model and parses the output into a string.
output_parser = StrOutputParser()
chain = prompt | llm | output_parser

# Step 4: Initialize a manual conversation memory store.
# This list will accumulate user and assistant messages across turns.
chat_history: list = []

# Step 5: Define the agent runner that invokes the chain and executes tools.
def run_agent(user_input: str) -> str:
    print(f"\n>>> User: {user_input}")

    # Invoke the chain with the current question and conversation history.
    response = chain.invoke({
        "input": user_input,
        "chat_history": chat_history,
    })

    # Split the model response into lines and scan for actions or a final answer.
    lines = response.splitlines()
    pending_action = None
    final_answer = None

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("Action:"):
            # Capture the tool name when the model requests an action.
            pending_action = stripped.removeprefix("Action:").strip().lower()

        elif stripped.startswith("Action Input:") and pending_action:
            # If action input follows, execute the matching tool.
            action_input = stripped.removeprefix("Action Input:").strip()
            if pending_action in TOOLS:
                observation = TOOLS[pending_action](action_input)
                print(f"[Tool: {pending_action}] Input: {action_input} => {observation}")
            pending_action = None

        elif stripped.startswith("Final Answer:"):
            # Capture the final answer provided by the model.
            final_answer = stripped.removeprefix("Final Answer:").strip()

    # Use the parsed final answer if available; otherwise fall back to the raw response.
    result = final_answer or response.strip()

    # Update chat memory so subsequent turns can reference prior messages.
    chat_history.append(HumanMessage(content=user_input))
    chat_history.append(AIMessage(content=result))

    print(f"<<< Assistant: {result}")
    return result


# Step 6: Run a sample multi-turn conversation through the agent.
run_agent("What is an AI agent?")
run_agent("Now tell me what Ollama is.")
run_agent("Calculate 50 multiplied by 12.")