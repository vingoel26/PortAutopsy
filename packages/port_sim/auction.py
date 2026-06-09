"""
port_sim.auction
~~~~~~~~~~~~~~~~
Second-price-style auction engine.
Resolves competing bids for crane slots.
"""

from __future__ import annotations

from collections import defaultdict


def run_auction(bids: list[dict], resources) -> dict[str, str]:
    """
    Resolve competing bids for crane slots.

    Args:
        bids: list of {"agent_id": ..., "slot": ..., "bid_value": ...}
        resources: PortResources instance (for validation)

    Returns:
        {agent_id: allocated_slot} mapping
    """
    if not bids:
        return {}

    allocations: dict[str, str] = {}
    allocated_slots: set[str] = set()

    # Sort all bids by value descending — highest bidder wins
    all_bids_sorted = sorted(bids, key=lambda b: b["bid_value"], reverse=True)

    for bid in all_bids_sorted:
        agent = bid["agent_id"]
        slot = bid["slot"]

        # Skip if agent already allocated or slot already taken
        if agent not in allocations and slot not in allocated_slots:
            allocations[agent] = slot
            allocated_slots.add(slot)

    return allocations
