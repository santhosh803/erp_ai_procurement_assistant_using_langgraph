"""update_memory — deterministic rolling-window summary (no LLM call)."""

from typing import Optional

from src.graph.config import MEMORY_WINDOW
from src.graph.utils import traced

_TURN_LIMIT = 200    # chars per query/answer kept in summary
_ANSWER_PREVIEW = 80   # answer preview length in summary line


def _pair_turns(history: list[dict]) -> list[tuple[str, str]]:
    """Walk history into (user, assistant) pairs."""
    pairs: list[tuple[str, str]] = []
    pending_user: Optional[str] = None
    for msg in history or []:
        role = msg.get("role")
        content = (msg.get("content") or "")[:_TURN_LIMIT]
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user is not None:
            pairs.append((pending_user, content))
            pending_user = None
    return pairs


@traced("memory")
def update_memory(state: dict) -> dict:
    history = state.get("history", []) or []
    query = (state.get("query") or "")[:_TURN_LIMIT]
    answer = (state.get("answer") or "")[:_TURN_LIMIT]

    pairs = _pair_turns(history)
    if query and answer:
        pairs.append((query, answer))

    pairs = pairs[-MEMORY_WINDOW:]

    summary = " | ".join(
        f"Q: {q} → A: {a[:_ANSWER_PREVIEW]}{'…' if len(a) > _ANSWER_PREVIEW else ''}"
        for q, a in pairs
    )

    return {
        "memory_summary": summary,
        "_summary": f"{len(pairs)} turns",
        "_payload": {"turns": len(pairs), "summary_preview": summary[:200]},
    }
