import dspy

# Configure the Ollama Local Engine Client
# The dspy.Ollama class is available in newer versions. For broader compatibility,
# we'll use the general-purpose dspy.LM class which is compatible with older versions.
lm = dspy.LM(
    model='ollama/gemma4:e2b',          # Specify your pulled Ollama model, prefixed with 'ollama/'
    api_base='http://localhost:11434',  # Use api_base for the URL
    api_key='none',                     # Ollama does not require an API key
    config=dict(
        max_tokens=4096,                # Max tokens for the generation
        temperature=0.2,                # Low temperature minimizes malformed outputs
        top_p=0.9,                      # Nucleus sampling
        num_ctx=8192,                   # Context window size
        repeat_penalty=1.15             # Penalize repeated tokens
    )
)

 
dspy.settings.configure(lm=lm)

# # Define your structured Signature task
# class BasicQA(dspy.Signature):
#     """Answer questions with a short, precise factual sentence."""
#     question = dspy.InputField(desc="The user inquiry")
#     answer = dspy.OutputField(desc="A direct, concise answer")

# # Initialize the predictor
# predictor = dspy.Predict(BasicQA)

# # Trigger the prediction loop
# response = predictor(question="What is the benefit of keeping a local model resident in VRAM?")

# # ❌ OLD: print(f"Question: {response.question}")
# #  FIX: Print your input string directly, and access the exact OutputField name from the response
# print(f"Question: What is the benefit of keeping a local model resident in VRAM?")
# print(f"Answer: {response.answer}")

# 1. Define the structural Signature for video prompts
class VideoPromptGenerator(dspy.Signature):
    """Convert a basic video concept into a structured, highly descriptive cinematic prompt."""
    creative_brief = dspy.InputField(desc="The core video concept or idea")
    optimized_prompt = dspy.OutputField(desc="A detailed prompt following the Subject -> Style -> Camera -> Lighting format")

# 2. Use a Module that supports iterative optimization
# (For deeper algorithmic tuning, you would compile this module using a dataset of good examples)
prompt_optimizer = dspy.ChainOfThought(VideoPromptGenerator)

# 3. Execute the optimizer pass
brief = "A futuristic cyberpunk hover-car driving down a rainy street."
result = prompt_optimizer(creative_brief=brief)

# Safely access the 'rationale' and 'optimized_prompt' attributes.
# The model may not always return a 'rationale', so we provide a default value.
rationale_text = getattr(result, 'rationale', "Model did not provide a reasoning chain.").strip()
optimized_prompt_text = getattr(result, 'optimized_prompt', "").strip()

print(f"Creative Brief: {brief}\n")
print(f"Rationale:\n{rationale_text}\n")
print(f"Optimized Prompt:\n{optimized_prompt_text}")