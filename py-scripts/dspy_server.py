from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import dspy

# Initialize the FastAPI App instance
app = FastAPI(title="AI Video Prompt Optimizer API")

# 1. Configuration Client: Connect DSPy directly to your local Ollama engine port
lm = dspy.LM(
    model='ollama/gemma4:e2b',                  # Specify your pulled Ollama model [cite: 9]
    api_base='http://localhost:11434',      # 💡 FIX: Remove '/v1' from the end
    api_key='none',                         # Ollama does not require an API key [cite: 9]
    config=dict(
        num_ctx=65536,                      # 64K context window [cite: 10]
        temperature=0.2,                    # Low temperature minimizes malformed outputs [cite: 10]
        top_p=0.9,
        repeat_penalty=1.15
    )
)

# Set the configured language model engine globally in your environment space
dspy.settings.configure(lm=lm)


# 2. Define the Structural Task Architecture using a DSPy Signature
class VideoPromptGenerator(dspy.Signature):
    """Convert a basic video concept into a structured, highly descriptive cinematic prompt."""
    creative_brief = dspy.InputField(desc="The core high-level video concept or idea from the user")
    optimized_prompt = dspy.OutputField(desc="A detailed prompt following the Subject -> Style -> Camera -> Lighting format")


# Wrap your task architecture using the modern structured chain-of-thought processing module
optimizer_module = dspy.ChainOfThought(VideoPromptGenerator)


# 3. Define Pydantic Data Structures for API Validation Guardrails
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    user_brief: str
    rationale: str
    optimized_prompt: str

# 4. Expose the Integrated Chat Bot API Endpoint Router
@app.post("/api/chat/optimize", response_model=ChatResponse)
async def optimize_user_prompt(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="The creative brief cannot be blank or empty.")
    
    try:
        # Run the incoming chat message through the DSPy pipeline processing layer
        response = optimizer_module(creative_brief=payload.message)
        
        # 💡 FIX: Safely retrieve 'rationale' or fall back to an empty string if omitted by the model
        rationale_text = getattr(response, 'rationale', "Model did not provide a reasoning chain.")
        optimized_prompt_text = getattr(response, 'optimized_prompt', "")
        
        if not optimized_prompt_text:
            raise ValueError("Model outputted a blank prompt response.")

        return ChatResponse(
            user_brief=payload.message,
            rationale=rationale_text,
            optimized_prompt=optimized_prompt_text
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Engine Processing Failure: {str(e)}")


# 5. Native Execution Entrypoint
if __name__ == "__main__":
    import uvicorn
    # Point precisely to your string module name ('dspy_server') mapping without a '.py' extension literal
    uvicorn.run("dspy_server:app", host="127.0.0.1", port=8000, reload=True)
    