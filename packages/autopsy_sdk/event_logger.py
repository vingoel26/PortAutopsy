"""
autopsy_sdk.event_logger
~~~~~~~~~~~~~~~~~~~~~~~~
Dual-write every TraceEvent to JSONL (human audit trail) + SQLite (queryable).
Thread-safe with WAL mode for concurrent reads during analysis.
"""

from __future__ import annotations

import json
import sqlite3
import pathlib
import threading
from .models import TraceEvent

# ── Configurable output paths ────────────────────────────────

JSONL_PATH = pathlib.Path("traces.jsonl")
DB_PATH = pathlib.Path("traces.db")

# ── Thread-safe connection pool ──────────────────────────────

_local = threading.local()
_write_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection with WAL mode enabled."""
    if not hasattr(_local, "con") or _local.con is None:
        _local.con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.con.execute("PRAGMA journal_mode=WAL")
        _local.con.execute("PRAGMA synchronous=NORMAL")
        _local.con.execute("""
            CREATE TABLE IF NOT EXISTS trace_events (
                trace_id      TEXT,
                agent_id      TEXT,
                timestamp     TEXT,
                round         INTEGER,
                inputs_json   TEXT,
                cot           TEXT,
                output_json   TEXT,
                downstream_json TEXT,
                status        TEXT,
                error         TEXT,
                duration_ms   REAL
            )
        """)
        _local.con.commit()
    return _local.con


def log_event(event: TraceEvent) -> None:
    """Write a validated TraceEvent to both JSONL and SQLite."""
    event_dict = event.model_dump(mode="json")

    # ── JSONL append (append-only, one JSON per line) ────────
    with _write_lock:
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_dict, default=str) + "\n")

    # ── SQLite insert ────────────────────────────────────────
    con = _get_connection()
    con.execute(
        "INSERT INTO trace_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            event.trace_id,
            event.agent_id,
            event.timestamp.isoformat(),
            event.round,
            json.dumps(event.inputs, default=str),
            event.chain_of_thought,
            json.dumps(event.output, default=str),
            json.dumps([e.model_dump() for e in event.downstream_effects]),
            event.status.value,
            event.error_message,
            event.duration_ms,
        ),
    )
    con.commit()


def read_all_from_db() -> list[dict]:
    """Read every row from SQLite (used by sdk.py for DB-backed queries)."""
    con = _get_connection()
    cur = con.execute("SELECT * FROM trace_events ORDER BY timestamp")
    columns = [
        "trace_id", "agent_id", "timestamp", "round",
        "inputs_json", "cot", "output_json",
        "downstream_json", "status", "error", "duration_ms",
    ]
    rows = []
    for row in cur.fetchall():
        rows.append(dict(zip(columns, row)))
    return rows


def append_downstream_effect(agent_id: str, round_num: int, effect: DownstreamEffect) -> None:
    """Attach a downstream effect to an existing trace event in SQLite."""
    con = _get_connection()
    # Fetch existing downstream_json
    row = con.execute(
        "SELECT downstream_json FROM trace_events WHERE agent_id=? AND round=? ORDER BY timestamp DESC LIMIT 1",
        (agent_id, round_num)
    ).fetchone()
    if not row:
        return

    current = json.loads(row[0] or "[]")
    current.append(effect.model_dump())

    con.execute(
        "UPDATE trace_events SET downstream_json=? WHERE agent_id=? AND round=?",
        (json.dumps(current, default=str), agent_id, round_num)
    )
    con.commit()
