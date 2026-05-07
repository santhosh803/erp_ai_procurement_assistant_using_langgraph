"""call_tools — runs lightweight regex/heuristic tools when the query warrants it."""

from src.graph.tools import has_id_pattern, has_step_intent, id_extractor, step_counter
from src.graph.utils import traced


@traced("tool_caller")
def call_tools(state: dict) -> dict:
    query = state.get("query", "")
    qtype = state.get("query_type")
    chunks = state.get("chunks", [])

    results: list[dict] = []

    if has_id_pattern(query):
        results.append(id_extractor(query))

    if qtype == "workflow_guidance" and has_step_intent(query):
        results.append(step_counter(chunks))

    summary = (
        ", ".join(r["tool_name"] for r in results) if results else "no tools matched"
    )
    return {
        "tool_results": results,
        "_summary": summary,
        "_payload": {"results": results},
    }
