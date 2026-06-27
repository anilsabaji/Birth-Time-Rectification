"""KP significators: which planets 'signify' which houses, and vice-versa.

KP judges events through significators. The classical four-fold strength order
for the significators of a house is:

  A. Planets in the *star* (nakshatra) of any planet occupying the house.
  B. Planets occupying the house.
  C. Planets in the *star* of the owner (sign-lord) of the house.
  D. The owner of the house.

A planet, conversely, *signifies* the houses it occupies and owns, plus the
houses occupied/owned by the planet in whose star it sits (the "star-lord
transfer", which dominates in KP). Rahu/Ketu additionally act as agents of their
sign-dispositor and of planets conjoined with them.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.constants import ALL_PLANETS, DEG_PER_SIGN, SIGN_LORD, Planet
from ..core.ephemeris import ChartGeometry
from .cuspal import KPCusps
from .sublord import lord_set


@dataclass
class SignificatorModel:
    geometry: ChartGeometry
    cusps: KPCusps
    use_placidus: bool = True

    # filled in __post_init__
    occupied_house: dict[Planet, int] = field(default_factory=dict)
    star_lord_of: dict[Planet, Planet] = field(default_factory=dict)
    occupants_of_house: dict[int, list[Planet]] = field(default_factory=dict)
    owner_of_house: dict[int, Planet] = field(default_factory=dict)
    houses_owned_by: dict[Planet, set[int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        g = self.geometry
        for h in range(1, 13):
            self.occupants_of_house[h] = []
        for p in ALL_PLANETS:
            pos = g.planet(p)
            h = g.house_of(pos.longitude, whole_sign=not self.use_placidus)
            self.occupied_house[p] = h
            self.occupants_of_house[h].append(p)
            self.star_lord_of[p] = lord_set(pos.longitude).star_lord

        # House ownership: owner of a house = sign-lord of the sign on its cusp.
        for h in range(1, 13):
            sign_idx = int(g.cusps[h - 1] // DEG_PER_SIGN)
            owner = SIGN_LORD[sign_idx]
            self.owner_of_house[h] = owner
            self.houses_owned_by.setdefault(owner, set()).add(h)
        for p in ALL_PLANETS:
            self.houses_owned_by.setdefault(p, set())

    # ------------------------------------------------------------------ #
    # planet -> houses it signifies
    # ------------------------------------------------------------------ #

    def _base_houses(self, planet: Planet) -> set[int]:
        """Houses a planet signifies directly: occupancy + ownership."""
        houses = {self.occupied_house[planet]}
        houses |= self.houses_owned_by.get(planet, set())
        return houses

    def planet_significations(self, planet: Planet) -> set[int]:
        """Full set of houses a planet signifies (star-lord transfer + nodes)."""
        houses = set(self._base_houses(planet))
        # Star-lord transfer: the planet primarily gives the results of the
        # planet in whose star it is placed.
        star_lord = self.star_lord_of[planet]
        houses |= self._base_houses(star_lord)

        # Node agency: Rahu/Ketu represent their sign-dispositor and conjunctions.
        if planet in (Planet.RAHU, Planet.KETU):
            sign_idx = int(self.geometry.planet(planet).longitude // DEG_PER_SIGN)
            disp = SIGN_LORD[sign_idx]
            houses |= self._base_houses(disp)
            houses |= self._base_houses(self.star_lord_of[disp])
            # conjunct planets (same house)
            for co in self.occupants_of_house[self.occupied_house[planet]]:
                if co != planet:
                    houses |= self._base_houses(co)
        return houses

    # ------------------------------------------------------------------ #
    # house -> significator planets, by strength level
    # ------------------------------------------------------------------ #

    def significators_of(self, house: int) -> dict[str, list[Planet]]:
        occupants = list(self.occupants_of_house[house])
        owner = self.owner_of_house[house]

        level_a = [
            p for p in ALL_PLANETS
            if any(self.star_lord_of[p] == occ for occ in occupants)
        ]
        level_b = list(occupants)
        level_c = [p for p in ALL_PLANETS if self.star_lord_of[p] == owner]
        level_d = [owner]

        return {"A": level_a, "B": level_b, "C": level_c, "D": level_d}

    def ranked_significators(self, house: int) -> list[Planet]:
        """Flatten significators strongest-first, de-duplicated."""
        levels = self.significators_of(house)
        ordered: list[Planet] = []
        for key in ("A", "B", "C", "D"):
            for p in levels[key]:
                if p not in ordered:
                    ordered.append(p)
        return ordered

    def planets_signifying(self, houses: set[int]) -> set[Planet]:
        """All planets that signify *any* of the given houses."""
        return {
            p for p in ALL_PLANETS
            if self.planet_significations(p) & houses
        }
