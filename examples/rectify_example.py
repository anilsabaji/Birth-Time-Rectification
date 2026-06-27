"""Programmatic example: rectify a birth time against confirmed life events.

Run:  python examples/rectify_example.py
"""
from datetime import date

from btr.api import chart_report, make_birth_moment, rectify
from btr.core.constants import Ayanamsa, HouseSystem
from btr.core.ephemeris import Ephemeris
from btr.core.timeutil import julian_day_from_local
from btr.kp.ruling_planets import compute_ruling_planets
from btr.rectification.context import RectificationContext
from btr.rectification.events import EventType, LifeEvent


def main() -> None:
    # 1. The recorded (uncertain) birth time.
    birth = make_birth_moment(
        year=1990, month=8, day=15, hour=14, minute=30, second=0,
        tz_offset_hours=5.5, latitude=28.6139, longitude=77.2090,
        place_name="New Delhi, India",
    )

    # 2. Ruling Planets at the moment of sitting for rectification (KP).
    kp_eph = Ephemeris(Ayanamsa.KRISHNAMURTI, HouseSystem.PLACIDUS)
    consult_jd = julian_day_from_local(2026, 6, 27, 11, 0, 0, 5.5)
    consultation_rp = compute_ruling_planets(kp_eph, consult_jd, birth.location)

    # 3. Confirmed, dated life events (the evidence).
    events = [
        LifeEvent(EventType.MARRIAGE, date(2018, 2, 10), "Marriage", weight=1.5),
        LifeEvent(EventType.CHILD_BIRTH, date(2020, 6, 1), "First child", weight=1.2),
        LifeEvent(EventType.CAREER_START, date(2013, 7, 15), "First job", weight=1.0),
        LifeEvent(EventType.FOREIGN_TRAVEL, date(2016, 9, 20), "Moved abroad", weight=0.8),
    ]

    ctx = RectificationContext(
        birth_tz=5.5,
        events=events,
        consultation_ruling_planets=consultation_rp,
        expected_lagna_signs=["Scorpio"],
    )

    print(chart_report(birth, ayanamsa=Ayanamsa.KRISHNAMURTI))
    print()

    report = rectify(birth, ctx, window_minutes=30,
                     coarse_step_seconds=240, fine_step_seconds=10)
    print(report.render(n=3))


if __name__ == "__main__":
    main()
