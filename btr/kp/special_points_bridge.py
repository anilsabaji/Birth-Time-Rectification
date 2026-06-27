"""Small bridge exposing the Vedic weekday lord for KP Ruling Planets.

The Vedic day begins at sunrise, so the 'day lord' for a birth just after
midnight but before sunrise is still the *previous* civil day's lord.
"""
from __future__ import annotations

from ..charts.special_points import (
    WEEKDAY_LORDS,
    compute_sun_data,
    _weekday_index_from_sunrise,
)
from ..core.constants import Planet
from ..core.timeutil import GeoLocation


def weekday_lord_for_jd(jd_ut: float, loc: GeoLocation) -> Planet:
    """Return the planetary lord of the Vedic weekday containing `jd_ut`."""
    sun = compute_sun_data(jd_ut, loc)
    # Determine which sunrise begins the Vedic day this instant belongs to.
    if jd_ut < sun.sunrise_jd:
        ruling_sunrise = sun.prev_sunrise_jd
    else:
        ruling_sunrise = sun.sunrise_jd
    weekday = _weekday_index_from_sunrise(ruling_sunrise, loc)  # 0=Sun..6=Sat
    return WEEKDAY_LORDS[weekday]
