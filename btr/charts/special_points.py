"""Time-sensitive 'special points' used as rectification cross-checks.

These points move quickly with clock time, which is exactly why they are useful
for rectification:

* **Pranapada** - derived from the Sun and the time elapsed since sunrise.
* **Gulika / Mandi** - the ascendant taken at the Saturn-ruled eighth-part of
  the day (or night), a sub-planetary (upagraha) point.

Both depend on local sunrise/sunset, computed here with Swiss Ephemeris.
"""
from __future__ import annotations

from dataclasses import dataclass

import swisseph as swe

from ..core.constants import SIGN_QUALITY, Ayanamsa, HouseSystem, Planet
from ..core.ephemeris import Ephemeris, Position, norm360
from ..core.timeutil import GeoLocation

_RISE_FLAGS = swe.FLG_MOSEPH
_RSMI_RISE = swe.CALC_RISE | swe.BIT_DISC_CENTER
_RSMI_SET = swe.CALC_SET | swe.BIT_DISC_CENTER

# Weekday lord order used for the eighth-part (kala) assignment. Index 0 = the
# planetary lord of the weekday counted Sunday..Saturday.
WEEKDAY_LORDS = [
    Planet.SUN,      # Sunday
    Planet.MOON,     # Monday
    Planet.MARS,     # Tuesday
    Planet.MERCURY,  # Wednesday
    Planet.JUPITER,  # Thursday
    Planet.VENUS,    # Friday
    Planet.SATURN,   # Saturday
]


@dataclass(frozen=True)
class SunData:
    sunrise_jd: float
    sunset_jd: float
    next_sunrise_jd: float
    prev_sunrise_jd: float


def _rise(jd_start: float, loc: GeoLocation, rsmi: int) -> float:
    res, tret = swe.rise_trans(
        jd_start,
        swe.SUN,
        rsmi,
        (loc.longitude, loc.latitude, loc.altitude),
        0.0,
        0.0,
        _RISE_FLAGS,
    )
    if res < 0:
        raise ValueError("sun rise/set not found (circumpolar?)")
    return tret[0]


def compute_sun_data(jd_ut: float, loc: GeoLocation) -> SunData:
    """Find the sunrise that *begins the day containing* `jd_ut`, plus neighbours.

    We locate the latest sunrise at or before ``jd_ut`` (the one that opens the
    Vedic day the instant belongs to) and the next sunrise after it. This is
    robust regardless of where in the day/night the instant falls.
    """
    # Start from a sunrise comfortably before the instant, then walk forward to
    # the latest sunrise that is still <= jd_ut.
    sunrise = _rise(jd_ut - 1.0, loc, _RSMI_RISE)
    # If even that is after the instant (possible near the day boundary), back up.
    guard = 0
    while sunrise > jd_ut and guard < 5:
        sunrise = _rise(sunrise - 1.1, loc, _RSMI_RISE)
        guard += 1
    # Advance to the most recent sunrise on/before the instant.
    guard = 0
    while guard < 5:
        nxt = _rise(sunrise + 0.01, loc, _RSMI_RISE)
        if nxt <= jd_ut:
            sunrise = nxt
            guard += 1
        else:
            next_sunrise = nxt
            break
    else:
        next_sunrise = _rise(sunrise + 0.01, loc, _RSMI_RISE)

    sunset = _rise(sunrise, loc, _RSMI_SET)
    prev_sunrise = _rise(sunrise - 1.1, loc, _RSMI_RISE)
    return SunData(sunrise, sunset, next_sunrise, prev_sunrise)


def is_day_birth(jd_ut: float, sun: SunData) -> bool:
    return sun.sunrise_jd <= jd_ut < sun.sunset_jd


# --------------------------------------------------------------------------- #
# Pranapada
# --------------------------------------------------------------------------- #


def pranapada(eph: Ephemeris, jd_ut: float, loc: GeoLocation) -> Position:
    """Compute the Pranapada longitude.

    Algorithm:
      1. Elapsed time from sunrise -> minutes. (1 prana = 4 s; pranas/15 = min,
         so the ishta arc in degrees equals the elapsed minutes; Pranapada
         completes four zodiac cycles per day.)
      2. Add the Sun's sidereal longitude.
      3. Correct by the Sun's sign quality: movable +0, fixed +240, dual +120.
    """
    sun = compute_sun_data(jd_ut, loc)
    sunrise = sun.sunrise_jd
    if not is_day_birth(jd_ut, sun):
        # Night birth: measure ishta from the relevant sunrise (the one that
        # began this nychthemeron). Standard practice still counts from sunrise.
        if jd_ut < sun.sunrise_jd:
            sunrise = sun.prev_sunrise_jd
    elapsed_minutes = (jd_ut - sunrise) * 24.0 * 60.0
    ishta_arc = elapsed_minutes  # degrees

    sun_pos = eph.planet_position(jd_ut, Planet.SUN)
    quality = SIGN_QUALITY[sun_pos.sign_index]
    correction = {0: 0.0, 1: 240.0, 2: 120.0}[quality]

    pp = norm360(sun_pos.longitude + ishta_arc + correction)
    return Position(pp, 0.0)


# --------------------------------------------------------------------------- #
# Gulika / Mandi
# --------------------------------------------------------------------------- #


def _weekday_index_from_sunrise(sunrise_jd: float, loc: GeoLocation) -> int:
    """Vedic weekday (0=Sun..6=Sat) of the day that began at `sunrise_jd`.

    The Vedic day starts at sunrise, so we classify by the local civil date at
    the moment of sunrise. The astronomical identity ``floor(JD + 1.5) mod 7``
    yields 0=Sunday..6=Saturday directly; we add a longitude-based shift so the
    civil date is read in local solar time rather than UT.
    """
    import math

    jd_local = sunrise_jd + loc.longitude / 360.0  # crude local solar shift
    return int(math.floor(jd_local + 1.5)) % 7  # 0 = Sunday .. 6 = Saturday


def _saturn_part_bounds(
    jd_ut: float, sun: SunData, loc: GeoLocation
) -> tuple[float, float]:
    """Return (start_jd, end_jd) of the Saturn-ruled eighth-part.

    Day births divide sunrise->sunset; night births divide sunset->next
    sunrise. The first part's lord is the weekday lord (day) or the lord of the
    5th weekday from it (night); parts then proceed in weekday-lord order. The
    Saturn segment is Gulika's segment.
    """
    day = is_day_birth(jd_ut, sun)
    if day:
        start, end = sun.sunrise_jd, sun.sunset_jd
        weekday = _weekday_index_from_sunrise(sun.sunrise_jd, loc)
        first_lord_idx = weekday
    else:
        # Night: from sunset to next sunrise. Use the weekday of the day that
        # has just ended (the day part's weekday).
        if jd_ut < sun.sunrise_jd:
            # birth is before this sunrise -> belongs to previous night
            start, end = _rise(sun.prev_sunrise_jd, loc, _RSMI_SET), sun.sunrise_jd
            weekday = _weekday_index_from_sunrise(sun.prev_sunrise_jd, loc)
        else:
            start, end = sun.sunset_jd, sun.next_sunrise_jd
            weekday = _weekday_index_from_sunrise(sun.sunrise_jd, loc)
        # Night start lord = lord of the 5th weekday from the day lord.
        first_lord_idx = (weekday + 5) % 7

    part_len = (end - start) / 8.0
    # Find which of the 7 ruled parts is Saturn.
    for i in range(7):
        lord = WEEKDAY_LORDS[(first_lord_idx + i) % 7]
        if lord == Planet.SATURN:
            seg_start = start + i * part_len
            return seg_start, seg_start + part_len
    # Should never happen (Saturn always appears within 7 of any start).
    raise RuntimeError("Saturn part not found")


@dataclass(frozen=True)
class GulikaMandi:
    gulika: Position   # ascendant at the END of Saturn's part
    mandi: Position    # ascendant at the START (beginning) of Saturn's part
    saturn_part_start_jd: float
    saturn_part_end_jd: float


def gulika_mandi(eph: Ephemeris, jd_ut: float, loc: GeoLocation) -> GulikaMandi:
    """Compute Gulika and Mandi as ascendants at the Saturn eighth-part bounds.

    Traditions vary: we follow the convention where **Mandi** is the ascendant
    rising at the *beginning* of the Saturn part and **Gulika** at its *end*.
    """
    sun = compute_sun_data(jd_ut, loc)
    seg_start, seg_end = _saturn_part_bounds(jd_ut, sun, loc)
    mandi_asc = eph.geometry(seg_start, loc).ascendant
    gulika_asc = eph.geometry(seg_end, loc).ascendant
    return GulikaMandi(
        gulika=Position(gulika_asc, 0.0),
        mandi=Position(mandi_asc, 0.0),
        saturn_part_start_jd=seg_start,
        saturn_part_end_jd=seg_end,
    )
