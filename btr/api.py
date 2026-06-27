"""High-level convenience API for the BTR engine.

This is the friendly entry point most users want: build a chart report for a
single time, or rectify a birth time against events - without touching the
low-level modules directly.
"""
from __future__ import annotations

from dataclasses import dataclass

from .charts.divisional import varga_sign_index
from .charts.special_points import gulika_mandi, pranapada
from .core.constants import ALL_PLANETS, SIGNS, Ayanamsa, HouseSystem, Planet
from .core.ephemeris import Ephemeris
from .core.timeutil import BirthMoment, GeoLocation
from .dasha.vimshottari import VimshottariDasha
from .kp.cuspal import KPCusps
from .kp.ruling_planets import compute_ruling_planets
from .kp.significators import SignificatorModel
from .kp.sublord import lord_set
from .rectification.context import RectificationContext
from .rectification.engine import RectificationReport, Rectifier, score_moment


def make_birth_moment(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: float,
    tz_offset_hours: float,
    latitude: float,
    longitude: float,
    place_name: str = "",
) -> BirthMoment:
    loc = GeoLocation(latitude, longitude, name=place_name)
    return BirthMoment(year, month, day, hour, minute, second, tz_offset_hours, loc)


def chart_report(moment: BirthMoment, ayanamsa: Ayanamsa = Ayanamsa.KRISHNAMURTI) -> str:
    """A full single-time chart dump: planets, KP lordships, cusps, dasha, points."""
    eph = Ephemeris(ayanamsa, HouseSystem.PLACIDUS)
    jd = moment.julian_day_ut()
    geo = eph.geometry(jd, moment.location)
    cusps = KPCusps(geo)
    sig = SignificatorModel(geo, cusps, use_placidus=True)
    moon = geo.planet(Planet.MOON)
    dasha = VimshottariDasha(moon.longitude, jd, depth=2)
    rp = compute_ruling_planets(eph, jd, moment.location, geo)
    pp = pranapada(eph, jd, moment.location)
    gm = gulika_mandi(eph, jd, moment.location)

    lines = []
    lines.append("=" * 68)
    lines.append(f"CHART  {moment.label()}  (TZ {moment.tz_offset_hours:+.2f})  "
                 f"ayanamsa={ayanamsa.value} ({geo.ayanamsa_value:.4f})")
    lines.append(f"Place  {moment.location.name} "
                 f"({moment.location.latitude:.4f}, {moment.location.longitude:.4f})")
    lines.append("-" * 68)
    asc_ls = lord_set(geo.ascendant)
    lines.append(f"Ascendant : {geo.asc_position().dms():28s} {asc_ls.kp_notation()}")
    lines.append("")
    lines.append(f"{'Planet':9s} {'Position':28s} {'Nak(Pada)':18s} KP(Sign-Star-Sub-SubSub)")
    for p in ALL_PLANETS:
        pos = geo.planet(p)
        ls = lord_set(pos.longitude)
        retro = " (R)" if pos.is_retrograde else ""
        lines.append(
            f"{p.value:9s} {pos.dms():28s} "
            f"{pos.nakshatra+'('+str(pos.pada)+')':18s} {ls.kp_notation()}{retro}"
        )
    lines.append("")
    lines.append("Cuspal sub-lords:")
    for h in range(1, 13):
        c = cusps.cusp(h)
        lines.append(f"  H{h:<2d} {SIGNS[int(c.longitude//30)]:12s} CSL={c.sub_lord.value}")
    lines.append("")
    lines.append("Special points:")
    lines.append(f"  Pranapada : {pp.dms()}")
    lines.append(f"  Gulika    : {gm.gulika.dms()}")
    lines.append(f"  Mandi     : {gm.mandi.dms()}")
    lines.append("")
    lines.append("Ruling Planets (at birth): " + rp.describe())
    lines.append("")
    lines.append(dasha.balance_string(moment.tz_offset_hours))
    lines.append("Mahadasha sequence:")
    for md in dasha.mahadashas[:9]:
        lines.append(f"  {md.lord.value:9s} {md.start_dt(moment.tz_offset_hours).date()} "
                     f"-> {md.end_dt(moment.tz_offset_hours).date()}")
    lines.append("=" * 68)
    return "\n".join(lines)


def rectify(
    base_moment: BirthMoment,
    context: RectificationContext,
    window_minutes: float = 30.0,
    coarse_step_seconds: float = 240.0,
    fine_step_seconds: float = 10.0,
) -> RectificationReport:
    """Run a full rectification scan and return the ranked report."""
    return Rectifier(context).rectify(
        base_moment,
        window_minutes=window_minutes,
        coarse_step_seconds=coarse_step_seconds,
        fine_step_seconds=fine_step_seconds,
    )
