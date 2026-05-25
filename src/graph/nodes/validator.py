"""validate_chunks — pure-Python relevance scoring (no extra LLM call)."""

import re

from src.graph.config import CONFIDENCE_THRESHOLD, MAX_RETRIEVAL_ATTEMPTS
from src.graph.utils import traced

_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "and", "or", "but", "if", "then", "of", "in", "on", "at", "to", "for",
    "with", "by", "from", "as", "what", "who", "whom", "whose", "which",
    "where", "when", "why", "how", "do", "does", "did", "can", "could",
    "should", "would", "may", "might", "i", "you", "we", "they", "it",
    "this", "that", "these", "those", "there", "here", "about",
}

_TOKEN_RE = re.compile(r"[a-zA-Z]{2,}")


def _tokens(text: str) -> set[str]:
    return {t for token in _TOKEN_RE.findall(text or "") if (t := token.lower()) not in _STOPWORDS}


def _score(query: str, chunks: list[dict]) -> tuple[float, dict]:
    if not chunks:
        return 0.0, {"reason": "no_chunks"}

    qtoks = _tokens(query)
    if not qtoks:
        return 0.5, {"reason": "no_query_tokens"}  # don't punish trivial queries

    joined = " ".join(c.get("content", "") for c in chunks)
    ctoks = _tokens(joined)

    overlap = len(qtoks & ctoks) / max(1, len(qtoks))   # 0..1

    avg_len = sum(len(c.get("content", "")) for c in chunks) / len(chunks)
    length_factor = min(1.0, avg_len / 400.0)            # 400 chars ≈ healthy chunk

    confidence = round(0.6 * overlap + 0.4 * length_factor, 3)
    return confidence, {
        "overlap": round(overlap, 3),
        "avg_chunk_len": round(avg_len, 1),
        "length_factor": round(length_factor, 3),
    }


@traced("validator")
def validate_chunks(state: dict) -> dict:
    query = state.get("query", "")
    chunks = state.get("chunks", [])
    attempt = state.get("retrieval_attempt", 0)

    confidence, breakdown = _score(query, chunks)
    forced = attempt >= MAX_RETRIEVAL_ATTEMPTS
    is_relevant = confidence >= CONFIDENCE_THRESHOLD or forced

    if forced and confidence < CONFIDENCE_THRESHOLD:
        reason = f"forced after {attempt} attempts (conf={confidence})"
    else:
        reason = f"score={confidence} (threshold={CONFIDENCE_THRESHOLD})"

    return {
        "confidence": confidence,
        "is_relevant": is_relevant,
        "validator_reason": reason,
        "_summary": f"conf={confidence} relevant={is_relevant}",
        "_payload": {
            "confidence": confidence,
            "is_relevant": is_relevant,
            "reason": reason,
            "breakdown": breakdown,
        },
    }
