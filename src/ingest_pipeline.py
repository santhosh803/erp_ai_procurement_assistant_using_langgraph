"""
End-to-end pipeline: Load docs → Chunk → Embed → Store in FAISS.
Run this script ONCE to build the knowledge base index.
"""

import os
import sys

# Ensure src/ is importable when run from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.document_loader import load_documents
from src.text_chunker import chunk_documents
from src.embedder import get_embedder
from src.vector_store import build_and_save_index
from src.config import EMBEDDING_MODEL_ID


def run_ingestion():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_folder = os.path.join(base_dir, "data")

    print("=" * 60)
    print("  ERP AI Procurement Assistant — Ingestion Pipeline")
    print("=" * 60)

    # Step 1: Load documents
    print("\n[1/4] Loading documents from /data ...")
    documents = load_documents(data_folder)
    if not documents:
        print("ERROR: No documents found. Check your /data folder.")
        sys.exit(1)

    # Step 2: Chunk documents
    print("\n[2/4] Chunking documents ...")
    chunks = chunk_documents(documents, chunk_size=500, chunk_overlap=50)

    # Step 3: Load embedder
    print(f"\n[3/4] Loading embedding model ({EMBEDDING_MODEL_ID}) ...")
    embedder = get_embedder()

    # Step 4: Build and save FAISS index
    print("\n[4/4] Building and saving FAISS index ...")
    build_and_save_index(chunks, embedder)

    print("\n" + "=" * 60)
    print(f"  Ingestion COMPLETE. {len(chunks)} chunks indexed.")
    print("  You can now run the API or RAG pipeline.")
    print("=" * 60)


if __name__ == "__main__":
    run_ingestion()
