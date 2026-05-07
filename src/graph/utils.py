"""Tracing helpers shared by every node."""

import time
from functools import wraps
from typing import Callable


def trace_event(node: str, *, status: str = "ok", duration_ms: float = 0.0,
                summary: str = "", payload: dict | None = None) -> dict:
    """Build a single TraceEvent dict matching the state schema."""
    return {
        "node": node,
        "status": status,
        "duration_ms": round(duration_ms, 2),
        "summary": summary,
        "payload": payload or {},
    }


def traced(node_name: str) -> Callable:
    """
    Decorator: time a node, swallow exceptions into a trace event, and
    guarantee the node always returns a dict containing a `trace` list.

    The wrapped function should return a partial state dict WITHOUT a `trace`
    field — this decorator injects the timing/status event automatically. If
    the wrapped function returns its own `trace` list, those events are kept
    and the timing event is appended.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(state, *args, **kwargs):
            t0 = time.perf_counter()
            try:
                result = fn(state, *args, **kwargs) or {}
                dt_ms = (time.perf_counter() - t0) * 1000
                summary = result.pop("_summary", "")
                payload = result.pop("_payload", {})
                event = trace_event(
                    node_name,
                    status="ok",
                    duration_ms=dt_ms,
                    summary=summary,
                    payload=payload,
                )
                existing = result.get("trace", [])
                result["trace"] = existing + [event]
                return result
            except Exception as e:
                dt_ms = (time.perf_counter() - t0) * 1000
                event = trace_event(
                    node_name,
                    status="error",
                    duration_ms=dt_ms,
                    summary=f"{type(e).__name__}: {e}",
                    payload={"error": str(e)},
                )
                return {"trace": [event], "error": f"{node_name}: {e}"}
        return wrapper
    return decorator
