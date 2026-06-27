"""End-to-end tests for the rectification engine."""
from datetime import date

import pytest

from btr.api import make_birth_moment, rectify
from btr.core.constants import Ayanamsa, HouseSystem
from btr.core.ephemeris import Ephemeris
from btr.core.timeutil import GeoLocation, julian_day_from_local
from btr.kp.ruling_planets import compute_ruling_planets
from btr.rectification.context import RectificationContext
from btr.rectification.engine import score_moment
from btr.rectification.events import EventType, LifeEvent

DELHI = GeoLocation(28.6139, 77.2090, name="New Delhi")


def _ctx():
    eph = Ephemeris(Ayanamsa.KRISHNAMURTI, HouseSystem.PLACIDUS)
    cjd = julian_day_from_local(2026, 6, 27, 11, 0, 0, 5.5)
    rp = compute_ruling_planets(eph, cjd, DELHI)
    events = [
        LifeEvent(EventType.MARRIAGE, date(2018, 2, 10)),
        LifeEvent(EventType.CHILD_BIRTH, date(2020, 6, 1)),
        LifeEvent(EventType.CAREER_START, date(2013, 7, 15)),
    ]
    return RectificationContext(
        birth_tz=5.5,
        events=events,
        consultation_ruling_planets=rp,
        expected_lagna_signs=["Scorpio"],
    )


def test_score_moment_in_range():
    moment = make_birth_moment(1990, 8, 15, 14, 30, 0, 5.5, 28.6139, 77.2090, "Delhi")
    result = score_moment(moment, _ctx())
    assert 0.0 <= result.total_score <= 100.0
    # All seven methods should report.
    names = {ms.name for ms in result.method_scores}
    assert names == {
        "ruling_planets_match",
        "cuspal_significator_event",
        "dasha_event_correlation",
        "varga_consistency",
        "pranapada_check",
        "gulika_check",
        "lagna_trait_match",
    }


def test_rectify_returns_ranked_report():
    moment = make_birth_moment(1990, 8, 15, 14, 30, 0, 5.5, 28.6139, 77.2090, "Delhi")
    report = rectify(moment, _ctx(), window_minutes=12,
                     coarse_step_seconds=240, fine_step_seconds=30)
    assert len(report.ranked) > 1
    # Sorted descending by score.
    scores = [c.total_score for c in report.ranked]
    assert scores == sorted(scores, reverse=True)
    assert report.best.total_score >= report.ranked[-1].total_score


def test_score_varies_with_time():
    """A scan must not return a flat landscape - times should differ."""
    ctx = _ctx()
    moment = make_birth_moment(1990, 8, 15, 14, 30, 0, 5.5, 28.6139, 77.2090, "Delhi")
    report = rectify(moment, ctx, window_minutes=25,
                     coarse_step_seconds=180, fine_step_seconds=60)
    distinct = {round(c.total_score, 1) for c in report.ranked}
    assert len(distinct) > 1


def test_no_events_still_runs():
    """With no events the event-based methods contribute zero but it shouldn't crash."""
    ctx = RectificationContext(birth_tz=5.5, expected_lagna_signs=["Scorpio"])
    moment = make_birth_moment(1990, 8, 15, 14, 30, 0, 5.5, 28.6139, 77.2090, "Delhi")
    result = score_moment(moment, ctx)
    assert 0.0 <= result.total_score <= 100.0
