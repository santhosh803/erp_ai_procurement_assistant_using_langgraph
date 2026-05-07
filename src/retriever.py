"""
Performs similarity search against the FAISS index to retrieve
the most relevant document chunks for a given query.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.embedder import get_embedder
from src.vector_store import load_index


class Retriever:
    def __init__(self, k: int = 4):
        """
        Args:
            k: Number of top chunks to retrieve per query.
        """
        self.k = k
        self._embedder = None
        self._vectorstore = None

    def _ensure_loaded(self):
        """Lazy-load the embedder and FAISS index on first use."""
        if self._vectorstore is None:
            self._embedder = get_embedder()
            self._vectorstore = load_index(self._embedder)

    def retrieve(self, query: str) -> list[dict]:
        """
        Retrieve top-k relevant chunks for a query.

        Args:
            query: User's natural language question.

        Returns:
            List of dicts with 'content' and 'source' keys.
        """
        self._ensure_loaded()
        results = self._vectorstore.similarity_search(query, k=self.k)

        chunks = []
        for doc in results:
            chunks.append({
                "content": doc.page_content.strip(),
                "source": doc.metadata.get("source", "unknown"),
            })
        return chunks


if __name__ == "__main__":
    retriever = Retriever(k=4)
    query = "What is a purchase requisition?"
    results = retriever.retrieve(query)
    print(f"Top {len(results)} chunks for: '{query}'\n")
    for i, chunk in enumerate(results, 1):
        print(f"--- Chunk {i} [{chunk['source']}] ---")
        print(chunk["content"][:300])
        print()
