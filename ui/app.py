"""
app.py — Streamlit Chat Interface (LangGraph edition)

Renders the chat UI plus a per-turn execution trace showing which graph nodes
ran, their timing, and their intermediate outputs. Holds rolling memory client-
side and ships it to the stateless FastAPI backend on every request.
"""

import uuid

import requests
import streamlit as st

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ERP AI Procurement Assistant",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Config ────────────────────────────────────────────────────────────────────
API_URL = "http://localhost:8000/ask"

NODE_ORDER = ["classifier", "retriever", "validator", "tool_caller",
              "response_generator", "grader", "memory"]

STATUS_COLOR = {"ok": "#16a34a", "skipped": "#d97706", "error": "#dc2626"}

QTYPE_LABEL = {
    "factual_lookup": "📘 Factual lookup",
    "workflow_guidance": "🛠️ Workflow guidance",
    "general_chat": "💬 General chat",
}


# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        border-right: 1px solid #334155;
    }
    .user-bubble {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white; padding: 12px 18px; border-radius: 18px 18px 4px 18px;
        margin: 8px 0; display: inline-block; max-width: 85%;
        float: right; clear: both; font-size: 0.95rem;
        box-shadow: 0 4px 15px rgba(37,99,235,0.3);
    }
    .assistant-bubble {
        background: linear-gradient(135deg, #1e3a5f, #1e293b);
        color: #e2e8f0; padding: 14px 18px; border-radius: 18px 18px 18px 4px;
        margin: 8px 0; display: inline-block; max-width: 85%;
        float: left; clear: both; font-size: 0.95rem;
        border: 1px solid #334155; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .source-tag {
        background: #0f4c81; color: #93c5fd; font-size: 0.72rem;
        padding: 2px 8px; border-radius: 10px; margin: 2px; display: inline-block;
    }
    .chat-container { overflow: hidden; padding: 8px 0; }

    /* Trace pipeline strip */
    .pipeline-strip {
        clear: both; padding: 6px 0 4px 0; line-height: 2.0;
    }
    .node-badge {
        color: #fff; padding: 3px 10px; border-radius: 10px;
        margin: 2px 4px 2px 0; font-size: 0.72rem; font-family: monospace;
        display: inline-block;
    }
    .node-arrow { color: #475569; font-size: 0.85rem; margin: 0 2px; }
    .qtype-pill {
        background: #1e293b; color: #93c5fd; padding: 4px 12px;
        border-radius: 12px; font-size: 0.8rem; border: 1px solid #334155;
    }

    .stTextInput > div > div > input {
        background: #1e293b !important; color: #f1f5f9 !important;
        border: 1px solid #334155 !important; border-radius: 12px !important;
    }
    .stButton > button, .stFormSubmitButton > button {
        background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
        color: white !important; border: none !important;
        border-radius: 10px !important; font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important; transition: all 0.2s ease !important;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(37,99,235,0.5) !important;
    }
    h1, h2, h3 { color: #f1f5f9 !important; }
    p, li { color: #cbd5e1 !important; }

    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"]::-webkit-scrollbar {
        display: none !important; width: 0 !important; height: 0 !important;
    }
    [data-testid="stSidebar"], [data-testid="stSidebarUserContent"] {
        scrollbar-width: none !important; -ms-overflow-style: none !important;
    }
    [data-testid="stSidebarUserContent"] > div { height: 100%; }
    [data-testid="stSidebar"] div.stVerticalBlock {
        display: flex; flex-direction: column; height: 100%;
    }
    [data-testid="stSidebar"] div.stVerticalBlock > div:nth-last-child(2) {
        margin-top: auto !important;
    }
    [data-testid="stSidebarUserContent"] hr { margin: 0.5em 0 !important; }
    [data-testid="stSidebarUserContent"] h2 {
        margin-bottom: 0px !important; padding-bottom: 0px !important;
    }
    [data-testid="stSidebarUserContent"] p, [data-testid="stSidebarUserContent"] ul {
        margin-bottom: 0px !important;
    }
    .fixed-header {
        position: sticky; top: 2.875rem; background: #0f172a; z-index: 999;
        padding-top: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #334155;
        margin-top: -3rem; margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State ─────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []        # list of full response dicts
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "memory_summary" not in st.session_state:
    st.session_state.memory_summary = ""
if "history" not in st.session_state:
    st.session_state.history = []             # [{role, content}] for the API
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


# ── Helpers ───────────────────────────────────────────────────────────────────
def render_pipeline_strip(trace: list[dict]) -> str:
    by_node: dict[str, dict] = {t["node"]: t for t in trace if "node" in t}
    pieces: list[str] = []
    for i, name in enumerate(NODE_ORDER):
        if name in by_node:
            ev = by_node[name]
            color = STATUS_COLOR.get(ev.get("status", "ok"), "#64748b")
            tooltip = f'{ev.get("summary","")} ({ev.get("duration_ms",0):.0f} ms)'
            pieces.append(
                f'<span class="node-badge" style="background:{color}" title="{tooltip}">'
                f'{name} · {ev.get("duration_ms",0):.0f}ms</span>'
            )
        else:
            pieces.append(
                f'<span class="node-badge" style="background:#334155;color:#94a3b8" '
                f'title="not executed">{name}</span>'
            )
        if i < len(NODE_ORDER) - 1:
            pieces.append('<span class="node-arrow">▶</span>')
    return f'<div class="pipeline-strip">{"".join(pieces)}</div>'


def render_trace(turn: dict) -> None:
    trace = turn.get("trace") or []
    qtype = turn.get("query_type", "")
    confidence = float(turn.get("confidence") or 0.0)
    tool_results = turn.get("tool_results") or []
    chunks = turn.get("chunks") or []

    retr_event = next((t for t in trace if t.get("node") == "retriever"), None)
    attempts = (retr_event or {}).get("payload", {}).get("attempt", 0)
    k = (retr_event or {}).get("payload", {}).get("k", 0)

    with st.expander("🔬 Graph Execution Trace", expanded=False):
        st.markdown(render_pipeline_strip(trace), unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        c1.markdown(f'<span class="qtype-pill">{QTYPE_LABEL.get(qtype, qtype)}</span>',
                    unsafe_allow_html=True)
        c2.progress(min(max(confidence, 0.0), 1.0),
                    text=f"Confidence: {confidence:.2f}")
        retr_label = f"{attempts} attempt(s) @ k={k}" if attempts else "skipped"
        c3.markdown(f"**Retrieval:** {retr_label}")

        st.markdown("---")
        st.markdown("**Per-node detail**")
        for ev in trace:
            header = (
                f"{ev.get('node','?')} — {ev.get('summary','')} "
                f"({ev.get('duration_ms',0):.1f} ms · {ev.get('status','ok')})"
            )
            with st.expander(header, expanded=False):
                payload = ev.get("payload", {}) or {}
                node = ev.get("node")
                if node == "retriever":
                    previews = payload.get("chunk_previews", [])
                    if previews:
                        st.table(previews)
                    else:
                        st.json(payload)
                elif node == "tool_caller":
                    if tool_results:
                        st.table([
                            {
                                "tool": r.get("tool_name", ""),
                                "input": str(r.get("input", "")),
                                "output": str(r.get("output", "")),
                            }
                            for r in tool_results
                        ])
                    else:
                        st.caption("No tools matched.")
                elif node == "response_generator":
                    st.markdown("**Prompt (preview):**")
                    st.code(payload.get("prompt_preview", ""), language="text")
                    st.markdown("**Sources:** " + ", ".join(payload.get("sources", []) or []))
                elif node == "grader":
                    grade_val = payload.get("grade", "PASS").upper()
                    st.markdown(f"**Decision:** `{grade_val}`")
                    st.markdown(f"**Reason:** {payload.get('reason')}")
                    if payload.get("rewritten_query"):
                        st.markdown(f"**Rewritten Query:** `{payload.get('rewritten_query')}`")
                    if st.checkbox("Show Raw Grader Output", key=f"raw_grader_{id(turn)}"):
                        st.code(payload.get("raw_output", ""), language="text")
                else:
                    st.json(payload)

        if chunks:
            with st.expander("📄 Retrieved chunks (full)", expanded=False):
                for i, c in enumerate(chunks, 1):
                    st.markdown(
                        f"**Chunk {i} — `{c.get('source','?')}`**"
                    )
                    st.code((c.get("content") or "")[:1200], language="text")

        if st.checkbox("Show raw response", key=f"raw_{id(turn)}"):
            st.json(turn)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div style="padding-top: 0.5rem;">
    <h2>🏭 ERP Procurement AI</h2>
    <hr style="margin: 0.75em 0;">
    <b style="font-size: 1.05rem;">Powered by:</b>
    <ul style="margin: 0.5em 0 1.5em 0; padding-left: 1.5em; line-height: 1.8;">
        <li>🧠 Qwen2.5-7B (via HuggingFace)</li>
        <li>🕸️ LangGraph StateGraph</li>
        <li>🔍 FAISS Vector Search</li>
        <li>📚 SAP S/4HANA Knowledge Base</li>
    </ul>
    <b style="font-size: 1.05rem;">Graph nodes:</b>
    <ul style="margin: 0.5em 0 1.5em 0; padding-left: 1.5em; line-height: 1.7; font-size: 0.85rem;">
        <li>classifier → retriever</li>
        <li>validator → tool_caller</li>
        <li>response_generator → memory</li>
    </ul>
    <b style="font-size: 1.05rem;">Ask me about:</b>
    <ul style="margin: 0.5em 0 1.5em 0; padding-left: 1.5em; line-height: 1.8;">
        <li>Purchase Requisition (PR)</li>
        <li>Purchase Order (PO)</li>
        <li>Goods Receipt (GR)</li>
        <li>Invoice Verification</li>
        <li>Vendor/Material Master</li>
        <li>P2P Workflow</li>
    </ul>
</div>
""", unsafe_allow_html=True)

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.history = []
        st.session_state.memory_summary = ""
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.markdown(
        "<hr style='margin: 0.5em 0;'>"
        "<div style='text-align: center;'><small style='color: #64748b;'>"
        "ERP AI Assistant v2.0 · LangGraph</small></div>",
        unsafe_allow_html=True,
    )


# ── Main Header (Sticky) ──────────────────────────────────────────────────────
st.markdown("""
<div class="fixed-header">
    <h1 style="margin-bottom: 0px;">🏭 ERP AI Procurement Assistant</h1>
    <p style="color: #cbd5e1; font-style: italic; margin-top: 5px;">
        LangGraph-powered agentic workflow over SAP S/4HANA Sourcing & Procurement docs
    </p>
</div>
""", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)


# ── Quick Question Buttons ────────────────────────────────────────────────────
st.markdown("**Quick Questions:**")
quick_cols = st.columns(3)
quick_questions = [
    "What is a Purchase Requisition?",
    "Explain the PR to PO process",
    "What is invoice verification?",
    "How many steps are in the P2P workflow?",
    "Tell me about PO 4500001234",
    "How are vendors managed in SAP?",
]
for i, qcol in enumerate(quick_cols):
    for j in range(2):
        idx = i * 2 + j
        if idx < len(quick_questions):
            if qcol.button(quick_questions[idx], key=f"quick_{idx}"):
                st.session_state.pending_query = quick_questions[idx]

st.markdown("---")


# ── Chat History ──────────────────────────────────────────────────────────────
chat_area = st.container()
with chat_area:
    if not st.session_state.chat_history:
        st.markdown(
            "<div style='text-align:center; color:#475569; padding: 40px;'>"
            "👋 Welcome! Ask a procurement question below to get started."
            "</div>",
            unsafe_allow_html=True,
        )

    for turn in st.session_state.chat_history:
        with st.container():
            st.markdown(
                f'<div class="chat-container">'
                f'<div class="user-bubble">🧑 {turn["query"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            source_tags = "".join(
                f'<span class="source-tag">📄 {s}</span>'
                for s in (turn.get("sources") or [])
            )
            st.markdown(
                f'<div class="chat-container">'
                f'<div class="assistant-bubble">🤖 {turn["answer"]}'
                f'<br><br><small>{source_tags}</small>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

            render_trace(turn)


# ── Input Area ────────────────────────────────────────────────────────────────
user_query = st.chat_input("e.g. What is the difference between PR and PO?")

query_to_process = None
if user_query:
    query_to_process = user_query.strip()
elif st.session_state.pending_query:
    query_to_process = st.session_state.pending_query
    st.session_state.pending_query = None

if query_to_process:
    with st.spinner("Running graph: classify → retrieve → validate → generate…"):
        try:
            response = requests.post(
                API_URL,
                json={
                    "query": query_to_process,
                    "history": st.session_state.history,
                    "memory_summary": st.session_state.memory_summary,
                    "session_id": st.session_state.session_id,
                },
                timeout=180,
            )
            response.raise_for_status()
            data = response.json()

            st.session_state.chat_history.append({
                "query": query_to_process,
                "answer": data.get("answer", "No answer returned."),
                "sources": data.get("sources", []),
                "chunks": data.get("chunks", []),
                "trace": data.get("trace", []),
                "query_type": data.get("query_type", ""),
                "confidence": data.get("confidence", 0.0),
                "tool_results": data.get("tool_results", []),
            })
            st.session_state.memory_summary = data.get("memory_summary", "") or ""
            st.session_state.history = data.get("history", []) or []
            st.rerun()

        except requests.exceptions.ConnectionError:
            st.error(
                "⚠️ Cannot reach the API server. "
                "Make sure FastAPI is running: `uvicorn api.main:app --reload --port 8000`"
            )
        except Exception as e:
            st.error(f"⚠️ Error: {str(e)}")
