"""
port_sim.containers
~~~~~~~~~~~~~~~~~~~
Container dataclass and spawner.
Each container represents cargo that needs a crane slot at the port.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import random
import uuid


@dataclass
class Container:
    """A single container with cargo constraints."""
    container_id: str = field(
        default_factory=lambda: f"container_{uuid.uuid4().hex[:3]}"
    )
    cargo_type: str = "standard"              # "cold_chain", "hazmat", "standard"
    temperature_constraint: Optional[float] = None  # °C, None for non-cold
    urgency: str = "NORMAL"                   # "LOW", "NORMAL", "HIGH", "CRITICAL"
    size_teu: int = 1                         # 1 or 2
    customs_cleared: bool = True
    dwell_time_target: float = 4.0            # hours


def spawn_containers(n: int = 200, seed: int | None = 42) -> list[Container]:
    """
    Generate n containers with realistic cargo distributions.
    Uses a fixed seed by default for reproducible demos.
    """
    if seed is not None:
        random.seed(seed)

    containers = []
    for i in range(n):
        cargo = random.choices(
            ["standard", "cold_chain", "hazmat"],
            weights=[0.75, 0.20, 0.05],
        )[0]

        containers.append(Container(
            container_id=f"container_{i:03d}",
            cargo_type=cargo,
            temperature_constraint=(
                round(random.uniform(2.0, 8.0), 1) if cargo == "cold_chain" else None
            ),
            urgency=random.choices(
                ["LOW", "NORMAL", "HIGH", "CRITICAL"],
                weights=[0.2, 0.5, 0.25, 0.05],
            )[0],
            size_teu=random.choice([1, 1, 2]),
            customs_cleared=random.random() > 0.05,
            dwell_time_target=round(random.uniform(2.0, 8.0), 1),
        ))

    return containers
