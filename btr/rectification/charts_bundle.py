"""A per-candidate-time bundle of every chart artefact the scorers need.

Building these objects is the expensive part of a rectification scan, so we
compute them once per candidate instant and hand the bundle to every scorer.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

from ..charts.special_points import gulika_mandi, pranapada
from ..core.constants import Ayanamsa, HouseSystem, Planet
from ..core.ephemeris import ChartGeometry, Ephemeris
from ..core.timeutil import BirthMoment
from ..dasha.vimshottari import VimshottariDasha
from ..kp.cuspal import KPCusps
from ..kp.ruling_planets import RulingPlanets, compute_ruling_planets
from ..kp.significators import SignificatorModel


@dataclass
class CandidateCharts:
    """All derived charts/objects for one candidate birth instant."""

    moment: BirthMoment
    lahiri_eph: Ephemeris
    kp_eph: Ephemeris

    @cached_property
    def jd(self) -> float:
        return self.moment.julian_day_ut()

    # ---- geometries ----------------------------------------------------- #
    @cached_property
    def lahiri_geo(self) -> ChartGeometry:
        return self.lahiri_eph.geometry(self.jd, self.moment.location)

    @cached_property
    def kp_geo(self) -> ChartGeometry:
        return self.kp_eph.geometry(self.jd, self.moment.location)

    # ---- dasha ---------------------------------------------------------- #
    @cached_property
    def dasha(self) -> VimshottariDasha:
        moon = self.lahiri_geo.planet(Planet.MOON)
        return VimshottariDasha(moon.longitude, self.jd, depth=3)

    # ---- KP artefacts (use KP ayanamsa + Placidus) ---------------------- #
    @cached_property
    def kp_cusps(self) -> KPCusps:
        return KPCusps(self.kp_geo)

    @cached_property
    def kp_significators(self) -> SignificatorModel:
        return SignificatorModel(self.kp_geo, self.kp_cusps, use_placidus=True)

    @cached_property
    def ruling_planets(self) -> RulingPlanets:
        return compute_ruling_planets(self.kp_eph, self.jd, self.moment.location, self.kp_geo)

    # ---- Parashara significators (Lahiri, whole-sign bhava) ------------- #
    @cached_property
    def parashara_significators(self) -> SignificatorModel:
        cusps = KPCusps(self.lahiri_geo)  # only used for ownership lookups
        return SignificatorModel(self.lahiri_geo, cusps, use_placidus=False)

    # ---- special points ------------------------------------------------- #
    @cached_property
    def pranapada(self):
        return pranapada(self.lahiri_eph, self.jd, self.moment.location)

    @cached_property
    def gulika(self):
        return gulika_mandi(self.lahiri_eph, self.jd, self.moment.location)


def build_candidate(moment: BirthMoment) -> CandidateCharts:
    return CandidateCharts(
        moment=moment,
        lahiri_eph=Ephemeris(Ayanamsa.LAHIRI, HouseSystem.PLACIDUS),
        kp_eph=Ephemeris(Ayanamsa.KRISHNAMURTI, HouseSystem.PLACIDUS),
    )
