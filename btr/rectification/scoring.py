"""Per-method scoring functions.

Each scorer takes the candidate's :class:`CandidateCharts` plus the
:class:`RectificationContext` and returns a :class:`MethodScore` in [0, 1] with a
human-readable explanation. The engine combines them with configurable weights.

Implemented methods (mapped to the two systems):

  Parashara
    * dasha_event_correlation  - running Maha/Antar/Pratyantar lords must
      signify the houses of each confirmed event.
    * varga_consistency        - the event's dasha lords must also activate the
      event houses inside the relevant divisional chart (D9/D7/D10/D12...).
    * pranapada_check          - Pranapada should fall in a benefic house from
      the Lagna (4/5/9/10/11) - a classic validity test.
    * gulika_check             - Gulika's KP sub-lord should relate to the
      running dasha / event houses.
    * lagna_trait_match        - Ascendant sign/nakshatra vs. stated traits.

  KP
    * ruling_planets_match     - birth Asc & Moon (sign/star/sub lords) vs. the
      Ruling Planets taken at the rectification moment.
    * cuspal_significator_event- the event's cuspal sub-lord must signify the
      event houses and the dasha lords at the event must be its significators.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..core.constants import ALL_PLANETS, DEG_PER_SIGN, SIGN_LORD, SIGNS, Planet
from ..charts.divisional import varga_sign_index
from ..kp.sublord import lord_set
from .charts_bundle import CandidateCharts
from .context import RectificationContext
from .events import LifeEvent


@dataclass
class MethodScore:
    name: str
    system: str          # "KP" or "Parashara"
    score: float         # 0..1
    weight: float
    detail: str = ""
    per_event: list[str] = field(default_factory=list)

    @property
    def weighted(self) -> float:
        return max(0.0, min(1.0, self.score)) * self.weight


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _activation_fraction(planets: set[Planet], houses: set[int], sig) -> float:
    """Fraction of `planets` that signify at least one of `houses`."""
    if not planets:
        return 0.0
    hits = sum(1 for p in planets if sig.planet_significations(p) & houses)
    return hits / len(planets)


def _dasha_lords_at(bundle: CandidateCharts, event: LifeEvent, tz: float) -> tuple[Planet, ...]:
    jd = event.julian_day_ut(tz)
    return bundle.dasha.lords_at(jd)


# --------------------------------------------------------------------------- #
# KP: Ruling Planets
# --------------------------------------------------------------------------- #


def score_ruling_planets(bundle: CandidateCharts, ctx: RectificationContext) -> MethodScore:
    rp = ctx.consultation_ruling_planets
    weight = ctx.method_weights.get("ruling_planets_match", 0.0)
    if rp is None:
        return MethodScore("ruling_planets_match", "KP", 0.0, 0.0,
                           "skipped (no consultation moment provided)")

    rp_set = rp.as_set()
    asc_ls = lord_set(bundle.kp_geo.ascendant)
    moon_ls = lord_set(bundle.kp_geo.planet(Planet.MOON).longitude)

    # Sub lords carry the most weight, then star, then sign.
    checks = [
        ("Asc-sub", asc_ls.sub_lord, 3.0),
        ("Moon-sub", moon_ls.sub_lord, 3.0),
        ("Asc-star", asc_ls.star_lord, 2.0),
        ("Moon-star", moon_ls.star_lord, 2.0),
        ("Asc-sign", asc_ls.sign_lord, 1.0),
        ("Moon-sign", moon_ls.sign_lord, 1.0),
    ]
    got = sum(w for _, lord, w in checks if lord in rp_set)
    total = sum(w for *_, w in checks)
    score = got / total

    matched = [f"{name}={lord.value}{'*' if lord in rp_set else ''}"
               for name, lord, _ in checks]
    detail = (f"RP@consult={{{','.join(p.value for p in rp.ordered())}}}; "
              f"matches: {', '.join(matched)}")
    return MethodScore("ruling_planets_match", "KP", score, weight, detail)


# --------------------------------------------------------------------------- #
# KP: cuspal sub-lord + significator event test
# --------------------------------------------------------------------------- #


def score_kp_cuspal_events(bundle: CandidateCharts, ctx: RectificationContext) -> MethodScore:
    weight = ctx.method_weights.get("cuspal_significator_event", 0.0)
    if not ctx.events:
        return MethodScore("cuspal_significator_event", "KP", 0.0, 0.0, "no events")

    sig = bundle.kp_significators
    cusps = bundle.kp_cusps
    per_event: list[str] = []
    total = 0.0
    for ev in ctx.events:
        houses = set(ev.resolved_houses())
        if not houses:
            continue
        primary_house = ev.resolved_houses()[0]
        csl = cusps.cuspal_sub_lord(primary_house)
        csl_signifies = bool(sig.planet_significations(csl) & houses)

        dasha_lords = set(_dasha_lords_at(bundle, ev, ctx.birth_tz))
        dasha_frac = _activation_fraction(dasha_lords, houses, sig)

        ev_score = (0.5 if csl_signifies else 0.0) + 0.5 * dasha_frac
        total += ev_score * ev.weight
        per_event.append(
            f"{ev.event_type.value}@{ev.event_date}: CSL(H{primary_house})="
            f"{csl.value}{'+' if csl_signifies else '-'} "
            f"dasha[{'/'.join(p.value for p in dasha_lords)}] act={dasha_frac:.2f}"
        )

    wsum = sum(ev.weight for ev in ctx.events if ev.resolved_houses())
    score = total / wsum if wsum else 0.0
    return MethodScore("cuspal_significator_event", "KP", score, weight,
                       "CSL must signify event houses; dasha lords must be significators",
                       per_event)


# --------------------------------------------------------------------------- #
# Parashara: dasha-event correlation
# --------------------------------------------------------------------------- #


def score_dasha_correlation(bundle: CandidateCharts, ctx: RectificationContext) -> MethodScore:
    weight = ctx.method_weights.get("dasha_event_correlation", 0.0)
    if not ctx.events:
        return MethodScore("dasha_event_correlation", "Parashara", 0.0, 0.0, "no events")

    sig = bundle.parashara_significators
    per_event: list[str] = []
    total = 0.0
    wsum = 0.0
    for ev in ctx.events:
        houses = set(ev.resolved_houses())
        if not houses:
            continue
        lords = _dasha_lords_at(bundle, ev, ctx.birth_tz)
        if not lords:
            continue
        # Weight Maha highest, then antar, then pratyantar.
        level_weights = [3.0, 2.0, 1.0][: len(lords)]
        got = sum(
            lw for lord, lw in zip(lords, level_weights)
            if sig.planet_significations(lord) & houses
        )
        frac = got / sum(level_weights)
        total += frac * ev.weight
        wsum += ev.weight
        per_event.append(
            f"{ev.event_type.value}@{ev.event_date}: "
            f"dasha[{'/'.join(p.value for p in lords)}] "
            f"signify {sorted(houses)} -> {frac:.2f}"
        )
    score = total / wsum if wsum else 0.0
    return MethodScore("dasha_event_correlation", "Parashara", score, weight,
                       "running Maha/Antar/Pratyantar lords should signify event houses",
                       per_event)


# --------------------------------------------------------------------------- #
# Parashara: divisional (varga) consistency
# --------------------------------------------------------------------------- #


def _varga_house_of(planet_long: float, lagna_long: float, varga: str) -> int:
    lagna_sign = varga_sign_index(lagna_long, varga)
    p_sign = varga_sign_index(planet_long, varga)
    return ((p_sign - lagna_sign) % 12) + 1


def _varga_owner_of_house(house: int, lagna_long: float, varga: str) -> Planet:
    lagna_sign = varga_sign_index(lagna_long, varga)
    sign_on_house = (lagna_sign + house - 1) % 12
    return SIGN_LORD[sign_on_house]


def score_varga_consistency(bundle: CandidateCharts, ctx: RectificationContext) -> MethodScore:
    weight = ctx.method_weights.get("varga_consistency", 0.0)
    events = [ev for ev in ctx.events if ev.primary_varga() and ev.resolved_houses()]
    if not events:
        return MethodScore("varga_consistency", "Parashara", 0.0, 0.0,
                           "no events with a divisional mapping")

    geo = bundle.lahiri_geo
    lagna_long = geo.ascendant
    per_event: list[str] = []
    total = 0.0
    wsum = 0.0
    for ev in events:
        varga = ev.primary_varga()
        houses = set(ev.resolved_houses())
        lords = _dasha_lords_at(bundle, ev, ctx.birth_tz)
        if not lords:
            continue
        # In the varga: a dasha lord 'activates' an event house if it occupies
        # or owns one of those houses.
        owners = {h: _varga_owner_of_house(h, lagna_long, varga) for h in houses}
        owner_planets = set(owners.values())
        occupant_hit = any(
            _varga_house_of(geo.planet(lord).longitude, lagna_long, varga) in houses
            for lord in lords
        )
        owner_hit = any(lord in owner_planets for lord in lords)
        ev_score = 0.0
        if occupant_hit:
            ev_score += 0.5
        if owner_hit:
            ev_score += 0.5
        total += ev_score * ev.weight
        wsum += ev.weight
        per_event.append(
            f"{ev.event_type.value} [{varga}] occ={occupant_hit} own={owner_hit} -> {ev_score:.2f}"
        )
    score = total / wsum if wsum else 0.0
    return MethodScore("varga_consistency", "Parashara", score, weight,
                       "dasha lords at the event should activate event houses in the varga",
                       per_event)


# --------------------------------------------------------------------------- #
# Parashara: Pranapada validity
# --------------------------------------------------------------------------- #

_BENEFIC_PP_HOUSES = {1, 4, 5, 7, 9, 10, 11}


def score_pranapada(bundle: CandidateCharts, ctx: RectificationContext) -> MethodScore:
    weight = ctx.method_weights.get("pranapada_check", 0.0)
    geo = bundle.lahiri_geo
    pp = bundle.pranapada
    house = geo.house_of(pp.longitude, whole_sign=True)
    score = 1.0 if house in _BENEFIC_PP_HOUSES else 0.2
    detail = (f"Pranapada {pp.dms()} in bhava {house} "
              f"({'auspicious' if house in _BENEFIC_PP_HOUSES else 'weak'})")
    return MethodScore("pranapada_check", "Parashara", score, weight, detail)


# --------------------------------------------------------------------------- #
# Parashara: Gulika sub-lord relevance (KP-flavoured cross check)
# --------------------------------------------------------------------------- #


def score_gulika(bundle: CandidateCharts, ctx: RectificationContext) -> MethodScore:
    weight = ctx.method_weights.get("gulika_check", 0.0)
    if not ctx.events:
        return MethodScore("gulika_check", "Parashara", 0.0, 0.0, "no events")
    gulika = bundle.gulika.gulika
    g_ls = lord_set(gulika.longitude)
    sig = bundle.kp_significators
    all_event_houses: set[int] = set()
    for ev in ctx.events:
        all_event_houses |= set(ev.resolved_houses())
    if not all_event_houses:
        return MethodScore("gulika_check", "Parashara", 0.0, 0.0, "no event houses")
    relates = bool(sig.planet_significations(g_ls.sub_lord) & all_event_houses)
    score = 1.0 if relates else 0.3
    detail = (f"Gulika {gulika.dms()} sub-lord {g_ls.sub_lord.value} "
              f"{'relates to' if relates else 'unrelated to'} event houses {sorted(all_event_houses)}")
    return MethodScore("gulika_check", "Parashara", score, weight, detail)


# --------------------------------------------------------------------------- #
# Parashara/KP: Lagna trait match
# --------------------------------------------------------------------------- #


def score_lagna_traits(bundle: CandidateCharts, ctx: RectificationContext) -> MethodScore:
    weight = ctx.method_weights.get("lagna_trait_match", 0.0)
    if not (ctx.expected_lagna_signs or ctx.expected_lagna_nakshatra):
        return MethodScore("lagna_trait_match", "Parashara", 0.0, 0.0,
                           "skipped (no expected lagna sign/nakshatra given)")
    asc = bundle.lahiri_geo.asc_position()
    parts = []
    score_terms = []
    if ctx.expected_lagna_signs:
        ok = asc.sign in ctx.expected_lagna_signs
        score_terms.append(1.0 if ok else 0.0)
        parts.append(f"sign {asc.sign} {'OK' if ok else 'NO'}")
    if ctx.expected_lagna_nakshatra:
        ok = asc.nakshatra == ctx.expected_lagna_nakshatra
        score_terms.append(1.0 if ok else 0.0)
        parts.append(f"nak {asc.nakshatra} {'OK' if ok else 'NO'}")
    score = sum(score_terms) / len(score_terms)
    return MethodScore("lagna_trait_match", "Parashara", score, weight,
                       f"Asc {asc.dms()}: " + ", ".join(parts))


# --------------------------------------------------------------------------- #
# registry
# --------------------------------------------------------------------------- #

ALL_SCORERS = [
    score_ruling_planets,
    score_kp_cuspal_events,
    score_dasha_correlation,
    score_varga_consistency,
    score_pranapada,
    score_gulika,
    score_lagna_traits,
]
