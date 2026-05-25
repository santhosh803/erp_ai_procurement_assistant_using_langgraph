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
st.markdown("""
<style>
    /* ─── Google Fonts ─── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ─── Solarized Light Palette ───
       base3  #fdf6e3   base2  #eee8d5   base1  #93a1a1   base0  #839496
       base00 #657b83   base01 #586e75   base02 #073642   base03 #002b36
       yellow #b58900   orange #cb4b16   red    #dc322f   magenta #d33682
       violet #6c71c4   blue   #268bd2   cyan   #2aa198   green  #859900
    */

    /* ─── Animations ─── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(12px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to   { opacity: 1; }
    }
    @keyframes subtlePulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(38,139,210,0.15); }
        50%      { box-shadow: 0 0 0 6px rgba(38,139,210,0); }
    }
    @keyframes shimmer {
        0%   { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }

    /* ─── Global ─── */
    html, body, .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }
    .stApp {
        background: #fdf6e3 !important;
    }
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif !important;
        color: #073642 !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
    }
    p, li, span, div {
        color: #586e75 !important;
    }

    /* ─── Sidebar ─── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #eee8d5 0%, #fdf6e3 100%) !important;
        border-right: 1px solid #d6cdb0 !important;
    }
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"]::-webkit-scrollbar {
        display: none !important; width: 0 !important;
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
    [data-testid="stSidebarUserContent"] hr {
        border-color: #d6cdb0 !important; margin: 0.75em 0 !important;
    }

    /* ─── Sidebar Brand ─── */
    .sidebar-brand {
        text-align: center; padding: 1.25rem 0 0.5rem 0;
    }
    .sidebar-brand .logo-icon {
        font-size: 2.5rem; line-height: 1; display: block; margin-bottom: 0.2rem;
    }
    .sidebar-brand h2 {
        font-size: 1.2rem !important; margin: 0 !important; padding: 0 !important;
        color: #073642 !important; font-weight: 700 !important; letter-spacing: -0.02em;
    }
    .sidebar-brand .sub {
        font-size: 0.72rem; color: #93a1a1 !important; font-weight: 400;
        letter-spacing: 0.04em; text-transform: uppercase; margin-top: 2px;
    }

    /* ─── Sidebar Section ─── */
    .sb-section-title {
        font-size: 0.68rem !important; text-transform: uppercase;
        letter-spacing: 0.08em; color: #93a1a1 !important;
        font-weight: 600 !important; margin: 1rem 0 0.4rem 0; padding: 0;
    }
    .sb-pill-row {
        display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 0.5rem;
    }
    .sb-pill {
        background: #fdf6e3; border: 1px solid #d6cdb0; border-radius: 6px;
        padding: 3px 9px; font-size: 0.73rem; color: #586e75 !important;
        font-weight: 500; transition: all 0.2s ease;
    }
    .sb-pill:hover { background: #fff8e1; border-color: #b58900; }

    .sb-arch-flow {
        background: #fdf6e3; border: 1px solid #d6cdb0; border-radius: 10px;
        padding: 10px 12px; margin: 0.3rem 0 0.5rem 0;
        font-family: 'JetBrains Mono', monospace; font-size: 0.68rem;
        color: #657b83 !important; line-height: 1.7;
    }
    .sb-arch-flow .flow-node {
        background: #eee8d5; border-radius: 4px; padding: 1px 6px;
        border: 1px solid #d6cdb0; white-space: nowrap;
    }
    .sb-arch-flow .flow-arrow { color: #93a1a1; margin: 0 2px; }

    .sb-topic-list {
        list-style: none; padding: 0; margin: 0;
    }
    .sb-topic-list li {
        display: flex; align-items: center; gap: 6px;
        font-size: 0.82rem; color: #586e75 !important;
        padding: 3px 0; line-height: 1.5;
    }
    .sb-topic-list li .dot {
        width: 5px; height: 5px; border-radius: 50%; background: #268bd2;
        flex-shrink: 0;
    }

    .sb-footer {
        text-align: center; padding: 0.5rem 0;
        font-size: 0.7rem; color: #93a1a1 !important;
    }

    /* ─── Main Header ─── */
    .main-header {
        padding: 1.5rem 0 1rem 0;
        animation: fadeIn 0.6s ease-out;
    }
    .main-header h1 {
        font-size: 1.75rem !important; margin: 0 0 4px 0 !important;
        color: #073642 !important; font-weight: 700 !important;
    }
    .main-header .tagline {
        font-size: 0.88rem; color: #93a1a1 !important;
        font-weight: 400; margin: 0;
    }
    .header-divider {
        border: none; height: 1px; margin: 0.75rem 0 1rem 0;
        background: linear-gradient(90deg, #d6cdb0 0%, transparent 100%);
    }

    /* ─── Quick Question Cards ─── */
    .qq-label {
        font-size: 0.72rem !important; text-transform: uppercase;
        letter-spacing: 0.06em; color: #93a1a1 !important;
        font-weight: 600 !important; margin-bottom: 0.5rem;
    }
    .stButton > button {
        background: #eee8d5 !important; color: #586e75 !important;
        border: 1px solid #d6cdb0 !important; border-radius: 10px !important;
        font-weight: 500 !important; font-size: 0.82rem !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stButton > button:hover {
        background: #fff8e1 !important;
        border-color: #268bd2 !important; color: #268bd2 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(38,139,210,0.12) !important;
    }
    .stButton > button:active {
        transform: translateY(0px) !important;
    }

    /* ─── Chat Containers ─── */
    .chat-container { overflow: hidden; padding: 4px 0; }

    /* ─── User Bubble ─── */
    .user-msg {
        display: flex; justify-content: flex-end; gap: 10px;
        margin: 10px 0; animation: fadeInUp 0.35s ease-out;
    }
    .user-msg .bubble {
        background: linear-gradient(135deg, #268bd2, #1a6fa8);
        color: #fdf6e3 !important; padding: 14px 20px;
        border-radius: 20px 20px 4px 20px; max-width: 75%;
        font-size: 0.9rem; line-height: 1.55; font-weight: 400;
        box-shadow: 0 4px 16px rgba(38,139,210,0.18);
    }
    .user-msg .bubble * { color: #fdf6e3 !important; }
    .user-msg .avatar {
        width: 34px; height: 34px; border-radius: 50%;
        background: linear-gradient(135deg, #268bd2, #1a6fa8);
        display: flex; align-items: center; justify-content: center;
        font-size: 0.85rem; flex-shrink: 0; margin-top: 4px;
        box-shadow: 0 2px 8px rgba(38,139,210,0.2);
    }

    /* ─── Assistant Bubble ─── */
    .asst-msg {
        display: flex; gap: 10px; margin: 10px 0;
        animation: fadeInUp 0.35s ease-out;
    }
    .asst-msg .avatar {
        width: 34px; height: 34px; border-radius: 50%;
        background: linear-gradient(135deg, #eee8d5, #d6cdb0);
        display: flex; align-items: center; justify-content: center;
        font-size: 0.85rem; flex-shrink: 0; margin-top: 4px;
        border: 1px solid #d6cdb0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    .asst-msg .bubble {
        background: #fff; border: 1px solid #e8e0cc;
        padding: 16px 20px; border-radius: 20px 20px 20px 4px;
        max-width: 75%; font-size: 0.9rem; line-height: 1.6;
        color: #586e75 !important; font-weight: 400;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
    }
    .asst-msg .bubble * { color: #586e75 !important; }

    /* ─── Source Tags ─── */
    .source-row {
        display: flex; flex-wrap: wrap; gap: 5px; margin-top: 10px;
        padding-top: 10px; border-top: 1px solid #eee8d5;
    }
    .source-tag {
        background: #eee8d5; color: #657b83 !important;
        font-size: 0.68rem; padding: 2px 10px; border-radius: 20px;
        font-weight: 500; border: 1px solid #d6cdb0;
        font-family: 'JetBrains Mono', monospace;
        display: inline-flex; align-items: center; gap: 3px;
    }

    /* ─── Trace Pipeline Strip ─── */
    .pipeline-strip {
        clear: both; padding: 10px 0; display: flex;
        align-items: center; flex-wrap: wrap; gap: 2px;
    }
    .node-badge {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 4px 10px; border-radius: 6px;
        font-size: 0.7rem; font-family: 'JetBrains Mono', monospace;
        font-weight: 500; color: #fdf6e3 !important;
        transition: all 0.2s ease;
    }
    .node-badge:hover {
        transform: translateY(-1px);
        filter: brightness(1.1);
    }
    .node-badge .badge-icon { font-size: 0.72rem; }
    .node-badge-inactive {
        display: inline-flex; align-items: center; gap: 4px;
        padding: 4px 10px; border-radius: 6px;
        font-size: 0.7rem; font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
        background: #eee8d5 !important; color: #93a1a1 !important;
        border: 1px dashed #d6cdb0;
    }
    .node-arrow {
        color: #93a1a1 !important; font-size: 0.7rem; margin: 0 1px;
        font-family: 'JetBrains Mono', monospace;
    }

    /* ─── Trace Metric Cards ─── */
    .trace-metrics {
        display: flex; gap: 10px; margin: 8px 0 4px 0; flex-wrap: wrap;
    }
    .trace-metric-card {
        background: #fdf6e3; border: 1px solid #e8e0cc;
        border-radius: 10px; padding: 10px 16px;
        flex: 1; min-width: 140px;
    }
    .trace-metric-card .label {
        font-size: 0.65rem; text-transform: uppercase;
        letter-spacing: 0.06em; color: #93a1a1 !important;
        font-weight: 600; margin-bottom: 4px;
    }
    .trace-metric-card .value {
        font-size: 0.95rem; font-weight: 600; color: #073642 !important;
    }

    /* ─── Query-type Pill ─── */
    .qtype-pill {
        display: inline-flex; align-items: center; gap: 4px;
        background: #eee8d5; color: #268bd2 !important;
        padding: 5px 14px; border-radius: 20px;
        font-size: 0.78rem; font-weight: 600;
        border: 1px solid #d6cdb0;
    }

    /* ─── Confidence Bar ─── */
    .conf-bar-wrap {
        background: #eee8d5; border-radius: 20px; height: 8px;
        overflow: hidden; margin-top: 6px; border: 1px solid #d6cdb0;
    }
    .conf-bar-fill {
        height: 100%; border-radius: 20px;
        transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* ─── Expander overrides ─── */
    [data-testid="stExpander"] {
        border: 1px solid #e8e0cc !important;
        border-radius: 12px !important;
        background: #fff !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03) !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stExpander"] summary {
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important; font-size: 0.85rem !important;
        color: #586e75 !important;
    }
    [data-testid="stExpander"] summary:hover {
        color: #268bd2 !important;
    }

    /* ─── Streamlit bottom bar/footer override ─── */
    div[data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
        background-color: #fdf6e3 !important;
        background: #fdf6e3 !important;
    }

    /* ─── Chat Input — pill bar + circular send button ─── */
    @keyframes sendBtnGlow {
        0%, 100% { box-shadow: 0 2px 8px rgba(38,139,210,0.25); }
        50%      { box-shadow: 0 4px 18px rgba(38,139,210,0.45); }
    }

    [data-testid="stChatInput"] {
        border-top: none !important;
        padding: 0.5rem 0 !important;
        background: transparent !important;
    }
    /* The outer wrapper that holds textarea + button */
    [data-testid="stChatInput"] > div {
        background: #fdf6e3 !important;
        border: 1px solid #d6cdb0 !important;
        border-radius: 999px !important;
        padding: 4px 6px 4px 16px !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04) !important;
        transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
    }
    [data-testid="stChatInput"] > div:focus-within {
        border-color: #268bd2 !important;
        box-shadow: 0 2px 16px rgba(38,139,210,0.12) !important;
    }
    /* Textarea itself — transparent, flush with the pill */
    [data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: #586e75 !important;
        border: none !important;
        border-radius: 0 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        padding: 8px 4px !important;
        resize: none !important;
        box-shadow: none !important;
        outline: none !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #93a1a1 !important; opacity: 1 !important;
        font-weight: 400 !important;
    }
    [data-testid="stChatInput"] textarea:focus {
        box-shadow: none !important;
        border: none !important;
    }
    /* Circular send button */
    [data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #2aa198, #268bd2) !important;
        color: #fdf6e3 !important;
        border: none !important;
        border-radius: 50% !important;
        width: 38px !important; height: 38px !important;
        min-width: 38px !important; min-height: 38px !important;
        max-width: 38px !important; max-height: 38px !important;
        padding: 0 !important;
        display: flex !important; align-items: center !important;
        justify-content: center !important;
        flex-shrink: 0 !important;
        cursor: pointer !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(38,139,210,0.25) !important;
    }
    [data-testid="stChatInput"] button:hover {
        transform: scale(1.08) !important;
        animation: sendBtnGlow 1.5s ease-in-out infinite !important;
    }
    [data-testid="stChatInput"] button:active {
        transform: scale(0.96) !important;
    }
    /* Hide the default arrow inside circle SVG icon */
    [data-testid="stChatInput"] button svg {
        display: none !important;
    }
    /* Render a clean, standalone up arrow */
    [data-testid="stChatInput"] button::after {
        content: "↑" !important;
        font-size: 20px !important;
        color: #fdf6e3 !important;
        font-weight: 600 !important;
        line-height: 1 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* ─── Welcome Card ─── */
    .welcome-card {
        text-align: center; padding: 3rem 2rem;
        background: #fff; border: 1px solid #e8e0cc;
        border-radius: 16px; margin: 1rem 0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.03);
        animation: fadeIn 0.6s ease-out;
    }
    .welcome-card .welcome-icon {
        font-size: 2.5rem; margin-bottom: 0.5rem; display: block;
    }
    .welcome-card h3 {
        font-size: 1.15rem !important; color: #073642 !important;
        margin: 0 0 6px 0 !important; font-weight: 600 !important;
    }
    .welcome-card p {
        font-size: 0.88rem; color: #93a1a1 !important;
        margin: 0; line-height: 1.5;
    }

    /* ─── Clear Chat Button ─── */
    .clear-btn > button {
        background: #fff !important; color: #dc322f !important;
        border: 1px solid #e8e0cc !important; border-radius: 10px !important;
        font-weight: 500 !important; font-size: 0.8rem !important;
    }
    .clear-btn > button:hover {
        background: #fdf2f2 !important;
        border-color: #dc322f !important;
        transform: translateY(-1px) !important;
    }

    /* ─── Streamlit progress bar override ─── */
    [data-testid="stProgress"] > div > div > div {
        background: #268bd2 !important;
    }

    /* ─── Table overrides ─── */
    [data-testid="stTable"] table {
        font-family: 'Inter', sans-serif !important;
        font-size: 0.82rem !important;
    }

    /* ─── Code block overrides ─── */
    [data-testid="stCode"] code {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.78rem !important;
        background: #eee8d5 !important;
    }

    /* ─── Spinner override ─── */
    .stSpinner > div {
        border-top-color: #268bd2 !important;
    }

    /* ─── Status indicators ─── */
    .status-dot {
        width: 7px; height: 7px; border-radius: 50%;
        display: inline-block; margin-right: 5px;
        animation: subtlePulse 2s infinite;
    }

    /* ─── Custom Sequential Loading Card ─── */
    .loading-container {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 1rem 1.25rem;
        background: #fff;
        border: 1px solid #e8e0cc;
        border-radius: 12px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
        animation: fadeIn 0.3s ease-out;
    }
    .loading-spinner {
        width: 18px;
        height: 18px;
        border: 2px solid #eee8d5;
        border-top: 2px solid #268bd2;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .loading-text {
        font-size: 0.88rem;
        color: #586e75 !important;
        font-weight: 500;
        font-family: 'Inter', sans-serif !important;
    }

    /* ─── Responsive ─── */
    @media (max-width: 768px) {
        .user-msg .bubble, .asst-msg .bubble { max-width: 92%; }
        .main-header h1 { font-size: 1.3rem !important; }
        .trace-metrics { flex-direction: column; }
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

    def call_api():
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
        return response.json()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(call_api)

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

            data = future.result()

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

    except requests.exceptions.ConnectionError:
        status_placeholder.empty()
        st.error(
            "⚠️ Cannot reach the API server. "
            "Make sure FastAPI is running: `uvicorn api.main:app --reload --port 8000`"
        )
    except Exception as e:
        status_placeholder.empty()
        st.error(f"⚠️ Error: {str(e)}")
