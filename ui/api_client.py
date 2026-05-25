"""
API Client for the ERP AI Procurement Assistant backend.
Handles the HTTP communication with the LangGraph FastAPI backend.
"""

import sys
import os
import requests
from pydantic import BaseModel, Field

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.config import API_URL

class HistoryTurn(BaseModel):
    role: str
    content: str

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

class AskRequest(BaseModel):
    query: str
    history: list[HistoryTurn] = Field(default_factory=list)
    memory_summary: str = ""
    session_id: str = "default"

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

class BackendError(Exception):
    pass

def ask_backend(query: str, history: list[dict], memory_summary: str, session_id: str) -> AskResponse:
    """
    Sends the user query to the FastAPI backend and returns the typed response.
    """
    req_data = AskRequest(
        query=query,
        history=[HistoryTurn(**t) for t in history],
        memory_summary=memory_summary,
        session_id=session_id
    )
    
    try:
        resp = requests.post(API_URL, json=req_data.model_dump())
        resp.raise_for_status()
        return AskResponse(**resp.json())
    except requests.exceptions.RequestException as e:
        raise BackendError(f"Failed to connect to backend: {e}")
