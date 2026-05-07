"""
Generates vector embeddings using sentence-transformers (all-MiniLM-L6-v2).
"""

from langchain_huggingface import HuggingFaceEmbeddings


def get_embedder() -> HuggingFaceEmbeddings:
    """
    Returns a HuggingFaceEmbeddings instance using all-MiniLM-L6-v2.
    This model is lightweight, fast, and well-suited for semantic search.
    """
    embedder = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return embedder
