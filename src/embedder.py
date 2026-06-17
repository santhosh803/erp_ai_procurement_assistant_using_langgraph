"""
Generates vector embeddings using sentence-transformers (all-MiniLM-L6-v2).
"""

from langchain_huggingface import HuggingFaceEmbeddings


from src.config import EMBEDDING_MODEL_ID


def get_embedder() -> HuggingFaceEmbeddings:
    """
    Returns a HuggingFaceEmbeddings instance using the configured model.
    This model is lightweight, fast, and well-suited for semantic search.
    """
    embedder = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_ID,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    return embedder 
