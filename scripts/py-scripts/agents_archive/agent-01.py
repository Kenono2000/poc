"""
Basic Ollama LLM Chat Agent

Purpose: Demonstrates the simplest LangChain interaction with a local Ollama model.
This is a foundational example for using language models without complex logic.

Features:
- Loads a local Ollama model (llama3.2:3b)
- Creates a simple chat prompt template
- Sends a question to the model and receives a string response
- No tools, memory, or agent logic

Use Case:
- Learning how to set up basic LLM interactions
- Testing Ollama connectivity
- Simple text generation tasks

Required: Ollama running with llama3.2:3b model
"""

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

# Top-level model name used by this script
model = "gemma4:e2b"

# Import the Ollama LLM wrapper, prompt template builder, and a simple string parser.
# OllamaLLM is the model interface. ChatPromptTemplate builds the chat-style prompt.
# StrOutputParser ensures the LLM output is returned as a plain Python string.

# 1. Initialize the Ollama LLM instance with the desired model.
#    The model name is stored in the top-level variable above.
llm = OllamaLLM(model=model)

# 2. Define a chat prompt template for the assistant.
#    The template includes a system message that configures the assistant's persona
#    and a user message placeholder that will be filled with actual input text.
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a witty assistant who gives concise answers."),
    ("user", "{input}")
])

# 3. Compose a LangChain expression pipeline (chain) using the prompt, the LLM,
#    and the output parser. The "|" operator wires the components together.
#    - prompt: formats the chat messages with the user's input
#    - llm: sends the formatted prompt to the Ollama model and returns a generated response
#    - StrOutputParser: converts the raw model response into a clean Python string
chain = prompt | llm | StrOutputParser()

# 4. Execute the chain by invoking it with concrete input data.
#    The template placeholder {input} is replaced with the provided question.
response = chain.invoke({"input": "Why is the sky blue, but make it funny?"})

# Print the final assistant response to the console.
print(f"Assistant: {response}")