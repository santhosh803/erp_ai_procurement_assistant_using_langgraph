"""
StateGraph topology for the ERP procurement assistant.

Nodes (in src/graph/nodes/):
    classifier → retriever → validator → [tool_caller] → response_generator → memory

Edges:
    classifier ─(general_chat)──────────────────────► response_generator
    classifier ─(factual / workflow)────────────────► retriever
    retriever ──────────────────────────────────────► validator
    validator ─(¬relevant ∧ attempts<MAX)───────────► retriever       # retry loop
    validator ─(workflow OR ID pattern)─────────────► tool_caller
    validator ─(otherwise)──────────────────────────► response_generator
    tool_caller ────────────────────────────────────► response_generator
    response_generator ─────────────────────────────► memory ─► END
"""

from langgraph.graph import END, START, StateGraph

from src.graph.config import GRAPH_RECURSION_LIMIT, MAX_RETRIEVAL_ATTEMPTS
from src.graph.nodes import (
    call_tools,
    classify_query,
    generate,
    retrieve_chunks,
    update_memory,
    validate_chunks,
)
from src.graph.state import ProcurementState
from src.graph.tools import has_id_pattern


# ─────────────────── Conditional routing functions ────────────────────────────

def route_after_classifier(state: dict) -> str:
    qtype = state.get("query_type")
    if qtype == "general_chat":
        return "response_generator"
    return "retriever"


def route_after_validator(state: dict) -> str:
    if not state.get("is_relevant", False) and state.get("retrieval_attempt", 0) < MAX_RETRIEVAL_ATTEMPTS:
        return "retriever"

    qtype = state.get("query_type")
    query = state.get("query", "")
    if qtype == "workflow_guidance" or has_id_pattern(query):
        return "tool_caller"

    return "response_generator"


# ─────────────────── Graph construction ───────────────────────────────────────

def _build_graph():
    builder = StateGraph(ProcurementState)

    builder.add_node("classifier", classify_query)
    builder.add_node("retriever", retrieve_chunks)
    builder.add_node("validator", validate_chunks)
    builder.add_node("tool_caller", call_tools)
    builder.add_node("response_generator", generate)
    builder.add_node("memory", update_memory)

    builder.add_edge(START, "classifier")

    builder.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {
            "retriever": "retriever",
            "response_generator": "response_generator",
        },
    )

    builder.add_edge("retriever", "validator")

    builder.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "retriever": "retriever",
            "tool_caller": "tool_caller",
            "response_generator": "response_generator",
        },
    )

    builder.add_edge("tool_caller", "response_generator")
    builder.add_edge("response_generator", "memory")
    builder.add_edge("memory", END)

    return builder.compile()


compiled_graph = _build_graph().with_config(recursion_limit=GRAPH_RECURSION_LIMIT)


# ─────────────────── Convenience entry point ──────────────────────────────────

def run_graph(query: str, history: list[dict] | None = None,
              memory_summary: str = "", session_id: str = "default") -> dict:
    """Invoke the graph with a clean initial state."""
    initial_state: dict = {
        "query": query,
        "history": history or [],
        "memory_summary": memory_summary or "",
        "session_id": session_id,
        "retrieval_attempt": 0,
        "trace": [],
    }
    return compiled_graph.invoke(initial_state)


if __name__ == "__main__":
    # Smoke test — requires HF_TOKEN set and FAISS index built.
    import json

    result = run_graph("What is a Purchase Requisition?")
    print(json.dumps({
        "query_type": result.get("query_type"),
        "confidence": result.get("confidence"),
        "answer": (result.get("answer") or "")[:200],
        "sources": result.get("sources"),
        "trace": [
            {"node": t["node"], "status": t["status"],
             "ms": t["duration_ms"], "summary": t["summary"]}
            for t in result.get("trace", [])
        ],
    }, indent=2))
