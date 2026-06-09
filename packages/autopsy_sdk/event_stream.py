"""
autopsy_sdk.event_stream
~~~~~~~~~~~~~~~~~~~~~~~~
In-memory ordered event bus. The causal engine reads from here
for real-time analysis. Thread-safe for concurrent agent execution.
"""

from __future__ import annotations

import threading
from .models import TraceEvent, DownstreamEffect

# ── Internal storage ─────────────────────────────────────────

_stream: list[TraceEvent] = []
_lock = threading.Lock()


def push(event: TraceEvent) -> None:
    """Append a new trace event to the in-memory stream."""
    with _lock:
        _stream.append(event)


def all_events() -> list[TraceEvent]:
    """Return all events sorted by timestamp."""
    with _lock:
        return sorted(list(_stream), key=lambda e: e.timestamp)


def events_for(agent_id: str) -> list[TraceEvent]:
    """Return all events for a specific agent."""
    with _lock:
        return [e for e in _stream if e.agent_id == agent_id]


def event_count() -> int:
    """Return total number of events in the stream."""
    with _lock:
        return len(_stream)


def clear() -> None:
    """Clear all events (useful between simulation runs)."""
    with _lock:
        _stream.clear()


def append_downstream_effect(agent_id: str, round_num: int, effect: DownstreamEffect) -> None:
    """Attach a downstream effect to the in-memory event stream."""
    with _lock:
        # Find the latest event for this agent in this round
        for event in reversed(_stream):
            if event.agent_id == agent_id and event.round == round_num:
                event.downstream_effects.append(effect)
                break
