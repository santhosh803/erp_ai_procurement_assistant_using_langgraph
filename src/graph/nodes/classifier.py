"""query_classifier — uses Qwen to label the query as FACTUAL / WORKFLOW / CHAT."""

from src.graph.config import CLASSIFIER_TEMPLATE
from src.graph.utils import traced
from src.llm_handler import classify

LABEL_MAP = {
    "FACTUAL": "factual_lookup",
    "WORKFLOW": "workflow_guidance",
    "CHAT": "general_chat",
}


def _parse_label(raw: str) -> str:
    """Pull the first known label out of the raw LLM output."""
    if not raw:
        return "factual_lookup"
    upper = raw.upper()
    for label, qtype in LABEL_MAP.items():
        if label in upper:
            return qtype
    return "factual_lookup"  # safe default — triggers retrieval


@traced("classifier")
def classify_query(state: dict) -> dict:
    query = state.get("query", "").strip()
    summary = state.get("memory_summary", "")
    if not query:
        return {
            "query_type": "general_chat",
            "classifier_raw": "",
            "_summary": "empty query → chat",
            "_payload": {"raw": ""},
        }

    prompt = CLASSIFIER_TEMPLATE.format(query=query, summary=summary or "(none)")
    raw = classify(prompt)
    qtype = _parse_label(raw)
    return {
        "query_type": qtype,
        "classifier_raw": raw,
        "_summary": qtype,
        "_payload": {"raw": raw, "prompt_preview": prompt[:200]},
    }
