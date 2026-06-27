"""The rectification engine: scan candidate birth times and rank them.

Strategy (two-pass, coarse-to-fine):

  1. **Coarse scan** across the user's uncertainty window at a coarse step
     (e.g. every 4 minutes - roughly one KP sub-lord change of the Ascendant)
     to find promising neighbourhoods.
  2. **Fine scan** around the best coarse candidates at a fine step (e.g. every
     few seconds, approaching Nadi-Ansa precision) to pinpoint the time.

Every candidate is scored by all enabled methods; scores are combined with the
configured weights into a single 0..100 confidence number.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..core.timeutil import BirthMoment
from .charts_bundle import build_candidate
from .context import RectificationContext
from .scoring import ALL_SCORERS, MethodScore


@dataclass
class CandidateResult:
    moment: BirthMoment
    total_score: float                       # 0..100
    method_scores: list[MethodScore] = field(default_factory=list)

    @property
    def time_label(self) -> str:
        return self.moment.local_datetime().strftime("%Y-%m-%d %H:%M:%S")

    def summary(self) -> str:
        lines = [f"{self.time_label}  ->  {self.total_score:.1f}/100"]
        for ms in self.method_scores:
            if ms.weight <= 0:
                continue
            lines.append(
                f"    [{ms.system:9s}] {ms.name:26s} "
                f"{ms.score*100:5.1f}%  (w={ms.weight})  {ms.detail}"
            )
            for pe in ms.per_event:
                lines.append(f"        - {pe}")
        return "\n".join(lines)


def score_moment(moment: BirthMoment, ctx: RectificationContext) -> CandidateResult:
    """Score a single candidate birth moment with all enabled methods."""
    bundle = build_candidate(moment)
    method_scores: list[MethodScore] = [scorer(bundle, ctx) for scorer in ALL_SCORERS]

    total_w = sum(ms.weight for ms in method_scores)
    weighted = sum(ms.weighted for ms in method_scores)
    total = (weighted / total_w * 100.0) if total_w > 0 else 0.0
    return CandidateResult(moment=moment, total_score=total, method_scores=method_scores)


@dataclass
class RectificationReport:
    base_moment: BirthMoment
    ranked: list[CandidateResult]
    coarse_step_seconds: float
    fine_step_seconds: float
    window_seconds: float

    @property
    def best(self) -> CandidateResult:
        return self.ranked[0]

    def top(self, n: int = 5) -> list[CandidateResult]:
        return self.ranked[:n]

    def render(self, n: int = 5) -> str:
        lines = [
            "=" * 72,
            "BIRTH TIME RECTIFICATION REPORT",
            "=" * 72,
            f"Given time     : {self.base_moment.label()}  "
            f"(TZ {self.base_moment.tz_offset_hours:+.2f})",
            f"Place          : {self.base_moment.location.name or ''} "
            f"({self.base_moment.location.latitude:.4f}, "
            f"{self.base_moment.location.longitude:.4f})",
            f"Search window  : +/- {self.window_seconds/60:.0f} min  |  "
            f"coarse {self.coarse_step_seconds:.0f}s, fine {self.fine_step_seconds:.0f}s",
            "-" * 72,
            f"BEST RECTIFIED TIME: {self.best.time_label}  "
            f"(confidence {self.best.total_score:.1f}/100)",
            "-" * 72,
            f"Top {n} candidates:",
        ]
        for i, cand in enumerate(self.top(n), 1):
            lines.append(f"\n#{i}  {cand.summary()}")
        lines.append("=" * 72)
        return "\n".join(lines)


class Rectifier:
    """Coarse-to-fine birth-time rectification driver."""

    def __init__(self, context: RectificationContext) -> None:
        self.ctx = context

    def _scan_range(
        self,
        base: BirthMoment,
        start_offset: float,
        end_offset: float,
        step: float,
    ) -> list[CandidateResult]:
        results: list[CandidateResult] = []
        offset = start_offset
        # Guard against pathological step values.
        step = max(step, 1.0)
        while offset <= end_offset + 1e-6:
            moment = base.shifted(offset)
            results.append(score_moment(moment, self.ctx))
            offset += step
        return results

    def rectify(
        self,
        base_moment: BirthMoment,
        window_minutes: float = 30.0,
        coarse_step_seconds: float = 240.0,
        fine_step_seconds: float = 10.0,
        fine_neighbourhood_seconds: float = 300.0,
        top_n_coarse: int = 3,
    ) -> RectificationReport:
        """Run the two-pass scan and return a ranked report.

        :param window_minutes: +/- search radius around the given time.
        :param coarse_step_seconds: step for the first pass.
        :param fine_step_seconds: step for the refinement pass.
        :param fine_neighbourhood_seconds: +/- radius refined around each top
            coarse candidate.
        :param top_n_coarse: how many coarse peaks to refine.
        """
        window = window_minutes * 60.0

        # Pass 1: coarse.
        coarse = self._scan_range(base_moment, -window, window, coarse_step_seconds)
        coarse.sort(key=lambda c: c.total_score, reverse=True)

        # Pass 2: refine around the best coarse peaks.
        seen: set[str] = set()
        refined: list[CandidateResult] = []
        base_local = base_moment.local_datetime()
        for peak in coarse[:top_n_coarse]:
            center_offset = (peak.moment.local_datetime() - base_local).total_seconds()
            local_results = self._scan_range(
                base_moment,
                center_offset - fine_neighbourhood_seconds,
                center_offset + fine_neighbourhood_seconds,
                fine_step_seconds,
            )
            for r in local_results:
                if r.time_label not in seen:
                    seen.add(r.time_label)
                    refined.append(r)

        all_results = refined if refined else coarse
        all_results.sort(key=lambda c: c.total_score, reverse=True)

        return RectificationReport(
            base_moment=base_moment,
            ranked=all_results,
            coarse_step_seconds=coarse_step_seconds,
            fine_step_seconds=fine_step_seconds,
            window_seconds=window,
        )
