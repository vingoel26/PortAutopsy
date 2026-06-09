"""
autopsy_sdk
~~~~~~~~~~~
Observability SDK for multi-agent AI systems.

Quick start:
    from packages.autopsy_sdk import trace_agent, get_traces

    @trace_agent
    def my_agent(agent_id, ...):
        return {"action": "..."}

    my_agent(agent_id="agent_1", ...)
    traces = get_traces()
"""

from .tracer import trace_agent
from .sdk import get_traces, get_trace, get_trace_count, clear_traces, add_downstream_effect
from .models import (
    TraceEvent,
    AutopsyReport,
    DownstreamEffect,
    EventStatus,
)

__all__ = [
    "trace_agent",
    "get_traces",
    "get_trace",
    "get_trace_count",
    "clear_traces",
    "TraceEvent",
    "AutopsyReport",
    "DownstreamEffect",
    "EventStatus",
]
