"""Date/time helpers: local civil time <-> UTC <-> Julian Day (UT).

Birth times are almost always recorded in local civil (clock) time with a known
UTC offset. Swiss Ephemeris works in Universal Time, so everything funnels
through :func:`to_julian_day_ut`.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import swisseph as swe


@dataclass(frozen=True)
class GeoLocation:
    """A birth/event place. Longitude is positive East, latitude positive North."""

    latitude: float
    longitude: float
    altitude: float = 0.0
    name: str = ""

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError(f"latitude out of range: {self.latitude}")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError(f"longitude out of range: {self.longitude}")


@dataclass(frozen=True)
class BirthMoment:
    """A fully specified instant of birth in *local civil time*.

    `tz_offset_hours` is the offset of the local clock from UTC, e.g. +5.5 for
    India Standard Time. We store the offset explicitly rather than a tz name so
    historical/ambiguous zones are unambiguous for rectification.
    """

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: float
    tz_offset_hours: float
    location: GeoLocation

    def local_datetime(self) -> datetime:
        tz = timezone(timedelta(hours=self.tz_offset_hours))
        whole = int(self.second)
        micro = int(round((self.second - whole) * 1_000_000))
        return datetime(
            self.year,
            self.month,
            self.day,
            self.hour,
            self.minute,
            whole,
            micro,
            tzinfo=tz,
        )

    def utc_datetime(self) -> datetime:
        return self.local_datetime().astimezone(timezone.utc)

    def with_local_time(self, dt: datetime) -> "BirthMoment":
        """Return a copy whose civil time is replaced by `dt` (same tz/place)."""
        return BirthMoment(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            second=dt.second + dt.microsecond / 1_000_000,
            tz_offset_hours=self.tz_offset_hours,
            location=self.location,
        )

    def shifted(self, seconds: float) -> "BirthMoment":
        """Return a copy shifted forward/backward by `seconds` of local time."""
        return self.with_local_time(self.local_datetime() + timedelta(seconds=seconds))

    def julian_day_ut(self) -> float:
        return to_julian_day_ut(self.utc_datetime())

    def label(self) -> str:
        return self.local_datetime().strftime("%Y-%m-%d %H:%M:%S")


def to_julian_day_ut(dt_utc: datetime) -> float:
    """Convert a timezone-aware UTC datetime into a Julian Day (UT)."""
    if dt_utc.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    dt_utc = dt_utc.astimezone(timezone.utc)
    frac_hour = (
        dt_utc.hour
        + dt_utc.minute / 60.0
        + dt_utc.second / 3600.0
        + dt_utc.microsecond / 3_600_000_000.0
    )
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, frac_hour, swe.GREG_CAL)


def julian_day_from_local(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: float = 0.0,
    tz_offset_hours: float = 0.0,
) -> float:
    """Convenience: build a JD(UT) directly from local civil components."""
    tz = timezone(timedelta(hours=tz_offset_hours))
    whole = int(second)
    micro = int(round((second - whole) * 1_000_000))
    local = datetime(year, month, day, hour, minute, whole, micro, tzinfo=tz)
    return to_julian_day_ut(local.astimezone(timezone.utc))


def datetime_from_jd_ut(jd: float, tz_offset_hours: float = 0.0) -> datetime:
    """Inverse of :func:`to_julian_day_ut`, returned in the requested offset."""
    y, m, d, frac_hour = swe.revjul(jd, swe.GREG_CAL)
    hour = int(frac_hour)
    rem_min = (frac_hour - hour) * 60.0
    minute = int(rem_min)
    second = (rem_min - minute) * 60.0
    whole = int(second)
    micro = int(round((second - whole) * 1_000_000))
    if micro >= 1_000_000:  # rounding guard
        micro -= 1_000_000
        whole += 1
    dt_utc = datetime(y, m, d, hour, minute, min(whole, 59), micro, tzinfo=timezone.utc)
    return dt_utc.astimezone(timezone(timedelta(hours=tz_offset_hours)))
