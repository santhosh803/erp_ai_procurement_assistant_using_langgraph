"""grade_answer — LLM-as-a-Judge reflection and query rewriting."""

import re

from src.graph.config import GRADER_TEMPLATE, MAX_RETRIEVAL_ATTEMPTS
from src.graph.utils import traced
from src.llm_handler import generate_response


def parse_grader_output(llm_output: str, original_query: str) -> tuple[str, str, str]:
    """
    Parse the structured output from the LLM grader.
    Expected format:
      GRADE: PASS or FAIL
      REASON: <brief explanation>
      REWRITTEN_QUERY: <optimized search query>
    """
    grade = "PASS"
    reason = "No reason provided."
    rewritten_query = original_query

    lines = (llm_output or "").split("\n")
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue

        if re.match(r"^grade\s*:", line_strip, re.IGNORECASE):
            val = re.sub(r"^grade\s*:", "", line_strip, flags=re.IGNORECASE).strip().upper()
            if "FAIL" in val:
                grade = "FAIL"
            elif "PASS" in val:
                grade = "PASS"
        elif re.match(r"^reason\s*:", line_strip, re.IGNORECASE):
            reason = re.sub(r"^reason\s*:", "", line_strip, flags=re.IGNORECASE).strip()
        elif re.match(r"^rewritten_query\s*:", line_strip, re.IGNORECASE):
            rewritten_query = re.sub(r"^rewritten_query\s*:", "", line_strip, flags=re.IGNORECASE).strip()

    # Fallback to original query if rewritten query is empty
    if not rewritten_query:
        rewritten_query = original_query

    return grade, reason, rewritten_query


@traced("grader")
def grade_answer(state: dict) -> dict:
    query = state.get("query", "")
    original_query = state.get("original_query", query)
    answer = state.get("answer", "")
    chunks = state.get("chunks", []) or []
    qtype = state.get("query_type")
    attempt = state.get("retrieval_attempt", 0)

    # Skip grading for general chat
    if qtype == "general_chat":
        return {
            "grader_decision": "pass",
            "grader_reason": "Skipped grading for general chat.",
            "_summary": "skipped (general chat)",
            "_payload": {
                "decision": "pass",
                "reason": "Skipped grading for general chat."
            }
        }

    # Format the retrieved chunks for the grader
    context_parts = []
    for idx, c in enumerate(chunks, 1):
        context_parts.append(f"--- Chunk {idx} [{c.get('source', 'unknown')}] ---\n{c.get('content', '')}")
    context_str = "\n\n".join(context_parts) if context_parts else "No context retrieved."

    # Call LLM grader
    prompt = GRADER_TEMPLATE.format(context=context_str, query=query, answer=answer)
    llm_output = generate_response(prompt)

    # Parse evaluation results
    grade, reason, rewritten_query = parse_grader_output(llm_output, query)

    state_update = {
        "grader_decision": grade.lower(),
        "grader_reason": reason,
        "_summary": f"grade={grade} (attempt {attempt})",
        "_payload": {
            "grade": grade,
            "reason": reason,
            "rewritten_query": rewritten_query if grade == "FAIL" else None,
            "raw_output": llm_output,
        }
    }

    # If the grader fails and we have retry attempts remaining, rewrite the query in the state
    if grade == "FAIL" and attempt < MAX_RETRIEVAL_ATTEMPTS:
        state_update["query"] = rewritten_query

    return state_update
