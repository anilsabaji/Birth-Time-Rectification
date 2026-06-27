"""Tests for the core astronomy + time layer."""
from datetime import datetime, timezone

import pytest

from btr.core.constants import Ayanamsa, HouseSystem, Planet
from btr.core.ephemeris import Ephemeris, Position, norm360
from btr.core.timeutil import (
    BirthMoment,
    GeoLocation,
    datetime_from_jd_ut,
    julian_day_from_local,
    to_julian_day_ut,
)

DELHI = GeoLocation(28.6139, 77.2090, name="New Delhi")


def test_norm360():
    assert norm360(370.0) == pytest.approx(10.0)
    assert norm360(-10.0) == pytest.approx(350.0)


def test_jd_roundtrip():
    jd = julian_day_from_local(1990, 8, 15, 14, 30, 0, 5.5)
    dt = datetime_from_jd_ut(jd, 5.5)
    assert (dt.year, dt.month, dt.day, dt.hour, dt.minute) == (1990, 8, 15, 14, 30)


def test_birth_moment_shift():
    bm = BirthMoment(1990, 8, 15, 14, 30, 0, 5.5, DELHI)
    shifted = bm.shifted(90)  # +90 s
    assert shifted.local_datetime() - bm.local_datetime() == \
        (datetime(2000, 1, 1, 0, 1, 30) - datetime(2000, 1, 1, 0, 0, 0))


def test_utc_conversion():
    bm = BirthMoment(1990, 8, 15, 14, 30, 0, 5.5, DELHI)
    assert bm.utc_datetime() == datetime(1990, 8, 15, 9, 0, 0, tzinfo=timezone.utc)


def test_position_properties():
    # 45 deg = Taurus 15, Krittika area
    pos = Position(45.0)
    assert pos.sign == "Taurus"
    assert pos.degree_in_sign == pytest.approx(15.0)
    assert 0 <= pos.nakshatra_index < 27
    assert 1 <= pos.pada <= 4


def test_geometry_has_twelve_cusps():
    eph = Ephemeris(Ayanamsa.LAHIRI, HouseSystem.PLACIDUS)
    jd = julian_day_from_local(1990, 8, 15, 14, 30, 0, 5.5)
    geo = eph.geometry(jd, DELHI)
    assert len(geo.cusps) == 12
    assert geo.cusps[0] == pytest.approx(geo.ascendant, abs=1e-6)
    # all nine grahas present
    assert set(geo.planets.keys()) == set(Planet)


def test_ketu_opposite_rahu():
    eph = Ephemeris(Ayanamsa.LAHIRI, HouseSystem.PLACIDUS)
    jd = julian_day_from_local(1990, 8, 15, 14, 30, 0, 5.5)
    geo = eph.geometry(jd, DELHI)
    rahu = geo.planet(Planet.RAHU).longitude
    ketu = geo.planet(Planet.KETU).longitude
    assert norm360(ketu - rahu) == pytest.approx(180.0, abs=1e-6)


def test_house_of_whole_sign():
    eph = Ephemeris(Ayanamsa.LAHIRI, HouseSystem.PLACIDUS)
    jd = julian_day_from_local(1990, 8, 15, 14, 30, 0, 5.5)
    geo = eph.geometry(jd, DELHI)
    # The ascendant longitude must be in house 1 under whole-sign.
    assert geo.house_of(geo.ascendant, whole_sign=True) == 1
