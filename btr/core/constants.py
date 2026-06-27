"""Astrological reference data shared across the whole engine.

All longitudes are sidereal degrees in [0, 360). The nine grahas used by both
Parashara and KP are the seven classical planets plus the two lunar nodes
(Rahu/Ketu). Vimshottari dasha and the KP star/sub lord scheme are both built
on the same 120-year Vimshottari proportion table, so they live here together.
"""
from __future__ import annotations

from enum import Enum

# --------------------------------------------------------------------------- #
# Planets (grahas)
# --------------------------------------------------------------------------- #


class Planet(str, Enum):
    SUN = "Sun"
    MOON = "Moon"
    MARS = "Mars"
    MERCURY = "Mercury"
    JUPITER = "Jupiter"
    VENUS = "Venus"
    SATURN = "Saturn"
    RAHU = "Rahu"
    KETU = "Ketu"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


# Two-letter short codes commonly used in KP notation.
PLANET_SHORT = {
    Planet.SUN: "Su",
    Planet.MOON: "Mo",
    Planet.MARS: "Ma",
    Planet.MERCURY: "Me",
    Planet.JUPITER: "Ju",
    Planet.VENUS: "Ve",
    Planet.SATURN: "Sa",
    Planet.RAHU: "Ra",
    Planet.KETU: "Ke",
}

# The seven classical planets always have a physical body; nodes are computed.
SEVEN_PLANETS = [
    Planet.SUN,
    Planet.MOON,
    Planet.MARS,
    Planet.MERCURY,
    Planet.JUPITER,
    Planet.VENUS,
    Planet.SATURN,
]

ALL_PLANETS = SEVEN_PLANETS + [Planet.RAHU, Planet.KETU]

# --------------------------------------------------------------------------- #
# Rasis (signs) and their lords
# --------------------------------------------------------------------------- #

SIGNS = [
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
]

# Sign index (0=Aries) -> ruling planet (classical rulerships).
SIGN_LORD = {
    0: Planet.MARS,
    1: Planet.VENUS,
    2: Planet.MERCURY,
    3: Planet.MOON,
    4: Planet.SUN,
    5: Planet.MERCURY,
    6: Planet.VENUS,
    7: Planet.MARS,
    8: Planet.JUPITER,
    9: Planet.SATURN,
    10: Planet.SATURN,
    11: Planet.JUPITER,
}

# Movable / Fixed / Dual quality of each sign (used by Pranapada rules).
# 0 = movable (chara), 1 = fixed (sthira), 2 = dual (dwiswabhava)
SIGN_QUALITY = [0, 1, 2, 0, 1, 2, 0, 1, 2, 0, 1, 2]

# --------------------------------------------------------------------------- #
# Nakshatras (27) and Vimshottari scheme
# --------------------------------------------------------------------------- #

NAKSHATRAS = [
    "Ashwini",
    "Bharani",
    "Krittika",
    "Rohini",
    "Mrigashira",
    "Ardra",
    "Punarvasu",
    "Pushya",
    "Ashlesha",
    "Magha",
    "Purva Phalguni",
    "Uttara Phalguni",
    "Hasta",
    "Chitra",
    "Swati",
    "Vishakha",
    "Anuradha",
    "Jyeshtha",
    "Mula",
    "Purva Ashadha",
    "Uttara Ashadha",
    "Shravana",
    "Dhanishta",
    "Shatabhisha",
    "Purva Bhadrapada",
    "Uttara Bhadrapada",
    "Revati",
]

# Vimshottari dasha lords in their fixed cyclic order, with mahadasha years.
# The same order + proportions drive the KP star/sub/sub-sub subdivisions.
VIMSHOTTARI_ORDER = [
    Planet.KETU,
    Planet.VENUS,
    Planet.SUN,
    Planet.MOON,
    Planet.MARS,
    Planet.RAHU,
    Planet.JUPITER,
    Planet.SATURN,
    Planet.MERCURY,
]

VIMSHOTTARI_YEARS = {
    Planet.KETU: 7,
    Planet.VENUS: 20,
    Planet.SUN: 6,
    Planet.MOON: 10,
    Planet.MARS: 7,
    Planet.RAHU: 18,
    Planet.JUPITER: 16,
    Planet.SATURN: 19,
    Planet.MERCURY: 17,
}

VIMSHOTTARI_TOTAL_YEARS = 120  # sum of the above

# Nakshatra index (0=Ashwini) -> its ruling (starting) dasha lord.
# The 27 nakshatras cycle through the 9 Vimshottari lords three times.
NAKSHATRA_LORD = [VIMSHOTTARI_ORDER[i % 9] for i in range(27)]

# Geometry.
DEG_PER_SIGN = 30.0
DEG_PER_NAKSHATRA = 360.0 / 27.0  # 13.333... degrees
DEG_PER_PADA = DEG_PER_NAKSHATRA / 4.0  # 3.333... degrees

# A solar year length used to convert Vimshottari "years" to days. KP and most
# modern Vedic software use 365.25 days. Classical texts use 360. We default to
# 365.2425 (mean Gregorian) for calendar accuracy and allow override.
SIDEREAL_YEAR_DAYS = 365.2425

# --------------------------------------------------------------------------- #
# Ayanamsa
# --------------------------------------------------------------------------- #


class Ayanamsa(str, Enum):
    LAHIRI = "lahiri"          # standard Parashara / govt. ephemeris
    KRISHNAMURTI = "kp"        # KP ayanamsa (Krishnamurti)


# --------------------------------------------------------------------------- #
# House systems
# --------------------------------------------------------------------------- #


class HouseSystem(str, Enum):
    PLACIDUS = "P"            # KP uses Placidus cusps
    WHOLE_SIGN = "W"          # common in Parashara
    EQUAL = "E"


# --------------------------------------------------------------------------- #
# Divisional charts (vargas)
# --------------------------------------------------------------------------- #

# Mapping of supported varga -> divisor. Computation logic lives in
# charts/divisional.py; this is the catalogue + the life-area each one judges.
VARGA_SIGNIFICATION = {
    "D1": "Rasi - body, overall life",
    "D9": "Navamsa - marriage, dharma, inner strength",
    "D7": "Saptamsa - children, progeny",
    "D10": "Dasamsa - career, profession, status",
    "D12": "Dwadasamsa - parents, lineage",
    "D60": "Shashtiamsa - finest karmic resolution",
}
