"""
Creates, saves, and loads the FAISS vector index.
"""

import os
import json
from langchain_community.vectorstores import FAISS


# Resolve the project root directory
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_DIR = os.path.join(_BASE_DIR, "faiss_index")
INDEX_NAME = "erp_index"


def build_and_save_index(chunks: list, embedder) -> FAISS:
    """
    Build a FAISS index from document chunks and save to disk.

    Args:
        chunks: List of chunked LangChain Document objects.
        embedder: HuggingFaceEmbeddings instance.

    Returns:
        FAISS vectorstore object.
    """
    os.makedirs(INDEX_DIR, exist_ok=True)

    print(f"  Building FAISS index from {len(chunks)} chunks...")
    vectorstore = FAISS.from_documents(chunks, embedder)
    vectorstore.save_local(INDEX_DIR, index_name=INDEX_NAME)

    # Save metadata (chunk count) alongside the index
    metadata = {"chunk_count": len(chunks)}
    with open(os.path.join(INDEX_DIR, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  FAISS index saved to: {INDEX_DIR}")
    return vectorstore


def load_index(embedder) -> FAISS:
    """
    Load an existing FAISS index from disk.

    Args:
        embedder: HuggingFaceEmbeddings instance (must match the one used to build).

    Returns:
        FAISS vectorstore object.
    """
    if not os.path.exists(os.path.join(INDEX_DIR, f"{INDEX_NAME}.faiss")):
        raise FileNotFoundError(
            f"No FAISS index found at {INDEX_DIR}. "
            "Please run ingest_pipeline.py first."
        )

    vectorstore = FAISS.load_local(
        INDEX_DIR,
        embedder,
        index_name=INDEX_NAME,
        allow_dangerous_deserialization=True,
    )
    print(f"  FAISS index loaded from: {INDEX_DIR}")
    return vectorstore
