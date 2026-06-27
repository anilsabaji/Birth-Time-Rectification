"""Cuspal Sub-Lords (CSL) and the KP cusp/house model.

In KP each house cusp has a sub-lord (its 'CSL'). Whether a house's matters
fructify - and in which direction - is judged primarily from the CSL's own
significations. Because cusps move ~1°/4min, the set of 12 CSLs is extremely
sensitive to birth time, which is what makes them a strong rectification anchor.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.constants import SIGN_LORD, DEG_PER_SIGN, Planet
from ..core.ephemeris import ChartGeometry
from .sublord import KPLordSet, lord_set


@dataclass(frozen=True)
class CuspInfo:
    house: int                 # 1..12
    longitude: float
    lords: KPLordSet

    @property
    def sub_lord(self) -> Planet:
        return self.lords.sub_lord

    @property
    def sign_lord(self) -> Planet:
        return self.lords.sign_lord


class KPCusps:
    """Holds the KP lordship breakdown of all 12 cusps for one chart."""

    def __init__(self, geometry: ChartGeometry) -> None:
        self.geometry = geometry
        self.cusps: dict[int, CuspInfo] = {}
        for h in range(1, 13):
            lon = geometry.cusps[h - 1]
            self.cusps[h] = CuspInfo(house=h, longitude=lon, lords=lord_set(lon))

    def cusp(self, house: int) -> CuspInfo:
        return self.cusps[house]

    def cuspal_sub_lord(self, house: int) -> Planet:
        return self.cusps[house].sub_lord

    def house_sign_index(self, house: int) -> int:
        return int(self.cusps[house].longitude // DEG_PER_SIGN)

    def all_sub_lords(self) -> dict[int, Planet]:
        return {h: c.sub_lord for h, c in self.cusps.items()}
