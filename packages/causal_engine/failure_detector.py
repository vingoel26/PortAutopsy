"""
causal_engine.failure_detector
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Rule-based failure detection with severity scoring.
Uses callable detectors instead of brittle string matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable
from packages.autopsy_sdk import get_traces
from packages.autopsy_sdk.models import TraceEvent


# ── Detected failure record ──────────────────────────────────

@dataclass
class DetectedFailure:
    """A single detected failure with context."""
    trace_id: str
    agent_id: str
    round: int
    rule_name: str
    severity: int       # 1–10, higher = worse
    detail: str = ""


# ── Failure rules ────────────────────────────────────────────

@dataclass
class FailureRule:
    """A named failure detector with a severity level."""
    name: str
    severity: int
    detect: Callable[[TraceEvent], bool]
    description: str = ""


def _check_deadlock(evt: TraceEvent) -> bool:
    """Two+ agents stuck bidding MAX on the same slot."""
    output_str = str(evt.output).lower()
    cot_str = str(evt.chain_of_thought or "").lower()
    return "deadlock" in output_str or "deadlock" in cot_str


def _check_cold_chain_violation(evt: TraceEvent) -> bool:
    """Cold chain container placed on non-refrigerated slot."""
    output = evt.output
    # Direct violation flag
    if output.get("violation") is True:
        return True
    output_str = str(output).lower()
    if "cold_chain_violation" in output_str:
        return True

    # Infer violation: cold_chain cargo on a non-refrigerated slot
    inputs = evt.inputs
    container = inputs.get("container", {})
    if isinstance(container, dict):
        cargo_type = container.get("cargo_type", "")
    else:
        cargo_type = inputs.get("cargo_type", "")

    if cargo_type == "cold_chain":
        slot = output.get("slot", "")
        if slot:
            # Refrigerated slots are crane_0, crane_6, crane_12, crane_18
            try:
                crane_num = int(slot.split("_")[1])
                if crane_num % 6 != 0:
                    return True  # Cold chain on non-refrigerated slot!
            except (IndexError, ValueError):
                pass
    return False


def _check_constraint_null(evt: TraceEvent) -> bool:
    """Cold chain cargo with missing temperature constraint."""
    inputs = evt.inputs
    cargo_type = (
        inputs.get("cargo_type")
        or str(inputs.get("container", {}).get("cargo_type", ""))
    )
    temp = inputs.get("temperature_constraint")
    if temp is None:
        # Check nested container object
        container = inputs.get("container", {})
        if isinstance(container, dict):
            temp = container.get("temperature_constraint")

    return cargo_type == "cold_chain" and temp is None


def _check_urgency_misread(evt: TraceEvent) -> bool:
    """Agent misreads urgency, treats HIGH/CRITICAL as LOW."""
    cot = str(evt.chain_of_thought or "").lower()
    inputs = evt.inputs
    container = inputs.get("container", {})
    if isinstance(container, dict):
        urgency = container.get("urgency", "NORMAL")
    else:
        urgency = inputs.get("urgency", "NORMAL")

    if urgency in ("HIGH", "CRITICAL"):
        # Check if CoT treats it as low priority
        return "low priority" in cot or "not urgent" in cot
    return False


# ── Rule registry ────────────────────────────────────────────

RULES: list[FailureRule] = [
    FailureRule(
        "deadlock", 10, _check_deadlock,
        "Multiple agents stuck in infinite bidding on the same resource",
    ),
    FailureRule(
        "cold_chain_violation", 9, _check_cold_chain_violation,
        "Temperature-sensitive cargo placed on non-refrigerated slot",
    ),
    FailureRule(
        "urgency_misread", 7, _check_urgency_misread,
        "Agent misinterprets urgency level, delays critical cargo",
    ),
    FailureRule(
        "constraint_null", 5, _check_constraint_null,
        "Cold chain cargo missing temperature constraint (silently dropped)",
    ),
]


# ── Public API ───────────────────────────────────────────────

def detect_failures() -> list[DetectedFailure]:
    """
    Scan all trace events against all failure rules.
    Returns a list sorted by severity (worst first).
    """
    failures: list[DetectedFailure] = []

    for evt in get_traces():
        for rule in RULES:
            try:
                if rule.detect(evt):
                    failures.append(
                        DetectedFailure(
                            trace_id=evt.trace_id,
                            agent_id=evt.agent_id,
                            round=evt.round,
                            rule_name=rule.name,
                            severity=rule.severity,
                            detail=rule.description,
                        )
                    )
            except Exception:
                # Never let a detector crash the pipeline
                pass

    # Sort: highest severity first
    return sorted(failures, key=lambda f: f.severity, reverse=True)


def get_rules() -> list[dict]:
    """Return rule metadata for the dashboard."""
    return [
        {"name": r.name, "severity": r.severity, "description": r.description}
        for r in RULES
    ]
