"""
Simple LLM Invocation with ChatOllama

Purpose: The most minimal example of using ChatOllama for single-turn inference.
Demonstrates using the ChatOllama class directly without prompts or chains.

Features:
- ChatOllama model (llama3.2:3b) with zero temperature for deterministic output
- Direct model invocation without prompt templates
- Simple single-turn question answering

Use Case:
- Quick model testing
- Understanding ChatOllama vs OllamaLLM differences
- Baseline for building more complex agents

Required: Ollama running with llama3.2:3b model
"""

# Import the ChatOllama class from the langchain_ollama library
from langchain_ollama import ChatOllama

# Top-level model name used by this script
model = "gemma4:e2b"

# Initialize the model with the configured model name
# Create an instance of the ChatOllama model using the top-level model variable with zero temperature for deterministic responses
llm = ChatOllama(
    model=model,
    temperature=0,
)

# Invoke the model
# Send a prompt to the model and get the response
response = llm.invoke("Explain the benefits of local LLMs in one sentence.")

# Print the response
# Output the content of the model's response
print(response.content)