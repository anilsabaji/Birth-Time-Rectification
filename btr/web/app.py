"""A self-contained Flask web UI for Birth Time Rectification.

Run:
    python -m btr.web.app           # then open http://localhost:8000
or:
    btr-web                         # console script (see pyproject)

The page uses a Jinja2 template and serves static CSS/JS files.
"""
from __future__ import annotations

import os
from datetime import date, datetime

from flask import Flask, jsonify, render_template, request

from ..api import chart_report, make_birth_moment, rectify
from ..core.constants import Ayanamsa, HouseSystem
from ..core.ephemeris import Ephemeris
from ..core.timeutil import julian_day_from_local
from ..kp.ruling_planets import compute_ruling_planets
from ..rectification.context import DEFAULT_METHOD_WEIGHTS, RectificationContext
from ..rectification.events import EventType, LifeEvent

# Create Flask app with proper template and static folders
_app_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(_app_dir, "templates"),
    static_folder=os.path.join(_app_dir, "static"),
    static_url_path="/static",
)


# --------------------------------------------------------------------------- #
# request parsing
# --------------------------------------------------------------------------- #


def _birth_from_payload(p: dict):
    """Parse birth information from request payload."""
    d = p["birth"]
    dt = datetime.fromisoformat(d["datetime"])
    return make_birth_moment(
        year=dt.year,
        month=dt.month,
        day=dt.day,
        hour=dt.hour,
        minute=dt.minute,
        second=dt.second,
        tz_offset_hours=float(d["tz"]),
        latitude=float(d["latitude"]),
        longitude=float(d["longitude"]),
        place_name=d.get("place", ""),
    )


def _context_from_payload(p: dict) -> RectificationContext:
    """Parse rectification context from request payload."""
    birth = p["birth"]
    tz = float(birth["tz"])

    # Parse life events
    events = []
    for ev in p.get("events", []):
        if not ev.get("date"):
            continue
        events.append(
            LifeEvent(
                event_type=EventType(ev["type"]),
                event_date=date.fromisoformat(ev["date"]),
                description=ev.get("description", ""),
                weight=float(ev.get("weight", 1.0)),
            )
        )

    # Parse consultation ruling planets (KP method)
    consult_rp = None
    c = p.get("consultation")
    if c and c.get("datetime"):
        cdt = datetime.fromisoformat(c["datetime"])
        loc_lat = float(c.get("latitude") or birth["latitude"])
        loc_lon = float(c.get("longitude") or birth["longitude"])
        from ..core.timeutil import GeoLocation

        loc = GeoLocation(loc_lat, loc_lon, name=c.get("place", ""))
        cjd = julian_day_from_local(
            cdt.year,
            cdt.month,
            cdt.day,
            cdt.hour,
            cdt.minute,
            0.0,
            float(c.get("tz") or tz),
        )
        eph = Ephemeris(Ayanamsa.KRISHNAMURTI, HouseSystem.PLACIDUS)
        consult_rp = compute_ruling_planets(eph, cjd, loc)

    # Parse expected lagna signs
    signs = [s.strip() for s in p.get("expected_lagna_signs", []) if s.strip()]

    # Parse method weights
    weights = dict(DEFAULT_METHOD_WEIGHTS)
    weights.update(p.get("method_weights", {}))

    return RectificationContext(
        birth_tz=tz,
        events=events,
        consultation_ruling_planets=consult_rp,
        expected_lagna_signs=signs,
        method_weights=weights,
    )


# --------------------------------------------------------------------------- #
# API Endpoints
# --------------------------------------------------------------------------- #


@app.post("/api/chart")
def api_chart():
    """Compute and return a birth chart report."""
    try:
        payload = request.get_json(force=True)
        moment = _birth_from_payload(payload)
        ayan = (
            Ayanamsa.KRISHNAMURTI
            if payload.get("ayanamsa", "kp") == "kp"
            else Ayanamsa.LAHIRI
        )
        return jsonify({"report": chart_report(moment, ayanamsa=ayan)})
    except Exception as e:
        return (
            jsonify({"error": f"Chart computation failed: {str(e)}"}),
            400,
        )


@app.post("/api/rectify")
def api_rectify():
    """Run birth time rectification and return ranked candidates."""
    try:
        payload = request.get_json(force=True)
        moment = _birth_from_payload(payload)
        ctx = _context_from_payload(payload)
        scan = payload.get("scan", {})

        report = rectify(
            moment,
            ctx,
            window_minutes=float(scan.get("window", 30)),
            coarse_step_seconds=float(scan.get("coarse", 240)),
            fine_step_seconds=float(scan.get("fine", 15)),
        )

        # Format candidate results
        candidates = []
        for cand in report.top(int(scan.get("top", 5))):
            candidates.append(
                {
                    "time": cand.time_label,
                    "score": round(cand.total_score, 1),
                    "methods": [
                        {
                            "name": ms.name,
                            "system": ms.system,
                            "score": round(ms.score * 100, 1),
                            "weight": ms.weight,
                            "detail": ms.detail,
                            "per_event": ms.per_event,
                        }
                        for ms in cand.method_scores
                        if ms.weight > 0
                    ],
                }
            )

        return jsonify(
            {
                "given_time": moment.label(),
                "best_time": report.best.time_label,
                "best_score": round(report.best.total_score, 1),
                "candidates": candidates,
                "report_text": report.render(int(scan.get("top", 5))),
            }
        )
    except Exception as e:
        return (
            jsonify({"error": f"Rectification failed: {str(e)}"}),
            400,
        )


# --------------------------------------------------------------------------- #
# Web UI Routes
# --------------------------------------------------------------------------- #


@app.get("/")
def index():
    """Render the main application page."""
    return render_template("base.html")


@app.get("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "version": "0.1.0"})


# --------------------------------------------------------------------------- #
# Error Handlers
# --------------------------------------------------------------------------- #


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


def main() -> None:
    """Main entry point for the web UI."""
    port = int(os.environ.get("BTR_PORT", "8000"))
    host = os.environ.get("BTR_HOST", "0.0.0.0")
    debug = os.environ.get("BTR_DEBUG", "false").lower() == "true"
    
    print(f"🌙 BTR Web UI starting at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
