"""
ReAct-Style Agent with Calculator Tool

Purpose: Demonstrates a ReAct (Reasoning + Acting) agent that uses local tools
to solve problems. The agent thinks through a problem and decides when to use tools.

Features:
- Local Ollama LLM (llama3.2:3b)
- Calculator tool for mathematical expressions
- ReAct-style reasoning (Thought -> Action -> Observation)
- Parses model responses to extract and execute tool calls
- Manual tool implementation without LangChain agents library

Use Case:
- Math problem solving with step-by-step reasoning
- Understanding ReAct pattern for agent design
- Teaching how agents decide when to use tools

Required: Ollama running with llama3.2:3b model
"""

import sys
from pathlib import Path
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

sys.path.insert(0, str(Path(__file__).parent.parent / "py-libraries"))
from utilities import safe_calculate as calculator

# Top-level model name used by this script
model = "gemma4:e2b"

# Import the Ollama model wrapper, a chat prompt builder, and a simple string output parser.
# The prompt builder creates the structured chat messages sent to the model.
# The string parser ensures the final output is returned as a plain Python string.

# Step 1: Load the local Ollama model instance.
# The model name is stored in the top-level variable above.
llm = OllamaLLM(model=model)

# Step 2: Define a ReAct-style prompt template that instructs the model how to think.
# The system message describes the tool, the expected Thought/Action/Observation structure,
# and the final answer format. The human message gets replaced with the user's question.
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a helpful assistant that solves math problems step by step.

You have access to a calculator tool. Use the following format:

Thought: Think about what needs to be calculated
Action: calculator
Action Input: <a valid Python math expression>
Observation: <result of the calculation>
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: <your final answer>

Only use Python-compatible math expressions as input to the calculator.
"""),
    ("human", "{input}"),
])

# Step 4: Build the LangChain pipeline.
# The pipeline sends the formatted prompt into the model and parses the output to a string.
output_parser = StrOutputParser()
chain = prompt | llm | output_parser

# Step 5: Run the agent and interpret ReAct-style outputs.
def run_agent(question: str):
    # Print the original question for context.
    print(f"\n--- Input ---\n{question}\n")

    # Invoke the chain with the user question substituted into the prompt.
    response = chain.invoke({"input": question})
    print(f"--- Raw Response ---\n{response}\n")

    # Split the model response into lines so we can detect actions and the final answer.
    lines = response.splitlines()
    final_answer = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Detect a tool action request from the model.
        if line.startswith("Action:") and "calculator" in line.lower():
            # If the next line contains the action input, extract it.
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("Action Input:"):
                expr = lines[i + 1].strip().removeprefix("Action Input:").strip()
                # Execute the local calculator tool and print the result.
                result = calculator(expr)
                print(f"[Tool Call] calculator({expr}) = {result}")
        elif line.startswith("Final Answer:"):
            # Capture the final answer from the model's output.
            final_answer = line.removeprefix("Final Answer:").strip()

        i += 1

    # Print either the parsed final answer or the original raw response if no final answer was found.
    print("\n--- Agent Response ---")
    print(final_answer or response)

# Step 6: Provide a sample math question to the agent.
run_agent("What is 245 multiplied by 18, and then divided by 5?")