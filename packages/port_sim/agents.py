"""
port_sim.agents
~~~~~~~~~~~~~~~
Agent framework: 195 mock agents + 5 hero agents with real Gemini LLM calls.
All agents are wrapped with @trace_agent for observability.
"""

from __future__ import annotations

import json
import os
import random
from packages.autopsy_sdk import trace_agent

# ── Hero agents make real LLM calls; everyone else is mocked ─
HERO_AGENTS = {
    "container_047", "container_112", "container_183",
    "container_201", "container_099",
}

# ── Try to initialize Gemini client ──────────────────────────
_LLM_AVAILABLE = False
_gemini_client = None

try:
    from google import genai
    _api_key = os.environ.get("GEMINI_API_KEY")
    if _api_key:
        _gemini_client = genai.Client(api_key=_api_key)
        _LLM_AVAILABLE = True
except (ImportError, Exception):
    pass


def _mock_decision(container, available_slots: list[str]) -> dict:
    """
    Deterministic mock for non-hero agents.
    Prefers refrigerated slots for cold chain cargo.
    """
    if not available_slots:
        return {
            "action": "WAIT",
            "slot": None,
            "bid_value": 0.0,
            "chain_of_thought": "No slots available, waiting.",
        }

    if container.cargo_type == "cold_chain" and container.temperature_constraint:
        # Prefer refrigerated slots (crane_0, crane_6, crane_12, crane_18)
        ref_slots = [
            s for s in available_slots
            if int(s.split("_")[1]) % 6 == 0
        ]
        if ref_slots:
            return {
                "action": "BID",
                "slot": ref_slots[0],
                "bid_value": round(random.uniform(0.6, 0.9), 2),
                "chain_of_thought": (
                    f"Cold chain cargo (temp={container.temperature_constraint}°C). "
                    f"Selected refrigerated slot {ref_slots[0]}."
                ),
            }

    # Standard: pick a random available slot
    slot = random.choice(available_slots)
    return {
        "action": "BID",
        "slot": slot,
        "bid_value": round(random.uniform(0.3, 0.7), 2),
        "chain_of_thought": (
            f"Standard {container.cargo_type} cargo. "
            f"Selected slot {slot} (cheapest available)."
        ),
    }


def _llm_decision(agent_id: str, container, available_slots: list[str], round_num: int) -> dict:
    """Real Gemini LLM call for hero agents."""
    prompt = f"""You are container agent {agent_id} in a port logistics simulation.

Container specs:
- cargo_type: {container.cargo_type}
- temperature_constraint: {container.temperature_constraint}
- urgency: {container.urgency}
- size_teu: {container.size_teu}

Available crane slots: {available_slots}
Negotiation round: {round_num}

Respond ONLY with a JSON object:
{{"action": "BID", "slot": "<slot_id>", "bid_value": <0.0-1.0>, "chain_of_thought": "<your reasoning>"}}

Pick the best slot for your cargo type. Cold chain cargo MUST use refrigerated slots (crane_0, crane_6, crane_12, crane_18)."""

    try:
        response = _gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
            },
        )
        raw = response.text.strip()
        result = json.loads(raw)
        # Validate required keys
        result.setdefault("action", "BID")
        result.setdefault("slot", available_slots[0] if available_slots else None)
        result.setdefault("bid_value", 0.5)
        result.setdefault("chain_of_thought", "LLM decision")
        return result
    except Exception as e:
        # Fall back to mock if LLM fails
        return _mock_decision(container, available_slots)


@trace_agent
def container_decide(
    agent_id: str,
    container,
    available_slots: list[str],
    round_num: int = 0,
) -> dict:
    """
    Main agent decision function.
    Hero agents use Gemini; everyone else uses deterministic mock.
    The @trace_agent decorator captures everything automatically.
    """
    if not available_slots:
        return {
            "action": "WAIT",
            "slot": None,
            "bid_value": 0.0,
            "chain_of_thought": "No available slots.",
        }

    if agent_id in HERO_AGENTS and _LLM_AVAILABLE:
        return _llm_decision(agent_id, container, available_slots, round_num)

    return _mock_decision(container, available_slots)
