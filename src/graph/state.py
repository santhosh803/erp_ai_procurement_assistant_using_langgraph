"""
ProcurementState — the shared state schema flowing through the LangGraph.

Every node reads a slice of this state and returns a partial dict; LangGraph
merges the partials. The `trace` field uses an `add` reducer so each node can
append its own TraceEvent without clobbering prior events.
"""

from operator import add
from typing import Annotated, Literal, Optional, TypedDict

QueryType = Literal["factual_lookup", "workflow_guidance", "general_chat"]


class Chunk(TypedDict, total=False):
    content: str
    source: str
    score: Optional[float]


class TraceEvent(TypedDict, total=False):
    node: str
    status: str          # "ok" | "skipped" | "error"
    duration_ms: float
    summary: str
    payload: dict


class ToolResult(TypedDict, total=False):
    tool_name: str
    input: dict
    output: dict


class ProcurementState(TypedDict, total=False):
    # Input
    query: str
    session_id: str
    history: list[dict]                  # [{role: "user"|"assistant", content: str}]

    # Classification
    query_type: QueryType
    classifier_raw: str

    # Retrieval
    retrieval_k: int
    retrieval_attempt: int
    chunks: list[Chunk]

    # Validation
    confidence: float
    is_relevant: bool
    validator_reason: str

    # Tools
    tool_results: list[ToolResult]

    # Generation
    prompt: str
    answer: str
    sources: list[str]

    # Memory
    memory_summary: str

    # Observability — appendable across nodes
    trace: Annotated[list[TraceEvent], add]
    error: Optional[str]
