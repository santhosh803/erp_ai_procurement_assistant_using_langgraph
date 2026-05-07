"""generate — composes the final prompt and calls Qwen for the answer."""

from src.graph.utils import traced
from src.llm_handler import generate_response
from src.prompt_builder import SYSTEM_INSTRUCTION, build_prompt

CHAT_INSTRUCTION = (
    "You are a friendly assistant for a SAP S/4HANA procurement chatbot. "
    "Briefly greet the user or answer meta questions about your purpose. "
    "Encourage them to ask procurement questions like 'What is a Purchase Requisition?'."
)


def _compose_prompt(state: dict) -> str:
    query = state.get("query", "")
    chunks = state.get("chunks", []) or []
    tool_results = state.get("tool_results", []) or []
    memory_summary = (state.get("memory_summary") or "").strip()
    qtype = state.get("query_type")

    # Chat-only branch: skip retrieved context entirely.
    if qtype == "general_chat" and not chunks:
        memory_block = (
            f"\n\n--- CONVERSATION SUMMARY ---\n{memory_summary}"
            if memory_summary else ""
        )
        return f"{CHAT_INSTRUCTION}{memory_block}\n\nUser: {query}\nAssistant:"

    base = build_prompt(query, chunks)

    extras = []
    if tool_results:
        lines = ["--- TOOL RESULTS ---"]
        for r in tool_results:
            lines.append(f"[{r.get('tool_name')}] {r.get('output')}")
        extras.append("\n".join(lines))

    if memory_summary:
        extras.append(f"--- CONVERSATION SUMMARY ---\n{memory_summary}")

    if not extras:
        return base

    # Inject extras BEFORE the final "User Question:" line so the LLM treats
    # them as part of the grounding context.
    marker = "User Question:"
    if marker in base:
        head, tail = base.split(marker, 1)
        return f"{head}{chr(10).join(extras)}\n\n{marker}{tail}"
    return base + "\n\n" + "\n\n".join(extras)


@traced("response_generator")
def generate(state: dict) -> dict:
    prompt = _compose_prompt(state)
    answer = generate_response(prompt)
    chunks = state.get("chunks", []) or []
    sources = sorted({c.get("source", "unknown") for c in chunks if c.get("source")})

    return {
        "prompt": prompt,
        "answer": answer,
        "sources": sources,
        "_summary": f"{len(answer)} chars, {len(sources)} sources",
        "_payload": {
            "prompt_preview": prompt[:500],
            "answer_preview": (answer or "")[:200],
            "sources": sources,
        },
    }


# Re-export so tests can poke at it directly
__all__ = ["generate", "_compose_prompt", "SYSTEM_INSTRUCTION"]
