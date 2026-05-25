"""
ProcurementState — the shared state schema flowing through the LangGraph.

Every node reads a slice of this state and returns a partial dict; LangGraph
merges the partials. The `trace` field uses an `add` reducer so each node can
append its own TraceEvent without clobbering prior events.
"""

from operator import add
from typing import Annotated, Literal, Optional, TypedDict
try:
    from typing import NotRequired
except ImportError:
    from typing_extensions import NotRequired

QueryType = Literal["factual_lookup", "workflow_guidance", "general_chat"]

class Chunk(TypedDict):
    content: str
    source: str
    score: NotRequired[Optional[float]]

class TraceEvent(TypedDict):
    node: str
    status: str          # "ok" | "skipped" | "error"
    duration_ms: float
    summary: NotRequired[str]
    payload: NotRequired[dict]

class ToolResult(TypedDict):
    tool_name: str
    input: dict
    output: dict

class ProcurementState(TypedDict):
    # Input (Required)
    query: str
    session_id: str
    history: list[dict]                  # [{role: "user"|"assistant", content: str}]

    # Optional / Incremental state populated by nodes
    query_type: NotRequired[QueryType]
    classifier_raw: NotRequired[str]

    retrieval_k: NotRequired[int]
    retrieval_attempt: NotRequired[int]
    chunks: NotRequired[list[Chunk]]

    confidence: NotRequired[float]
    is_relevant: NotRequired[bool]
    validator_reason: NotRequired[str]

    tool_results: NotRequired[list[ToolResult]]

    prompt: NotRequired[str]
    answer: NotRequired[str]
    sources: NotRequired[list[str]]

    original_query: NotRequired[str]
    grader_decision: NotRequired[str]
    grader_reason: NotRequired[str]

    memory_summary: NotRequired[str]

    trace: Annotated[list[TraceEvent], add]
    error: NotRequired[str]
