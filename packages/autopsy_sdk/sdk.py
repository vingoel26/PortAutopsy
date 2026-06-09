"""
autopsy_sdk.sdk
~~~~~~~~~~~~~~~
Public query API for trace data.
Users and other packages import from here to read traces.
"""

from __future__ import annotations

import json
import sqlite3
from .event_stream import all_events, events_for, event_count, clear
from .event_stream import append_downstream_effect as _stream_append
from .event_logger import DB_PATH
from .event_logger import append_downstream_effect as _db_append
from .models import TraceEvent, DownstreamEffect, EventStatus


def add_downstream_effect(agent_id: str, round_num: int, effect: DownstreamEffect) -> None:
    """Attach a downstream effect to both in-memory and SQLite trace stores."""
    _stream_append(agent_id, round_num, effect)
    if DB_PATH.exists():
        _db_append(agent_id, round_num, effect)


def get_traces(agent_id: str | None = None) -> list[TraceEvent]:
    """
    Get trace events. Reads from in-memory stream first;
    if empty, falls back to SQLite (cross-process support).
    """
    if agent_id:
        events = events_for(agent_id)
        if events:
            return events

    events = all_events()
    if events:
        if agent_id:
            return [e for e in events if e.agent_id == agent_id]
        return events

    # Fallback: read from SQLite (cross-process scenario)
    return _load_from_db(agent_id)


def _load_from_db(agent_id: str | None = None) -> list[TraceEvent]:
    """Load trace events from SQLite (used when in-memory stream is empty)."""
    if not DB_PATH.exists():
        return []

    con = sqlite3.connect(str(DB_PATH))
    try:
        if agent_id:
            rows = con.execute(
                "SELECT * FROM trace_events WHERE agent_id=? ORDER BY timestamp",
                (agent_id,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM trace_events ORDER BY timestamp"
            ).fetchall()
    finally:
        con.close()

    events = []
    for row in rows:
        try:
            downstream_raw = json.loads(row[7] or "[]")
            downstream = [DownstreamEffect(**d) for d in downstream_raw]
            events.append(TraceEvent(
                trace_id=row[0],
                agent_id=row[1],
                timestamp=row[2],
                round=row[3] or 0,
                inputs=json.loads(row[4] or "{}"),
                chain_of_thought=row[5],
                output=json.loads(row[6] or "{}"),
                downstream_effects=downstream,
                status=EventStatus(row[8]) if row[8] else EventStatus.SUCCESS,
                error_message=row[9],
                duration_ms=row[10],
            ))
        except Exception:
            pass  # Skip malformed rows
    return events


def get_trace(trace_id: str) -> TraceEvent | None:
    """Look up a single trace event by trace_id from SQLite."""
    if not DB_PATH.exists():
        return None

    con = sqlite3.connect(str(DB_PATH))
    row = con.execute(
        "SELECT * FROM trace_events WHERE trace_id=?", (trace_id,)
    ).fetchone()
    con.close()

    if not row:
        return None

    # Parse downstream_effects back into Pydantic models
    downstream_raw = json.loads(row[7] or "[]")
    downstream = [DownstreamEffect(**d) for d in downstream_raw]

    return TraceEvent(
        trace_id=row[0],
        agent_id=row[1],
        timestamp=row[2],
        round=row[3] or 0,
        inputs=json.loads(row[4] or "{}"),
        chain_of_thought=row[5],
        output=json.loads(row[6] or "{}"),
        downstream_effects=downstream,
        status=EventStatus(row[8]) if row[8] else EventStatus.SUCCESS,
        error_message=row[9],
        duration_ms=row[10],
    )


def get_trace_count() -> int:
    """Return total number of events in the in-memory stream."""
    return event_count()


def clear_traces() -> None:
    """Clear in-memory stream (does NOT delete JSONL/SQLite data)."""
    clear()
