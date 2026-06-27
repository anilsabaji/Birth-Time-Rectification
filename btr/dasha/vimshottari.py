"""Vimshottari Dasha: the 120-year nakshatra-based period system.

The Moon's sidereal longitude fixes the birth nakshatra; the fraction of that
nakshatra already traversed fixes how much of the first mahadasha has elapsed at
birth. From there the Maha -> Antar -> Pratyantar tree subdivides each period in
the fixed Vimshottari proportion.

This is used by both systems during rectification:
  * Parashara - which Maha/Antar lord runs when a life event happened.
  * KP        - dasha lords participate as significators of an event.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.constants import (
    DEG_PER_NAKSHATRA,
    NAKSHATRA_LORD,
    SIDEREAL_YEAR_DAYS,
    VIMSHOTTARI_ORDER,
    VIMSHOTTARI_TOTAL_YEARS,
    VIMSHOTTARI_YEARS,
    Planet,
)
from ..core.timeutil import datetime_from_jd_ut

# datetime import only for typing the helper return
from datetime import datetime


def _order_starting_at(lord: Planet) -> list[Planet]:
    idx = VIMSHOTTARI_ORDER.index(lord)
    return VIMSHOTTARI_ORDER[idx:] + VIMSHOTTARI_ORDER[:idx]


@dataclass
class DashaPeriod:
    """One node in the dasha tree (maha/antar/pratyantar/...)."""

    lords: tuple[Planet, ...]      # e.g. (Venus, Saturn) = Venus maha / Saturn antar
    start_jd: float
    end_jd: float
    children: list["DashaPeriod"] = field(default_factory=list)

    @property
    def level(self) -> int:
        return len(self.lords)

    @property
    def lord(self) -> Planet:
        return self.lords[-1]

    def contains(self, jd: float) -> bool:
        return self.start_jd <= jd < self.end_jd

    def lord_chain_str(self) -> str:
        return " / ".join(p.value for p in self.lords)

    def start_dt(self, tz: float = 0.0) -> datetime:
        return datetime_from_jd_ut(self.start_jd, tz)

    def end_dt(self, tz: float = 0.0) -> datetime:
        return datetime_from_jd_ut(self.end_jd, tz)


class VimshottariDasha:
    """Builds and queries the Vimshottari dasha tree for a birth Moon."""

    def __init__(
        self,
        moon_longitude: float,
        birth_jd: float,
        year_length_days: float = SIDEREAL_YEAR_DAYS,
        depth: int = 3,
    ) -> None:
        """
        :param moon_longitude: sidereal longitude of the Moon at birth.
        :param birth_jd: Julian Day (UT) of birth.
        :param depth: 1=maha, 2=+antar, 3=+pratyantar, etc.
        """
        self.moon_longitude = moon_longitude % 360.0
        self.birth_jd = birth_jd
        self.year_length_days = year_length_days
        self.depth = depth
        self.nakshatra_index = int(self.moon_longitude // DEG_PER_NAKSHATRA)
        self.start_lord = NAKSHATRA_LORD[self.nakshatra_index]
        self._mahadashas: list[DashaPeriod] = []
        self._build()

    # ---- balance of dasha at birth -------------------------------------- #

    def balance_fraction(self) -> float:
        """Fraction of the *first* mahadasha already elapsed at birth (0..1)."""
        pos_in_nak = self.moon_longitude % DEG_PER_NAKSHATRA
        return pos_in_nak / DEG_PER_NAKSHATRA

    def _days(self, years: float) -> float:
        return years * self.year_length_days

    # ---- tree construction ---------------------------------------------- #

    def _subdivide(
        self,
        parent_lords: tuple[Planet, ...],
        start_jd: float,
        total_days: float,
        level_remaining: int,
    ) -> list[DashaPeriod]:
        if level_remaining <= 0:
            return []
        # Sub-periods within a period start from the parent's own lord and run
        # in Vimshottari order, each proportional to its mahadasha years.
        order = _order_starting_at(parent_lords[-1])
        periods: list[DashaPeriod] = []
        cursor = start_jd
        for lord in order:
            span = total_days * VIMSHOTTARI_YEARS[lord] / VIMSHOTTARI_TOTAL_YEARS
            node = DashaPeriod(
                lords=parent_lords + (lord,),
                start_jd=cursor,
                end_jd=cursor + span,
            )
            node.children = self._subdivide(
                node.lords, cursor, span, level_remaining - 1
            )
            periods.append(node)
            cursor += span
        return periods

    def _build(self) -> None:
        order = _order_starting_at(self.start_lord)
        elapsed_fraction = self.balance_fraction()

        # The first mahadasha is partly consumed before birth, so back up the
        # timeline start to its notional beginning, then the birth sits inside.
        first_full_days = self._days(VIMSHOTTARI_YEARS[self.start_lord])
        first_start_jd = self.birth_jd - elapsed_fraction * first_full_days

        cursor = first_start_jd
        for lord in order:
            span = self._days(VIMSHOTTARI_YEARS[lord])
            node = DashaPeriod(
                lords=(lord,),
                start_jd=cursor,
                end_jd=cursor + span,
            )
            node.children = self._subdivide((lord,), cursor, span, self.depth - 1)
            self._mahadashas.append(node)
            cursor += span

    # ---- queries --------------------------------------------------------- #

    @property
    def mahadashas(self) -> list[DashaPeriod]:
        return self._mahadashas

    def at(self, jd: float) -> list[DashaPeriod]:
        """Return the nested running periods [maha, antar, pratyantar, ...]."""
        result: list[DashaPeriod] = []
        nodes = self._mahadashas
        while nodes:
            current = next((n for n in nodes if n.contains(jd)), None)
            if current is None:
                break
            result.append(current)
            nodes = current.children
        return result

    def lords_at(self, jd: float) -> tuple[Planet, ...]:
        """The lord chain running at `jd`, e.g. (Venus, Saturn, Mercury)."""
        running = self.at(jd)
        return tuple(p.lord for p in running)

    def balance_string(self, tz: float = 0.0) -> str:
        first = self._mahadashas[0]
        remaining_days = first.end_jd - self.birth_jd
        years = remaining_days / self.year_length_days
        return (
            f"Birth Moon in nakshatra lord {self.start_lord.value}; "
            f"balance of {self.start_lord.value} mahadasha = {years:.2f} years "
            f"(ends {first.end_dt(tz).date()})"
        )
