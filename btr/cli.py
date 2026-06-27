"""Command-line interface for the BTR engine.

Two sub-commands:

  chart    - print the full chart for one birth time.
  rectify  - rectify a birth time against a JSON case file of life events.

Run ``btr rectify --help`` or see ``examples/sample_case.json`` for the schema.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from . import api
from .core.constants import Ayanamsa, HouseSystem
from .core.ephemeris import Ephemeris
from .core.timeutil import GeoLocation, julian_day_from_local
from .kp.ruling_planets import compute_ruling_planets
from .rectification.context import DEFAULT_METHOD_WEIGHTS, RectificationContext
from .rectification.events import EventType, LifeEvent


def _moment_from_dict(d: dict):
    return api.make_birth_moment(
        year=d["year"],
        month=d["month"],
        day=d["day"],
        hour=d["hour"],
        minute=d["minute"],
        second=float(d.get("second", 0)),
        tz_offset_hours=float(d["tz"]),
        latitude=float(d["latitude"]),
        longitude=float(d["longitude"]),
        place_name=d.get("place", ""),
    )


def _build_context_from_case(case: dict) -> RectificationContext:
    tz = float(case["birth"]["tz"])
    events = []
    for ev in case.get("events", []):
        events.append(
            LifeEvent(
                event_type=EventType(ev["type"]),
                event_date=date.fromisoformat(ev["date"]),
                description=ev.get("description", ""),
                houses=ev.get("houses", []),
                weight=float(ev.get("weight", 1.0)),
            )
        )

    consult_rp = None
    consult = case.get("consultation")
    if consult:
        loc = GeoLocation(
            float(consult["latitude"]),
            float(consult["longitude"]),
            name=consult.get("place", ""),
        )
        cjd = julian_day_from_local(
            consult["year"], consult["month"], consult["day"],
            consult.get("hour", 12), consult.get("minute", 0),
            0.0, float(consult["tz"]),
        )
        eph = Ephemeris(Ayanamsa.KRISHNAMURTI, HouseSystem.PLACIDUS)
        consult_rp = compute_ruling_planets(eph, cjd, loc)

    weights = dict(DEFAULT_METHOD_WEIGHTS)
    weights.update(case.get("method_weights", {}))

    return RectificationContext(
        birth_tz=tz,
        events=events,
        consultation_ruling_planets=consult_rp,
        expected_lagna_signs=case.get("expected_lagna_signs", []),
        expected_lagna_nakshatra=case.get("expected_lagna_nakshatra"),
        method_weights=weights,
    )


def cmd_chart(args: argparse.Namespace) -> int:
    with open(args.case) as fh:
        case = json.load(fh)
    moment = _moment_from_dict(case["birth"])
    ayan = Ayanamsa.KRISHNAMURTI if args.ayanamsa == "kp" else Ayanamsa.LAHIRI
    print(api.chart_report(moment, ayanamsa=ayan))
    return 0


def cmd_rectify(args: argparse.Namespace) -> int:
    with open(args.case) as fh:
        case = json.load(fh)
    moment = _moment_from_dict(case["birth"])
    ctx = _build_context_from_case(case)
    report = api.rectify(
        moment,
        ctx,
        window_minutes=args.window,
        coarse_step_seconds=args.coarse,
        fine_step_seconds=args.fine,
    )
    print(report.render(n=args.top))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="btr", description="Birth Time Rectification (Parashara + KP)")
    sub = p.add_subparsers(dest="command", required=True)

    pc = sub.add_parser("chart", help="print full chart for the birth time in a case file")
    pc.add_argument("case", help="path to JSON case file")
    pc.add_argument("--ayanamsa", choices=["kp", "lahiri"], default="kp")
    pc.set_defaults(func=cmd_chart)

    pr = sub.add_parser("rectify", help="rectify the birth time against events")
    pr.add_argument("case", help="path to JSON case file")
    pr.add_argument("--window", type=float, default=30.0, help="search radius in minutes (default 30)")
    pr.add_argument("--coarse", type=float, default=240.0, help="coarse step seconds (default 240)")
    pr.add_argument("--fine", type=float, default=10.0, help="fine step seconds (default 10)")
    pr.add_argument("--top", type=int, default=5, help="how many candidates to show")
    pr.set_defaults(func=cmd_rectify)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
