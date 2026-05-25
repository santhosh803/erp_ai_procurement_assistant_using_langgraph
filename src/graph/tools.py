"""
Lightweight, pure-Python tools called by the tool_caller node.

These do NOT call the LLM — they exist to demonstrate structured tool use
inside a LangGraph workflow. The output shape matches `ToolResult` in
src/graph/state.py.
"""

import re
from typing import Set

from src.graph.config import ID_PATTERN, STEP_INTENT_PATTERN, SYNONYM_MAP

_ID_RE = re.compile(ID_PATTERN, re.IGNORECASE)
_STEP_RE = re.compile(STEP_INTENT_PATTERN, re.IGNORECASE)
# Matches "1.", "1)", "Step 1:", "Step 1." at start of a line
_STEP_LINE_RE = re.compile(r"(?:^|\n)\s*(?:step\s+)?(\d{1,2})[.\):]", re.IGNORECASE)


def has_id_pattern(query: str) -> bool:
    return bool(_ID_RE.search(query or ""))


def has_step_intent(query: str) -> bool:
    return bool(_STEP_RE.search(query or ""))


def id_extractor(query: str) -> dict:
    """Pull PO/PR identifiers out of a query string."""
    matches = _ID_RE.findall(query or "")
    # findall on this pattern returns the captured group ("PO"/"PR") only,
    # so we re-run with finditer to get full spans.
    full = [m.group(0) for m in _ID_RE.finditer(query or "")]
    return {
        "tool_name": "id_extractor",
        "input": {"query": query},
        "output": {"ids": full, "kinds": list({m.upper() for m in matches})},
    }


def step_counter(chunks: list[dict]) -> dict:
    """
    Count the largest contiguous numbered-step sequence across retrieved chunks.

    We look for "1.", "2.", "Step 3:", etc. and take the max integer seen as a
    proxy for total steps. This is a heuristic — good enough for SOP-style docs.
    """
    seen: Set[int] = set()
    text = "\n".join(c.get("content", "") for c in (chunks or []))
    for m in _STEP_LINE_RE.finditer(text):
        try:
            seen.add(int(m.group(1)))
        except ValueError:
            continue

    # Find the longest run starting at 1
    longest_run = 0
    if 1 in seen:
        i = 1
        while i in seen:
            longest_run += 1
            i += 1

    return {
        "tool_name": "step_counter",
        "input": {"chunk_count": len(chunks or [])},
        "output": {
            "max_step_seen": max(seen) if seen else 0,
            "contiguous_from_one": longest_run,
            "all_step_numbers": sorted(seen),
        },
    }


def expand_query(query: str) -> str:
    """Replace short SAP acronyms with their expansions for a retry retrieval."""
    expanded = query
    for acronym, full in SYNONYM_MAP.items():
        # Word-boundary, case-insensitive
        expanded = re.sub(rf"\b{re.escape(acronym)}\b", f"{acronym} ({full})",
                          expanded, flags=re.IGNORECASE)
    return expanded
