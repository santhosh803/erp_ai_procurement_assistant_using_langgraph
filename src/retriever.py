"""
Performs similarity search against the FAISS index to retrieve
the most relevant document chunks for a given query.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.embedder import get_embedder
from src.vector_store import load_index
try:
    from langchain.retrievers import EnsembleRetriever
except ImportError:
    from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever


class Retriever:
    def __init__(self, k: int = 4):
        """
        Args:
            k: Number of top chunks to retrieve per query.
        """
        self.k = k
        self._embedder = None
        self._vectorstore = None
        self._bm25_retriever = None

    def _ensure_loaded(self):
        """Lazy-load the embedder, FAISS index, and BM25 retriever on first use."""
        if self._vectorstore is None:
            self._embedder = get_embedder()
            self._vectorstore = load_index(self._embedder)
            
            # Extract documents from FAISS store to initialize the BM25 index in memory
            docs = list(self._vectorstore.docstore._dict.values())
            self._bm25_retriever = BM25Retriever.from_documents(docs)

    def retrieve(self, query: str) -> list[dict]:
        """
        Retrieve top-k relevant chunks for a query using hybrid search (FAISS + BM25 RRF).

        Args:
            query: User's natural language question.

        Returns:
            List of dicts with 'content' and 'source' keys.
        """
        self._ensure_loaded()
        
        # Configure both retrievers dynamically with current k
        faiss_retriever = self._vectorstore.as_retriever(search_kwargs={"k": self.k})
        self._bm25_retriever.k = self.k
        
        # Ensemble both retrievers with equal weighting using Reciprocal Rank Fusion (RRF)
        ensemble = EnsembleRetriever(
            retrievers=[faiss_retriever, self._bm25_retriever],
            weights=[0.5, 0.5]
        )
        
        results = ensemble.invoke(query)

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
