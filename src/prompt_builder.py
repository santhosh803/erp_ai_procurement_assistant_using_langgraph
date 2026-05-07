"""
Constructs a context-injected prompt for the LLM using retrieved chunks.
"""


SYSTEM_INSTRUCTION = """You are an expert ERP Procurement Assistant specializing in SAP S/4HANA Sourcing & Procurement.

Your job is to answer user questions accurately using ONLY the context provided below.
If the answer is not found in the context, say: "I don't have enough information to answer that from the provided documents."

Do NOT make up information. Be concise, professional, and specific.
"""


def build_prompt(query: str, retrieved_chunks: list[dict]) -> str:
    """
    Build a prompt string by injecting retrieved context into the template.

    Args:
        query: The user's question.
        retrieved_chunks: List of dicts with 'content' and 'source' keys.

    Returns:
        Fully formatted prompt string.
    """
    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        source = chunk.get("source", "unknown")
        content = chunk.get("content", "").strip()
        context_parts.append(f"[Source {i}: {source}]\n{content}")

    context_text = "\n\n".join(context_parts)

    prompt = f"""{SYSTEM_INSTRUCTION}

--- CONTEXT START ---
{context_text}
--- CONTEXT END ---

User Question: {query}

Answer:"""

    return prompt
