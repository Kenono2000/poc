import dspy
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="AI Video Prompt Optimizer API")

lm = dspy.LM(
    model='ollama/gemma4:e2b',
    api_base='http://localhost:11434',
    api_key='none',
    config={
        "num_ctx": 65536,
        "temperature": 0.2,
        "top_p": 0.9,
        "repeat_penalty": 1.15
    }
)

dspy.settings.configure(lm=lm)


class VideoPromptGenerator(dspy.Signature):
    """Convert a basic video concept into a structured, highly descriptive cinematic prompt."""
    creative_brief = dspy.InputField(desc="The core high-level video concept or idea from the user")
    optimized_prompt = dspy.OutputField(desc="A detailed prompt following the Subject -> Style -> Camera -> Lighting format")


optimizer_module = dspy.ChainOfThought(VideoPromptGenerator)


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    user_brief: str
    rationale: str
    optimized_prompt: str


@app.post("/api/chat/optimize", response_model=ChatResponse)
async def optimize_user_prompt(payload: ChatRequest):
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="The creative brief cannot be blank or empty.")
    
    try:
        response = optimizer_module(creative_brief=payload.message)
        rationale_text = getattr(response, 'rationale', "Model did not provide a reasoning chain.")
        optimized_prompt_text = getattr(response, 'optimized_prompt', "")
        
        if not optimized_prompt_text:
            raise ValueError("Model outputted a blank prompt response.")

        return ChatResponse(
            user_brief=payload.message,
            rationale=rationale_text,
            optimized_prompt=optimized_prompt_text
        )
    except (dspy.utils.Error, ValueError, TypeError) as e:
        raise HTTPException(status_code=500, detail=f"Internal Engine Processing Failure: {e!s}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("dspy_server:app", host="127.0.0.1", port=8000, reload=True)
