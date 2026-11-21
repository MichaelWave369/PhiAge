"""Uncalibrated educational system dynamics, never a human outcome model."""
from __future__ import annotations

import math

def simulate(steps: int = 80, generation: float = 0.06,
             repair: float = 0.04, boost: float = 0.0) -> dict:
    if type(steps) is not int or not 1 <= steps <= 1000:
        raise ValueError("steps must be integer 1..1000")
    for name, value in (("generation", generation), ("repair", repair), ("boost", boost)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        if not 0 <= value <= 1:
            raise ValueError(f"{name} must be 0..1")
    damage, inflammation, senescence, capacity = 0.18, 0.08, 0.04, 0.85
    series = []
    clamp = lambda n: max(0.0, min(1.0, n))
    for t in range(steps + 1):
        series.append({
            "step": t, "damage": round(damage, 6),
            "inflammation": round(inflammation, 6),
            "senescence": round(senescence, 6),
            "repair_capacity": round(capacity, 6),
        })
        previous_damage, previous_inflammation, previous_senescence = damage, inflammation, senescence
        damage = clamp(previous_damage + 0.2 * (
            generation * (1 + 0.5 * previous_inflammation)
            - repair * capacity * (1 + boost)))
        inflammation = clamp(previous_inflammation + 0.013 * previous_damage
                             + 0.006 * previous_senescence - 0.012 * previous_inflammation)
        senescence = clamp(previous_senescence + 0.012 * previous_damage
                           - 0.006 * previous_senescence)
        capacity = clamp(capacity + 0.003 * (1 - previous_damage)
                         - 0.008 * previous_damage)
    return {
        "model": "phiage-toy-feedback/v0.1",
        "parameters": {"steps": steps, "generation": generation, "repair": repair, "boost": boost},
        "series": series,
        "warning": "Toy equations with arbitrary dimensionless parameters and steps. No calibration, human-age mapping, clinical interpretation, or safety inference.",
    }
