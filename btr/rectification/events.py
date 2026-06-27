"""The life-event model that rectification is scored against.

Every method ultimately tests one question: *does this candidate birth time make
the chart agree with what actually happened in the native's life?* An event ties
a calendar date to the houses that should be activated, so both the Parashara
dasha test and the KP significator test can consume the same object.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from ..core.timeutil import GeoLocation, julian_day_from_local


class EventType(str, Enum):
    """Common life events with their canonical KP/Parashara house signatures."""

    MARRIAGE = "marriage"
    CHILD_BIRTH = "child_birth"
    CAREER_START = "career_start"
    JOB_CHANGE = "job_change"
    PROMOTION = "promotion"
    FOREIGN_TRAVEL = "foreign_travel"
    EDUCATION = "education"
    PROPERTY_VEHICLE = "property_vehicle"
    FATHER_DEATH = "father_death"
    MOTHER_DEATH = "mother_death"
    OWN_HEALTH_CRISIS = "own_health_crisis"
    FINANCIAL_GAIN = "financial_gain"
    LOSS_SEPARATION = "loss_separation"
    SPIRITUAL_INITIATION = "spiritual_initiation"
    CUSTOM = "custom"


# Canonical house groups activated by each event (KP convention).
# Houses that must be fructified; **the first house listed is the KP-primary
# cusp** (the one whose cuspal sub-lord is tested). The primary varga is the
# Parashara divisional chart most relevant to that event.
EVENT_HOUSES: dict[EventType, list[int]] = {
    EventType.MARRIAGE: [7, 2, 11],
    EventType.CHILD_BIRTH: [5, 2, 11],
    EventType.CAREER_START: [10, 2, 6, 11],
    EventType.JOB_CHANGE: [10, 6, 9, 1],
    EventType.PROMOTION: [10, 2, 6, 11],
    EventType.FOREIGN_TRAVEL: [12, 3, 9],
    EventType.EDUCATION: [4, 9, 11],
    EventType.PROPERTY_VEHICLE: [4, 11],
    EventType.FATHER_DEATH: [9, 2, 7],            # 9th=father; 2/7 maraka
    EventType.MOTHER_DEATH: [4, 2, 9],            # 4th=mother; 2/9 maraka
    EventType.OWN_HEALTH_CRISIS: [6, 8, 12, 1],
    EventType.FINANCIAL_GAIN: [11, 2, 6, 10],
    EventType.LOSS_SEPARATION: [12, 6, 8],
    EventType.SPIRITUAL_INITIATION: [12, 9, 5],
    EventType.CUSTOM: [],
}

EVENT_PRIMARY_VARGA: dict[EventType, str] = {
    EventType.MARRIAGE: "D9",
    EventType.CHILD_BIRTH: "D7",
    EventType.CAREER_START: "D10",
    EventType.JOB_CHANGE: "D10",
    EventType.PROMOTION: "D10",
    EventType.FATHER_DEATH: "D12",
    EventType.MOTHER_DEATH: "D12",
    EventType.EDUCATION: "D9",
}


@dataclass
class LifeEvent:
    """A confirmed, dated event used as rectification evidence."""

    event_type: EventType
    event_date: date
    description: str = ""
    # Override the default houses if the user knows better, else inferred.
    houses: list[int] = field(default_factory=list)
    # Time of day is usually irrelevant for the dasha/significator test; noon is
    # a safe default. Place defaults to the birth place unless supplied.
    hour: int = 12
    minute: int = 0
    weight: float = 1.0           # importance of this event in the total score
    location: GeoLocation | None = None

    def resolved_houses(self) -> list[int]:
        if self.houses:
            return self.houses
        return EVENT_HOUSES.get(self.event_type, [])

    def primary_varga(self) -> str | None:
        return EVENT_PRIMARY_VARGA.get(self.event_type)

    def julian_day_ut(self, tz_offset_hours: float) -> float:
        return julian_day_from_local(
            self.event_date.year,
            self.event_date.month,
            self.event_date.day,
            self.hour,
            self.minute,
            0.0,
            tz_offset_hours,
        )
