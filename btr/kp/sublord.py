"""The KP sub-lord scheme: Sign -> Star (Nakshatra) -> Sub -> Sub-Sub.

KP subdivides each 13°20' nakshatra into nine 'subs', each spanning the same
proportion of the nakshatra as that lord's Vimshottari years bear to 120. The
subdivision recurses: each sub splits again into nine sub-subs in the identical
proportion. The Sub lord is the single most important factor in KP - and because
the sub changes far faster than the sign or star, the ascendant sub-lord is the
linchpin of KP birth-time rectification.

The whole zodiac contains 27 x 9 = 243 subs; together with sign and star this
yields the famous KP "249 table" granularity.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.constants import (
    DEG_PER_NAKSHATRA,
    DEG_PER_SIGN,
    NAKSHATRA_LORD,
    NAKSHATRAS,
    SIGN_LORD,
    SIGNS,
    VIMSHOTTARI_ORDER,
    VIMSHOTTARI_TOTAL_YEARS,
    VIMSHOTTARI_YEARS,
    Planet,
)


def _vimshottari_spans(total: float, start_lord: Planet) -> list[tuple[Planet, float, float]]:
    """Split `total` arc into 9 Vimshottari-proportioned parts from start_lord.

    Returns a list of (lord, start_offset, end_offset) within the parent arc.
    """
    idx = VIMSHOTTARI_ORDER.index(start_lord)
    order = VIMSHOTTARI_ORDER[idx:] + VIMSHOTTARI_ORDER[:idx]
    spans = []
    cursor = 0.0
    for lord in order:
        length = total * VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_TOTAL_YEARS
        spans.append((lord, cursor, cursor + length))
        cursor += length
    return spans


@dataclass(frozen=True)
class KPLordSet:
    """The full KP lordship breakdown of a single longitude."""

    longitude: float
    sign: str
    sign_lord: Planet
    nakshatra: str
    star_lord: Planet            # nakshatra (constellation) lord
    sub_lord: Planet
    sub_sub_lord: Planet

    def signature(self) -> tuple[Planet, Planet, Planet, Planet]:
        """(sign lord, star lord, sub lord, sub-sub lord)."""
        return (self.sign_lord, self.star_lord, self.sub_lord, self.sub_sub_lord)

    def kp_notation(self) -> str:
        return (
            f"{self.sign} {self.sign_lord.value[:2]}"
            f"-{self.star_lord.value[:2]}"
            f"-{self.sub_lord.value[:2]}"
            f"-{self.sub_sub_lord.value[:2]}"
        )


def lord_set(longitude: float) -> KPLordSet:
    """Compute Sign/Star/Sub/Sub-Sub lords for a sidereal longitude."""
    lon = longitude % 360.0

    sign_index = int(lon // DEG_PER_SIGN)
    sign_lord = SIGN_LORD[sign_index]

    nak_index = int(lon // DEG_PER_NAKSHATRA)
    star_lord = NAKSHATRA_LORD[nak_index]

    # Position within the nakshatra.
    nak_start = nak_index * DEG_PER_NAKSHATRA
    offset_in_nak = lon - nak_start

    # Sub: split the nakshatra (13°20') from the star lord.
    sub_lord = None
    sub_start = sub_end = 0.0
    for lord, s, e in _vimshottari_spans(DEG_PER_NAKSHATRA, star_lord):
        if s <= offset_in_nak < e:
            sub_lord = lord
            sub_start, sub_end = s, e
            break
    if sub_lord is None:  # exactly at the end edge
        sub_lord, sub_start, sub_end = _vimshottari_spans(DEG_PER_NAKSHATRA, star_lord)[-1]

    # Sub-sub: split the sub-span from the sub lord.
    offset_in_sub = offset_in_nak - sub_start
    sub_span = sub_end - sub_start
    sub_sub_lord = None
    for lord, s, e in _vimshottari_spans(sub_span, sub_lord):
        if s <= offset_in_sub < e:
            sub_sub_lord = lord
            break
    if sub_sub_lord is None:
        sub_sub_lord = _vimshottari_spans(sub_span, sub_lord)[-1][0]

    return KPLordSet(
        longitude=lon,
        sign=SIGNS[sign_index],
        sign_lord=sign_lord,
        nakshatra=NAKSHATRAS[nak_index],
        star_lord=star_lord,
        sub_lord=sub_lord,
        sub_sub_lord=sub_sub_lord,
    )


# --------------------------------------------------------------------------- #
# Nadi Ansa (one more level of subdivision) - used for second-level precision.
# --------------------------------------------------------------------------- #


def nadi_ansa_lord(longitude: float) -> Planet:
    """Return the Nadi-Ansa lord: a further 9-fold split of the sub-sub span.

    KP rectification at the finest grade tunes the birth time until this lord is
    correct; it changes on the order of a few seconds of clock time.
    """
    lon = longitude % 360.0
    nak_index = int(lon // DEG_PER_NAKSHATRA)
    star_lord = NAKSHATRA_LORD[nak_index]
    nak_start = nak_index * DEG_PER_NAKSHATRA
    offset_in_nak = lon - nak_start

    # sub
    for lord, s, e in _vimshottari_spans(DEG_PER_NAKSHATRA, star_lord):
        if s <= offset_in_nak < e:
            sub_lord, sub_start, sub_end = lord, s, e
            break
    else:
        sub_lord, sub_start, sub_end = _vimshottari_spans(DEG_PER_NAKSHATRA, star_lord)[-1]

    # sub-sub
    offset_in_sub = offset_in_nak - sub_start
    sub_span = sub_end - sub_start
    for lord, s, e in _vimshottari_spans(sub_span, sub_lord):
        if s <= offset_in_sub < e:
            ss_lord, ss_start, ss_end = lord, s, e
            break
    else:
        ss_lord, ss_start, ss_end = _vimshottari_spans(sub_span, sub_lord)[-1]

    # nadi ansa
    offset_in_ss = offset_in_sub - ss_start
    ss_span = ss_end - ss_start
    for lord, s, e in _vimshottari_spans(ss_span, ss_lord):
        if s <= offset_in_ss < e:
            return lord
    return _vimshottari_spans(ss_span, ss_lord)[-1][0]
