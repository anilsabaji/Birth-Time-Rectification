"""Ruling Planets (RP) - the signature KP technique.

At any judgement moment (consultation, an event, or the birth instant itself)
the Ruling Planets are:

  * the lord of the weekday (day lord),
  * the Moon's sign lord, star lord and sub lord,
  * the Ascendant's sign lord, star lord and sub lord.

For rectification we tune the birth time until the birth Ascendant and Moon
(their sign/star/sub lords) fall in harmony with the RP set taken at the time of
sitting for rectification. Rahu/Ketu are added when they tenant or aspect, or
are conjoined with, a ruling planet (here: when a node sits in the sign of an
existing RP, it is promoted - a common, tractable rule).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.constants import SIGN_LORD, DEG_PER_SIGN, Planet
from ..core.ephemeris import Ephemeris, ChartGeometry
from ..core.timeutil import GeoLocation
from .special_points_bridge import weekday_lord_for_jd
from .sublord import lord_set


@dataclass(frozen=True)
class RulingPlanets:
    day_lord: Planet
    moon_sign_lord: Planet
    moon_star_lord: Planet
    moon_sub_lord: Planet
    asc_sign_lord: Planet
    asc_star_lord: Planet
    asc_sub_lord: Planet
    nodes: tuple[Planet, ...] = ()

    def as_set(self) -> set[Planet]:
        base = {
            self.day_lord,
            self.moon_sign_lord,
            self.moon_star_lord,
            self.moon_sub_lord,
            self.asc_sign_lord,
            self.asc_star_lord,
            self.asc_sub_lord,
        }
        base |= set(self.nodes)
        return base

    def ordered(self) -> list[Planet]:
        """RPs roughly strongest-first (Asc sub, Moon sub, then stars, signs)."""
        seq = [
            self.asc_sub_lord,
            self.moon_sub_lord,
            self.asc_star_lord,
            self.moon_star_lord,
            self.day_lord,
            self.asc_sign_lord,
            self.moon_sign_lord,
        ]
        out: list[Planet] = []
        for p in list(seq) + list(self.nodes):
            if p not in out:
                out.append(p)
        return out

    def describe(self) -> str:
        parts = [
            f"Day={self.day_lord.value}",
            f"Moon[{self.moon_sign_lord.value}/{self.moon_star_lord.value}/{self.moon_sub_lord.value}]",
            f"Asc[{self.asc_sign_lord.value}/{self.asc_star_lord.value}/{self.asc_sub_lord.value}]",
        ]
        if self.nodes:
            parts.append("Nodes=" + ",".join(n.value for n in self.nodes))
        return " ".join(parts)


def compute_ruling_planets(
    eph: Ephemeris,
    jd_ut: float,
    loc: GeoLocation,
    geometry: ChartGeometry | None = None,
) -> RulingPlanets:
    """Compute the Ruling Planets for the moment `jd_ut` at `loc`."""
    if geometry is None:
        geometry = eph.geometry(jd_ut, loc)

    moon = geometry.planet(Planet.MOON)
    moon_ls = lord_set(moon.longitude)
    asc_ls = lord_set(geometry.ascendant)
    day_lord = weekday_lord_for_jd(jd_ut, loc)

    # Promote a node when it shares a sign with any existing RP.
    base_rps = {
        day_lord,
        moon_ls.sign_lord,
        moon_ls.star_lord,
        moon_ls.sub_lord,
        asc_ls.sign_lord,
        asc_ls.star_lord,
        asc_ls.sub_lord,
    }
    nodes: list[Planet] = []
    for node in (Planet.RAHU, Planet.KETU):
        node_sign = int(geometry.planet(node).longitude // DEG_PER_SIGN)
        node_sign_lord = SIGN_LORD[node_sign]
        if node_sign_lord in base_rps:
            nodes.append(node)

    return RulingPlanets(
        day_lord=day_lord,
        moon_sign_lord=moon_ls.sign_lord,
        moon_star_lord=moon_ls.star_lord,
        moon_sub_lord=moon_ls.sub_lord,
        asc_sign_lord=asc_ls.sign_lord,
        asc_star_lord=asc_ls.star_lord,
        asc_sub_lord=asc_ls.sub_lord,
        nodes=tuple(nodes),
    )
