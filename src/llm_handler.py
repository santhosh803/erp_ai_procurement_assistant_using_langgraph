"""
Calls the Groq API to generate a response.
Model: llama-3.3-70b-versatile (or configured in GROQ_MODEL_ID)

Setup:
  - Ensure GROQ_API_KEY is set in your .env file
"""

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

from src.config import GROQ_API_KEY, GROQ_MODEL_ID

# Initialize the Groq client.
client = Groq(api_key=GROQ_API_KEY)


def generate_response(prompt: str) -> str:
    """
    Send a prompt to the Groq API and return the generated text.

    Args:
        prompt: The full prompt string (with RAG context injected).

    Returns:
        The LLM's response as a string.
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "gsk_your_key_here":
        return (
            "ERROR: GROQ_API_KEY is not configured or still using the placeholder. "
            "Please set your Groq API key in the .env file. "
            "Get your key at: https://console.groq.com/"
        )

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL_ID,
            max_tokens=512,
            temperature=0.2,
            top_p=0.9
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"ERROR: Groq API connection failed — {str(e)}"


def classify(prompt: str) -> str:
    """
    Lightweight classification call: short output, deterministic sampling.

    Used by the query_classifier node to label a query as FACTUAL / WORKFLOW / CHAT.
    Returns the raw LLM output (caller is responsible for parsing).
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "gsk_your_key_here":
        return "FACTUAL"  # safe default — routes to retrieval

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=GROQ_MODEL_ID,
            max_tokens=8,
            temperature=0.0,
            top_p=1.0,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "FACTUAL"


if __name__ == "__main__":
    test_prompt = "What is a Purchase Order in SAP procurement? Answer in 2 sentences."
    print("Testing Groq API connection...")
    print(f"Model : {GROQ_MODEL_ID}")
    print(f"API Key : {GROQ_API_KEY[:10] if GROQ_API_KEY else 'NONE'}...{'*' * 20 if GROQ_API_KEY else 'MISSING'}\n")
    print(generate_response(test_prompt))


