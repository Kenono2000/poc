"""
Conversational Agent with In-Memory Chat History

Purpose: Demonstrates a multi-turn conversation with persistent session memory.
The agent remembers all previous messages in a conversation.

Features:
- ChatOllama model (llama3.2:3b)
- RunnableWithMessageHistory for automatic memory management
- Session-based conversation history storage
- Multi-turn interactions with context awareness
- Simple in-memory storage (suitable for single-session conversations)

Use Case:
- Building conversational interfaces/chatbots
- Testing memory-aware LLM interactions
- Understanding LangChain's message history patterns
- Session-based user interactions

Example:
- User introduces themselves: "Hi, my name is Alex"
- Model remembers the name in subsequent messages

Required: Ollama running with llama3.2:3b model
"""

# Import necessary modules for LangChain chat, memory, and prompts
from langchain_ollama import ChatOllama
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Top-level model name used by this script
model = "gemma4:e2b"

# Initialize the language model using the configured model name
llm = ChatOllama(model=model)

# Define the chat prompt template with system message, history placeholder, and human input
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

# Create a chain by piping the prompt to the language model
chain = prompt | llm

# Initialize a store dictionary to hold chat message histories for different sessions
store = {}

# Function to get or create the chat history for a given session ID
def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

# Create a runnable chain with message history support
conversation = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

# Configuration for the session, specifying the session ID
config = {"configurable": {"session_id": "default"}}

# First interaction: Send a message to introduce the name
conversation.invoke({"input": "Hi, my name is Alex."}, config=config)

# Second interaction: Ask for the name to test memory, and print the response
response = conversation.invoke({"input": "What is my name?"}, config=config)
print(response.content)