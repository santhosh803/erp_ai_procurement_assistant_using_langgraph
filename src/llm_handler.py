"""
Calls the HuggingFace Serverless Inference API to generate a response.
Model: Qwen/Qwen2.5-7B-Instruct

Setup:
  - Ensure HF_TOKEN is set in your .env file
"""

import os
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

# ── Configuration 
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_ID = os.getenv("HF_MODEL_ID", "Qwen/Qwen2.5-7B-Instruct")

# Initialize the client. It automatically picks up HF_TOKEN from the environment
client = InferenceClient(model=MODEL_ID, token=HF_TOKEN)


def generate_response(prompt: str) -> str:
    """
    Send a prompt to the HuggingFace Inference API and return the generated text.

    Args:
        prompt: The full prompt string (with RAG context injected).

    Returns:
        The LLM's response as a string.
    """
    if not HF_TOKEN:
        return (
            "ERROR: HF_TOKEN is not set. "
            "Please add your HuggingFace token to the .env file. "
            "Get your token at: https://huggingface.co/settings/tokens"
        )

    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.2,
            top_p=0.9
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"ERROR: HuggingFace API connection failed — {str(e)}"


def classify(prompt: str) -> str:
    """
    Lightweight classification call: short output, deterministic sampling.

    Used by the query_classifier node to label a query as FACTUAL / WORKFLOW / CHAT.
    Returns the raw LLM output (caller is responsible for parsing).
    """
    if not HF_TOKEN:
        return "FACTUAL"  # safe default — routes to retrieval

    try:
        response = client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8,
            temperature=0.0,
            top_p=1.0,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "FACTUAL"


if __name__ == "__main__":
    test_prompt = "What is a Purchase Order in SAP procurement? Answer in 2 sentences."
    print("Testing HuggingFace Inference API connection...")
    print(f"Model : {MODEL_ID}")
    print(f"Token : {HF_TOKEN[:10]}...{'*' * 20 if HF_TOKEN else 'MISSING'}\n")
    print(generate_response(test_prompt))

