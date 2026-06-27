"""Swiss Ephemeris wrapper producing sidereal positions, ascendant and cusps.

This module is the *only* place that talks to ``swisseph`` for chart geometry.
Everything is sidereal (Lahiri or KP ayanamsa). The Moshier ephemeris flag is
used so no external ephemeris data files are required.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

import swisseph as swe

from .constants import (
    ALL_PLANETS,
    DEG_PER_NAKSHATRA,
    DEG_PER_PADA,
    DEG_PER_SIGN,
    NAKSHATRAS,
    SIGNS,
    Ayanamsa,
    HouseSystem,
    Planet,
)
from .timeutil import GeoLocation

# Swiss Ephemeris uses global state for sidereal mode, so guard with a lock to
# keep concurrent rectification scans (or test runs) deterministic.
_SWE_LOCK = threading.RLock()

_PLANET_SWE_ID = {
    Planet.SUN: swe.SUN,
    Planet.MOON: swe.MOON,
    Planet.MARS: swe.MARS,
    Planet.MERCURY: swe.MERCURY,
    Planet.JUPITER: swe.JUPITER,
    Planet.VENUS: swe.VENUS,
    Planet.SATURN: swe.SATURN,
    Planet.RAHU: swe.TRUE_NODE,  # KP/most Vedic use the true node
}

_AYANAMSA_SWE_ID = {
    Ayanamsa.LAHIRI: swe.SIDM_LAHIRI,
    Ayanamsa.KRISHNAMURTI: swe.SIDM_KRISHNAMURTI,
}

_BASE_FLAGS = swe.FLG_MOSEPH | swe.FLG_SPEED


def norm360(deg: float) -> float:
    """Normalise an angle to the [0, 360) range."""
    return deg % 360.0


@dataclass(frozen=True)
class Position:
    """A point on the sidereal zodiac with derived sign/nakshatra info."""

    longitude: float            # sidereal ecliptic longitude [0,360)
    speed: float = 0.0          # degrees/day (negative = retrograde)

    @property
    def sign_index(self) -> int:
        return int(self.longitude // DEG_PER_SIGN)

    @property
    def sign(self) -> str:
        return SIGNS[self.sign_index]

    @property
    def degree_in_sign(self) -> float:
        return self.longitude % DEG_PER_SIGN

    @property
    def nakshatra_index(self) -> int:
        return int(self.longitude // DEG_PER_NAKSHATRA)

    @property
    def nakshatra(self) -> str:
        return NAKSHATRAS[self.nakshatra_index]

    @property
    def pada(self) -> int:
        """Pada (quarter) 1-4 within the nakshatra."""
        offset = self.longitude % DEG_PER_NAKSHATRA
        return int(offset // DEG_PER_PADA) + 1

    @property
    def is_retrograde(self) -> bool:
        return self.speed < 0

    def dms(self) -> str:
        d = int(self.degree_in_sign)
        m_full = (self.degree_in_sign - d) * 60.0
        m = int(m_full)
        s = (m_full - m) * 60.0
        return f"{self.sign} {d:02d}\u00b0{m:02d}'{s:04.1f}\""


@dataclass(frozen=True)
class PlanetPosition(Position):
    planet: Planet = Planet.SUN


@dataclass(frozen=True)
class ChartGeometry:
    """Raw geometry for one instant: planets, ascendant and 12 house cusps."""

    jd_ut: float
    ayanamsa: Ayanamsa
    ayanamsa_value: float
    planets: dict[Planet, PlanetPosition]
    cusps: list[float]          # 12 cusp longitudes, index 0 = 1st house cusp
    ascendant: float
    midheaven: float

    def planet(self, p: Planet) -> PlanetPosition:
        return self.planets[p]

    def asc_position(self) -> Position:
        return Position(self.ascendant, 0.0)

    def cusp_position(self, house: int) -> Position:
        """House is 1-based (1..12)."""
        return Position(self.cusps[house - 1], 0.0)

    def house_of(self, longitude: float, *, whole_sign: bool = False) -> int:
        """Return the 1-based house a longitude falls in given the cusps.

        For Placidus/Equal we test which cusp-to-cusp arc contains the point.
        For whole-sign we count signs from the ascendant's sign.
        """
        lon = norm360(longitude)
        if whole_sign:
            asc_sign = int(self.ascendant // DEG_PER_SIGN)
            pt_sign = int(lon // DEG_PER_SIGN)
            return ((pt_sign - asc_sign) % 12) + 1
        for i in range(12):
            start = self.cusps[i]
            end = self.cusps[(i + 1) % 12]
            span = (end - start) % 360.0
            rel = (lon - start) % 360.0
            if rel < span:
                return i + 1
        return 12


class Ephemeris:
    """High-level sidereal ephemeris bound to a chosen ayanamsa + house system."""

    def __init__(
        self,
        ayanamsa: Ayanamsa = Ayanamsa.LAHIRI,
        house_system: HouseSystem = HouseSystem.PLACIDUS,
    ) -> None:
        self.ayanamsa = ayanamsa
        self.house_system = house_system

    def _set_mode(self) -> None:
        swe.set_sid_mode(_AYANAMSA_SWE_ID[self.ayanamsa], 0, 0)

    def ayanamsa_value(self, jd_ut: float) -> float:
        with _SWE_LOCK:
            self._set_mode()
            return swe.get_ayanamsa_ut(jd_ut)

    def planet_position(self, jd_ut: float, planet: Planet) -> PlanetPosition:
        with _SWE_LOCK:
            self._set_mode()
            return self._planet_position_unlocked(jd_ut, planet)

    def _planet_position_unlocked(self, jd_ut: float, planet: Planet) -> PlanetPosition:
        flags = _BASE_FLAGS | swe.FLG_SIDEREAL
        if planet == Planet.KETU:
            rahu = self._planet_position_unlocked(jd_ut, Planet.RAHU)
            return PlanetPosition(
                longitude=norm360(rahu.longitude + 180.0),
                speed=rahu.speed,
                planet=Planet.KETU,
            )
        swe_id = _PLANET_SWE_ID[planet]
        values, _ = swe.calc_ut(jd_ut, swe_id, flags)
        return PlanetPosition(
            longitude=norm360(values[0]),
            speed=values[3],
            planet=planet,
        )

    def geometry(self, jd_ut: float, location: GeoLocation) -> ChartGeometry:
        """Compute the full chart geometry for an instant + place."""
        with _SWE_LOCK:
            self._set_mode()
            ayan = swe.get_ayanamsa_ut(jd_ut)
            planets = {
                p: self._planet_position_unlocked(jd_ut, p) for p in ALL_PLANETS
            }
            cusps, ascmc = swe.houses_ex(
                jd_ut,
                location.latitude,
                location.longitude,
                self.house_system.value.encode("ascii"),
                swe.FLG_SIDEREAL,
            )
            # swe returns 12 cusps in cusps[0..11] for most systems; some builds
            # return a 13-length tuple with a leading dummy. Normalise to 12.
            cusp_list = [norm360(c) for c in cusps[:12]]
            return ChartGeometry(
                jd_ut=jd_ut,
                ayanamsa=self.ayanamsa,
                ayanamsa_value=ayan,
                planets=planets,
                cusps=cusp_list,
                ascendant=norm360(ascmc[0]),
                midheaven=norm360(ascmc[1]),
            )
