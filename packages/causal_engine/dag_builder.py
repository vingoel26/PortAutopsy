"""
causal_engine.dag_builder
~~~~~~~~~~~~~~~~~~~~~~~~~
Build a NetworkX directed graph from trace events.
Nodes = agent decisions. Edges = causal links.

Edge types:
  - slot_contention: two agents bid on the same crane slot
  - sequential: same agent across consecutive rounds
  - explicit: from DownstreamEffect objects in trace data

Export to D3.js-compatible JSON via json_graph.node_link_data().
"""

from __future__ import annotations

from collections import defaultdict
import networkx as nx
from networkx.readwrite import json_graph
from packages.autopsy_sdk import get_traces


def build_dag(max_depth: int = 3) -> nx.DiGraph:
    """
    Build a causal DAG from all traced events.
    Trims to nodes within max_depth hops of any failure node.
    """
    G = nx.DiGraph()
    events = get_traces()

    if not events:
        return G

    # ── Step 1: Add all nodes ────────────────────────────────
    for evt in events:
        node_id = f"{evt.agent_id}_r{evt.round}"
        G.add_node(
            node_id,
            agent_id=evt.agent_id,
            round=evt.round,
            output=evt.output,
            chain_of_thought=evt.chain_of_thought,
            status=evt.status.value,
            trace_id=evt.trace_id,
            is_failure=_is_failure_output(evt.output),
        )

    # ── Step 2: Slot contention edges ────────────────────────
    # If two agents bid on the same slot, they causally interact
    slot_map: dict[str, list] = defaultdict(list)
    for evt in events:
        slot = evt.output.get("slot")
        if slot:
            slot_map[slot].append(evt)

    for slot, slot_events in slot_map.items():
        if len(slot_events) > 1:
            # Sort by round so edges point forward in time
            sorted_evts = sorted(slot_events, key=lambda e: e.round)
            for i in range(len(sorted_evts) - 1):
                src = f"{sorted_evts[i].agent_id}_r{sorted_evts[i].round}"
                tgt = f"{sorted_evts[i + 1].agent_id}_r{sorted_evts[i + 1].round}"
                if src != tgt and G.has_node(src) and G.has_node(tgt):
                    G.add_edge(
                        src, tgt,
                        effect_type="slot_contention",
                        variable=slot,
                        label=f"contention: {slot}",
                    )

    # ── Step 3: Sequential edges (same agent, next round) ────
    agent_events: dict[str, list] = defaultdict(list)
    for evt in events:
        agent_events[evt.agent_id].append(evt)

    for agent_id, agent_evts in agent_events.items():
        sorted_evts = sorted(agent_evts, key=lambda e: e.round)
        for i in range(len(sorted_evts) - 1):
            src = f"{agent_id}_r{sorted_evts[i].round}"
            tgt = f"{agent_id}_r{sorted_evts[i + 1].round}"
            if G.has_node(src) and G.has_node(tgt):
                G.add_edge(
                    src, tgt,
                    effect_type="sequential",
                    variable="round_progression",
                    label="next round",
                )

    # ── Step 4: Explicit downstream effect edges ─────────────
    for evt in events:
        for effect in evt.downstream_effects:
            target_node = _find_target_node(effect.target_agent, events)
            if target_node:
                src = f"{evt.agent_id}_r{evt.round}"
                if G.has_node(src) and G.has_node(target_node):
                    G.add_edge(
                        src, target_node,
                        effect_type=effect.effect_type,
                        variable=effect.variable or "",
                        label=f"{effect.effect_type}: {effect.variable or ''}",
                    )

    # ── Step 5: Trim to failure-relevant subgraph ────────────
    return _trim_to_failures(G, max_depth)


def _is_failure_output(output: dict) -> bool:
    """Check if an output dict indicates a failure."""
    output_str = str(output).lower()
    return any(
        pattern in output_str
        for pattern in ("violation", "deadlock", "error", "failed")
    )


def _find_target_node(target_agent: str, events) -> str | None:
    """Exact match by agent_id — no substring matching."""
    for evt in events:
        if evt.agent_id == target_agent:
            return f"{evt.agent_id}_r{evt.round}"
    return None


def _trim_to_failures(G: nx.DiGraph, max_depth: int) -> nx.DiGraph:
    """Keep only nodes within max_depth hops of a single failure node."""
    all_failures = [n for n, d in G.nodes(data=True) if d.get("is_failure")]
    if not all_failures:
        return G  # No failures → return full graph

    # Only trace from the first failure to keep the DAG small enough for LLM prompts
    failures = all_failures[:1]

    reachable = set()
    for f in failures:
        reachable.add(f)
        # Include ancestors (what caused the failure)
        try:
            for pred in nx.ancestors(G, f):
                try:
                    if nx.shortest_path_length(G, pred, f) <= max_depth:
                        reachable.add(pred)
                except nx.NetworkXNoPath:
                    pass
        except nx.NetworkXError:
            pass
        # Include descendants (what the failure caused)
        try:
            for succ in nx.descendants(G, f):
                try:
                    if nx.shortest_path_length(G, f, succ) <= max_depth:
                        reachable.add(succ)
                except nx.NetworkXNoPath:
                    pass
        except nx.NetworkXError:
            pass

    if not reachable:
        return G

    return G.subgraph(reachable).copy()


def export_graph_json(G: nx.DiGraph) -> dict:
    """
    Standard NetworkX → D3.js node-link export.
    This is the format A2's frontend expects.
    """
    data = json_graph.node_link_data(G)
    # Ensure all node attributes are JSON-serializable
    for node in data.get("nodes", []):
        for key, val in list(node.items()):
            if not isinstance(val, (str, int, float, bool, type(None), list, dict)):
                node[key] = str(val)
    return data
