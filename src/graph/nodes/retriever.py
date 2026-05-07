"""retrieve_chunks — wraps the existing FAISS Retriever class."""

from src.graph.config import DEFAULT_K, RETRY_K
from src.graph.tools import expand_query
from src.graph.utils import traced
from src.retriever import Retriever

# Cached singleton — Retriever lazy-loads embedder + FAISS index on first use,
# so repeated graph invocations don't repay that cost.
_retriever: Retriever | None = None


def _get_retriever(k: int) -> Retriever:
    global _retriever
    if _retriever is None:
        _retriever = Retriever(k=k)
    else:
        _retriever.k = k
    return _retriever


@traced("retriever")
def retrieve_chunks(state: dict) -> dict:
    attempt = state.get("retrieval_attempt", 0)
    is_retry = attempt >= 1

    k = RETRY_K if is_retry else state.get("retrieval_k", DEFAULT_K)
    raw_query = state.get("query", "")
    query = expand_query(raw_query) if is_retry else raw_query

    chunks = _get_retriever(k).retrieve(query)

    return {
        "chunks": chunks,
        "retrieval_attempt": attempt + 1,
        "retrieval_k": k,
        "_summary": f"{len(chunks)} chunks @ k={k}" + (" (retry)" if is_retry else ""),
        "_payload": {
            "k": k,
            "attempt": attempt + 1,
            "expanded_query": query if is_retry else None,
            "chunk_previews": [
                {"source": c.get("source"), "preview": (c.get("content", "") or "")[:120]}
                for c in chunks
            ],
        },
    }
