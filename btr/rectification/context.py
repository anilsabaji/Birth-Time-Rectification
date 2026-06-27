"""Inputs that drive a rectification run: events, traits and method weights."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.timeutil import GeoLocation
from ..kp.ruling_planets import RulingPlanets
from .events import LifeEvent

# Default blend of the seven methods. KP RP + event significators and Parashara
# dasha correlation carry the most weight; special points are lighter checks.
DEFAULT_METHOD_WEIGHTS: dict[str, float] = {
    "ruling_planets_match": 2.5,        # KP
    "cuspal_significator_event": 3.0,   # KP
    "dasha_event_correlation": 3.0,     # Parashara
    "varga_consistency": 1.5,           # Parashara
    "lagna_trait_match": 1.0,           # both
    "pranapada_check": 0.6,             # Parashara
    "gulika_check": 0.6,                # Parashara
}


@dataclass
class RectificationContext:
    """Everything the scorers need that is *independent* of the candidate time."""

    birth_tz: float
    events: list[LifeEvent] = field(default_factory=list)

    # KP Ruling Planets are taken at the moment of sitting for rectification.
    consultation_ruling_planets: RulingPlanets | None = None

    # Optional physical/lagna evidence.
    expected_lagna_signs: list[str] = field(default_factory=list)
    expected_lagna_nakshatra: str | None = None

    method_weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_METHOD_WEIGHTS)
    )

    def active_total_weight(self) -> float:
        return sum(self.method_weights.values())
