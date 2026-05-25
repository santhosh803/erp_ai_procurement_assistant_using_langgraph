"""
app.py — Streamlit Chat Interface (LangGraph edition)

Premium Solarized-Light UI with enterprise-grade aesthetics.
Renders the chat UI plus a per-turn execution trace showing which graph nodes
ran, their timing, and their intermediate outputs. Holds rolling memory client-
side and ships it to the stateless FastAPI backend on every request.
"""

import uuid
import concurrent.futures
import time
from typing import Dict, List

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.api_client import ask_backend, BackendError
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

NODE_ICONS = {
    "classifier": "🏷️", "retriever": "🔍", "validator": "✅",
    "tool_caller": "🔧", "response_generator": "💬", "grader": "⚖️",
    "memory": "🧠",
}

STATUS_COLOR = {"ok": "#859900", "skipped": "#b58900", "error": "#dc322f"}

QTYPE_LABEL = {
    "factual_lookup": "📘 Factual Lookup",
    "workflow_guidance": "🛠️ Workflow Guidance",
    "general_chat": "💬 General Chat",
}


# ── Custom CSS — Solarized Light ──────────────────────────────────────────────
import os
css_path = os.path.join(os.path.dirname(__file__), "style.css")
with open(css_path, "r", encoding="utf-8") as f:
    st.markdown(f"<style>\n{f.read()}\n</style>", unsafe_allow_html=True)



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
def render_pipeline_strip(trace: List[dict]) -> str:
    by_node: Dict[str, dict] = {t["node"]: t for t in trace if "node" in t}
    pieces: List[str] = []
    for i, name in enumerate(NODE_ORDER):
        icon = NODE_ICONS.get(name, "⚙️")
        if name in by_node:
            ev = by_node[name]
            color = STATUS_COLOR.get(ev.get("status", "ok"), "#839496")
            tooltip = f'{ev.get("summary","")} ({ev.get("duration_ms",0):.0f} ms)'
            pieces.append(
                f'<span class="node-badge" style="background:{color}" title="{tooltip}">'
                f'<span class="badge-icon">{icon}</span> '
                f'{name} · {ev.get("duration_ms",0):.0f}ms</span>'
            )
        else:
            pieces.append(
                f'<span class="node-badge-inactive" title="not executed">'
                f'{icon} {name}</span>'
            )
        if i < len(NODE_ORDER) - 1:
            pieces.append('<span class="node-arrow">→</span>')
    return f'<div class="pipeline-strip">{"".join(pieces)}</div>'


def render_confidence_bar(confidence: float) -> str:
    pct = min(max(confidence * 100, 0), 100)
    if confidence >= 0.6:
        color = "#859900"  # green
    elif confidence >= 0.35:
        color = "#b58900"  # yellow
    else:
        color = "#dc322f"  # red
    return (
        f'<div class="conf-bar-wrap">'
        f'<div class="conf-bar-fill" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )


def render_trace(turn: dict) -> None:
    trace = turn.get("trace") or []
    qtype = turn.get("query_type", "")
    confidence = float(turn.get("confidence") or 0.0)
    tool_results = turn.get("tool_results") or []
    chunks = turn.get("chunks") or []

    retr_event = next((t for t in trace if t.get("node") == "retriever"), None)
    attempts = (retr_event or {}).get("payload", {}).get("attempt", 0)
    k = (retr_event or {}).get("payload", {}).get("k", 0)

    grader_event = next((t for t in trace if t.get("node") == "grader"), None)
    grader_grade = (grader_event or {}).get("payload", {}).get("grade", "—")

    total_ms = sum(t.get("duration_ms", 0) for t in trace)

    with st.expander("🔬 Graph Execution Trace", expanded=False):
        st.markdown(render_pipeline_strip(trace), unsafe_allow_html=True)

        # Metric cards
        retr_label = f"{attempts} pass{'es' if attempts != 1 else ''} · k={k}" if attempts else "Skipped"
        conf_bar = render_confidence_bar(confidence)
        st.markdown(f"""
        <div class="trace-metrics">
            <div class="trace-metric-card">
                <div class="label">Query Type</div>
                <div><span class="qtype-pill">{QTYPE_LABEL.get(qtype, qtype)}</span></div>
            </div>
            <div class="trace-metric-card">
                <div class="label">Confidence</div>
                <div class="value">{confidence:.2f}</div>
                {conf_bar}
            </div>
            <div class="trace-metric-card">
                <div class="label">Retrieval</div>
                <div class="value">{retr_label}</div>
            </div>
            <div class="trace-metric-card">
                <div class="label">Grader</div>
                <div class="value">{grader_grade}</div>
            </div>
            <div class="trace-metric-card">
                <div class="label">Total Latency</div>
                <div class="value">{total_ms:.0f} ms</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Per-node Detail**")
        for ev in trace:
            node = ev.get("node", "?")
            icon = NODE_ICONS.get(node, "⚙️")
            header = (
                f"{icon}  {node} — {ev.get('summary','')} "
                f"({ev.get('duration_ms',0):.1f} ms · {ev.get('status','ok')})"
            )
            with st.expander(header, expanded=False):
                payload = ev.get("payload", {}) or {}
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
                    dot_color = "#859900" if grade_val == "PASS" else "#dc322f"
                    st.markdown(
                        f'<span class="status-dot" style="background:{dot_color};"></span> '
                        f'**Decision:** `{grade_val}`',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**Reason:** {payload.get('reason', '—')}")
                    rq = payload.get("rewritten_query")
                    if rq:
                        st.markdown(f"**Rewritten Query:** `{rq}`")
                    if st.checkbox("Show Raw Grader Output", key=f"raw_grader_{id(turn)}"):
                        st.code(payload.get("raw_output", ""), language="text")
                else:
                    st.json(payload)

        if chunks:
            with st.expander("📄 Retrieved Chunks (full)", expanded=False):
                for i, c in enumerate(chunks, 1):
                    st.markdown(f"**Chunk {i}** — `{c.get('source', '?')}`")
                    st.code((c.get("content") or "")[:1200], language="text")

        if st.checkbox("Show raw JSON response", key=f"raw_{id(turn)}"):
            st.json(turn)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <span class="logo-icon">🏭</span>
        <h2>ERP Procurement AI</h2>
        <div class="sub">SAP S/4HANA Assistant</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown('<div class="sb-section-title">Powered By</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="sb-pill-row">
        <span class="sb-pill">🧠 Qwen2.5-7B</span>
        <span class="sb-pill">🕸️ LangGraph</span>
        <span class="sb-pill">🔍 FAISS + BM25</span>
        <span class="sb-pill">⚡ FastAPI</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section-title">Graph Architecture</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="sb-arch-flow">
        <span class="flow-node">classifier</span> <span class="flow-arrow">→</span>
        <span class="flow-node">retriever</span> <span class="flow-arrow">→</span>
        <span class="flow-node">validator</span> <span class="flow-arrow">→</span>
        <span class="flow-node">tool_caller</span><br>
        <span style="margin-left:2px;">↳</span>
        <span class="flow-node">response_generator</span> <span class="flow-arrow">→</span>
        <span class="flow-node">grader</span> <span class="flow-arrow">→</span>
        <span class="flow-node">memory</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="sb-section-title">Knowledge Domains</div>', unsafe_allow_html=True)
    st.markdown("""
    <ul class="sb-topic-list">
        <li><span class="dot"></span>Purchase Requisitions &amp; Orders</li>
        <li><span class="dot"></span>Goods Receipt &amp; Invoice Verification</li>
        <li><span class="dot"></span>Vendor &amp; Material Master Data</li>
        <li><span class="dot"></span>Procure-to-Pay Workflows</li>
        <li><span class="dot"></span>Pricing Conditions &amp; RFQ</li>
    </ul>
    """, unsafe_allow_html=True)

    st.markdown("---")

    with st.container():
        if st.button("🗑️  Clear Conversation", use_container_width=True, key="clear_chat"):
            st.session_state.chat_history = []
            st.session_state.history = []
            st.session_state.memory_summary = ""
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()

    st.markdown(
        '<div class="sb-footer">ERP AI Assistant v2.0 · LangGraph</div>',
        unsafe_allow_html=True,
    )


# ── Main Header ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏭 ERP AI Procurement Assistant</h1>
    <p class="tagline">
        LangGraph-powered agentic workflow over SAP S/4HANA Sourcing &amp; Procurement documentation
    </p>
</div>
<hr class="header-divider">
""", unsafe_allow_html=True)


# ── Quick Question Buttons ────────────────────────────────────────────────────
st.markdown('<p class="qq-label">Quick Questions</p>', unsafe_allow_html=True)
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

st.markdown("<hr class='header-divider'>", unsafe_allow_html=True)


# ── Chat History ──────────────────────────────────────────────────────────────
chat_area = st.container()
with chat_area:
    if not st.session_state.chat_history:
        st.markdown("""
        <div class="welcome-card">
            <span class="welcome-icon">👋</span>
            <h3>Welcome to ERP Procurement AI</h3>
            <p>Ask a question about SAP S/4HANA procurement processes,<br>
            or click one of the quick questions above to get started.</p>
        </div>
        """, unsafe_allow_html=True)

    for turn in st.session_state.chat_history:
        with st.container():
            # User message
            st.markdown(
                f'<div class="user-msg">'
                f'<div class="bubble">{turn["query"]}</div>'
                f'<div class="avatar">👤</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Assistant message
            source_tags = "".join(
                f'<span class="source-tag">📄 {s}</span>'
                for s in (turn.get("sources") or [])
            )
            source_row = (
                f'<div class="source-row">{source_tags}</div>'
                if source_tags else ""
            )
            st.markdown(
                f'<div class="asst-msg">'
                f'<div class="avatar">🤖</div>'
                f'<div class="bubble">{turn["answer"]}{source_row}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # Execution trace
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
    status_placeholder = st.empty()

    # Capture session state in local variables in the main thread
    # since st.session_state is thread-local and cannot be accessed from background threads
    history_val = list(st.session_state.history)
    memory_summary_val = str(st.session_state.memory_summary)
    session_id_val = str(st.session_state.session_id)

    def call_api(hist, mem_sum, sess_id):
        return ask_backend(query_to_process, hist, mem_sum, sess_id)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_api, history_val, memory_summary_val, session_id_val)

            messages = [
                "🏷️ Classifying query intent & context...",
                "🔍 Retrieving relevant SAP S/4HANA SOP documentation...",
                "✅ Validating query relevance & confidence...",
                "🔧 Running helper tools (ID extractors & step counters)...",
                "💬 Formulating response & grading answer quality...",
                "🧠 Updating conversation memory..."
            ]

            msg_idx = 0
            last_update = time.time()

            while not future.done():
                current_time = time.time()
                # Cycle message every 1.5 seconds
                if current_time - last_update > 1.5:
                    if msg_idx < len(messages) - 1:
                        msg_idx += 1
                    last_update = current_time

                status_placeholder.markdown(f"""
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">{messages[msg_idx]}</div>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(0.1)

            data = future.result().model_dump()

        status_placeholder.empty()

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

    except BackendError as e:
        status_placeholder.empty()
        st.error(
            "⚠️ Cannot reach the API server. "
            "Make sure FastAPI is running: `uvicorn api.main:app --reload --port 8000`"
        )
    except Exception as e:
        status_placeholder.empty()
        st.error(f"⚠️ Error: {str(e)}")
