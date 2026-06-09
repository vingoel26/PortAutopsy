"""
port_sim.resources
~~~~~~~~~~~~~~~~~~
Port resource state machine: berths, cranes, and slot allocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Crane:
    """A single crane at a berth."""
    crane_id: str
    berth_id: str
    refrigerated: bool = False
    occupied_until: float = 0.0     # simulation time


@dataclass
class Berth:
    """A berth with multiple cranes."""
    berth_id: str
    capacity_teu: int = 4
    current_teu: int = 0
    cranes: list[str] = field(default_factory=list)


class PortResources:
    """
    Manages 4 berths × 6 cranes = 24 total cranes.
    First crane per berth is refrigerated (for cold chain cargo).
    """

    def __init__(self):
        self.berths: dict[str, Berth] = {}
        self.cranes: dict[str, Crane] = {}

        crane_idx = 0
        for i in range(4):
            berth_id = f"berth_{i}"
            self.berths[berth_id] = Berth(berth_id)

            for j in range(6):
                crane_id = f"crane_{crane_idx}"
                # First crane per berth is refrigerated
                refrigerated = (j == 0)
                crane = Crane(crane_id, berth_id, refrigerated)
                self.cranes[crane_id] = crane
                self.berths[berth_id].cranes.append(crane_id)
                crane_idx += 1

    def available_slots(self, t: float) -> list[str]:
        """Return crane IDs that are free at simulation time t."""
        return [
            c_id for c_id, c in self.cranes.items()
            if c.occupied_until <= t
        ]

    def refrigerated_slots(self, t: float) -> list[str]:
        """Return refrigerated crane IDs that are free at time t."""
        return [
            c_id for c_id, c in self.cranes.items()
            if c.refrigerated and c.occupied_until <= t
        ]

    def allocate(self, crane_id: str, until: float) -> None:
        """Mark a crane as occupied until the given time."""
        if crane_id in self.cranes:
            self.cranes[crane_id].occupied_until = until

    def snapshot(self) -> dict:
        """Serialize resource state for counterfactual replay."""
        return {
            "cranes": {
                k: {
                    "occupied_until": v.occupied_until,
                    "refrigerated": v.refrigerated,
                    "berth_id": v.berth_id,
                }
                for k, v in self.cranes.items()
            },
            "berths": {
                k: {"current_teu": v.current_teu}
                for k, v in self.berths.items()
            },
        }
