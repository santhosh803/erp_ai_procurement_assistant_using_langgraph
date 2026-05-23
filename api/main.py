"""
main.py — FastAPI Backend
Exposes POST /ask, backed by the LangGraph procurement workflow.

The endpoint stays stateless: the client sends the rolling memory_summary
and history with each request, and the response carries the updated values
back so the client can persist them.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.graph import compiled_graph

# ── App Setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="ERP AI Procurement Assistant",
    description="LangGraph-powered agentic RAG assistant for SAP S/4HANA procurement.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────
class HistoryTurn(BaseModel):
    role: str          # "user" | "assistant"
    content: str


class AskRequest(BaseModel):
    query: str
    history: list[HistoryTurn] = Field(default_factory=list)
    memory_summary: str = ""
    session_id: str = "default"


class ChunkDetail(BaseModel):
    content: str
    source: str


class TraceEventModel(BaseModel):
    node: str
    status: str
    duration_ms: float
    summary: str = ""
    payload: dict = Field(default_factory=dict)


class ToolResultModel(BaseModel):
    tool_name: str
    input: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)


class AskResponse(BaseModel):
    query: str
    answer: str
    sources: list[str]
    chunks: list[ChunkDetail]
    query_type: str
    confidence: float
    trace: list[TraceEventModel]
    tool_results: list[ToolResultModel]
    memory_summary: str
    history: list[HistoryTurn]


# ── Endpoints ─────────────────────────────────────────────────────────────────
@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "message": "ERP AI Procurement Assistant (LangGraph) is running."}


@app.post("/ask", response_model=AskResponse, summary="Ask a procurement question")
def ask(request: AskRequest):
    """
    Submit a procurement-related question. The graph classifies, retrieves,
    validates, optionally calls tools, generates an answer, and updates memory.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    history_in = [t.model_dump() for t in request.history]

    initial_state: dict = {
        "query": request.query,
        "original_query": request.query,
        "history": history_in,
        "memory_summary": request.memory_summary,
        "session_id": request.session_id,
        "retrieval_attempt": 0,
        "trace": [],
    }

    result = compiled_graph.invoke(initial_state)

    chunks = result.get("chunks", []) or []
    history_out = history_in + [
        {"role": "user", "content": request.query},
        {"role": "assistant", "content": result.get("answer", "")},
    ]

    return AskResponse(
        query=request.query,
        answer=result.get("answer", ""),
        sources=result.get("sources", []) or [],
        chunks=[
            ChunkDetail(content=c.get("content", ""), source=c.get("source", "unknown"))
            for c in chunks
        ],
        query_type=result.get("query_type", "factual_lookup"),
        confidence=float(result.get("confidence") or 0.0),
        trace=[TraceEventModel(**t) for t in (result.get("trace") or [])],
        tool_results=[ToolResultModel(**r) for r in (result.get("tool_results") or [])],
        memory_summary=result.get("memory_summary", "") or "",
        history=[HistoryTurn(**t) for t in history_out],
    )
