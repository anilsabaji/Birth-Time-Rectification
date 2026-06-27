"""A self-contained Flask web UI for Birth Time Rectification.

Run:
    python -m btr.web.app           # then open http://localhost:8000
or:
    btr-web                         # console script (see pyproject)

The page is a single HTML document (no build step). It POSTs the form to
``/api/rectify`` and ``/api/chart`` which call the engine and return JSON.
"""
from __future__ import annotations

from datetime import date, datetime

from flask import Flask, jsonify, request

from ..api import chart_report, make_birth_moment, rectify
from ..core.constants import Ayanamsa, HouseSystem
from ..core.ephemeris import Ephemeris
from ..core.timeutil import julian_day_from_local
from ..kp.ruling_planets import compute_ruling_planets
from ..rectification.context import DEFAULT_METHOD_WEIGHTS, RectificationContext
from ..rectification.events import EventType, LifeEvent

app = Flask(__name__)


# --------------------------------------------------------------------------- #
# request parsing
# --------------------------------------------------------------------------- #


def _birth_from_payload(p: dict):
    d = p["birth"]
    dt = datetime.fromisoformat(d["datetime"])
    return make_birth_moment(
        year=dt.year, month=dt.month, day=dt.day,
        hour=dt.hour, minute=dt.minute, second=dt.second,
        tz_offset_hours=float(d["tz"]),
        latitude=float(d["latitude"]), longitude=float(d["longitude"]),
        place_name=d.get("place", ""),
    )


def _context_from_payload(p: dict) -> RectificationContext:
    birth = p["birth"]
    tz = float(birth["tz"])

    events = []
    for ev in p.get("events", []):
        if not ev.get("date"):
            continue
        events.append(LifeEvent(
            event_type=EventType(ev["type"]),
            event_date=date.fromisoformat(ev["date"]),
            description=ev.get("description", ""),
            weight=float(ev.get("weight", 1.0)),
        ))

    consult_rp = None
    c = p.get("consultation")
    if c and c.get("datetime"):
        cdt = datetime.fromisoformat(c["datetime"])
        loc_lat = float(c.get("latitude") or birth["latitude"])
        loc_lon = float(c.get("longitude") or birth["longitude"])
        from ..core.timeutil import GeoLocation
        loc = GeoLocation(loc_lat, loc_lon, name=c.get("place", ""))
        cjd = julian_day_from_local(
            cdt.year, cdt.month, cdt.day, cdt.hour, cdt.minute, 0.0,
            float(c.get("tz") or tz),
        )
        eph = Ephemeris(Ayanamsa.KRISHNAMURTI, HouseSystem.PLACIDUS)
        consult_rp = compute_ruling_planets(eph, cjd, loc)

    signs = [s.strip() for s in p.get("expected_lagna_signs", []) if s.strip()]

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
# API
# --------------------------------------------------------------------------- #


@app.post("/api/chart")
def api_chart():
    payload = request.get_json(force=True)
    moment = _birth_from_payload(payload)
    ayan = Ayanamsa.KRISHNAMURTI if payload.get("ayanamsa", "kp") == "kp" else Ayanamsa.LAHIRI
    return jsonify({"report": chart_report(moment, ayanamsa=ayan)})


@app.post("/api/rectify")
def api_rectify():
    payload = request.get_json(force=True)
    moment = _birth_from_payload(payload)
    ctx = _context_from_payload(payload)
    scan = payload.get("scan", {})
    report = rectify(
        moment, ctx,
        window_minutes=float(scan.get("window", 30)),
        coarse_step_seconds=float(scan.get("coarse", 240)),
        fine_step_seconds=float(scan.get("fine", 15)),
    )

    candidates = []
    for cand in report.top(int(scan.get("top", 5))):
        candidates.append({
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
                for ms in cand.method_scores if ms.weight > 0
            ],
        })
    return jsonify({
        "given_time": moment.label(),
        "best_time": report.best.time_label,
        "best_score": round(report.best.total_score, 1),
        "candidates": candidates,
        "report_text": report.render(int(scan.get("top", 5))),
    })


@app.get("/")
def index():
    return INDEX_HTML


# --------------------------------------------------------------------------- #
# Single-page UI
# --------------------------------------------------------------------------- #

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Birth Time Rectification (Parashara + KP)</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; }
  body { margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
         background:#0d1117; color:#e6edf3; }
  header { padding:18px 24px; border-bottom:1px solid #30363d; background:#161b22; }
  header h1 { margin:0; font-size:18px; }
  header p { margin:4px 0 0; color:#8b949e; font-size:13px; }
  .wrap { display:flex; gap:20px; padding:20px; flex-wrap:wrap; }
  .panel { background:#161b22; border:1px solid #30363d; border-radius:12px; padding:18px; }
  .form { flex:1; min-width:340px; }
  .results { flex:1.3; min-width:380px; }
  h2 { font-size:14px; text-transform:uppercase; letter-spacing:.5px; color:#8b949e; margin:0 0 12px; }
  label { display:block; font-size:12px; color:#8b949e; margin:10px 0 4px; }
  input, select { width:100%; padding:8px 10px; background:#0d1117; border:1px solid #30363d;
                  border-radius:7px; color:#e6edf3; font-size:13px; }
  .row { display:flex; gap:10px; } .row > div { flex:1; }
  .events-head { display:flex; justify-content:space-between; align-items:center; margin-top:18px; }
  .event { display:flex; gap:8px; margin-top:8px; align-items:center; }
  .event select { flex:2; } .event input[type=date]{ flex:1.4; } .event input.w { flex:.7; }
  button { cursor:pointer; border:none; border-radius:8px; font-weight:600; font-size:14px; }
  .btn-primary { background:#238636; color:#fff; padding:11px 18px; width:100%; margin-top:18px; }
  .btn-primary:hover { background:#2ea043; }
  .btn-ghost { background:#21262d; color:#e6edf3; padding:8px 12px; border:1px solid #30363d; }
  .btn-sm { padding:4px 9px; font-size:12px; }
  .x { background:#3d1418; color:#ff7b72; border:1px solid #5c2226; }
  .best { background:#0f2e1a; border:1px solid #238636; border-radius:10px; padding:16px; margin-bottom:14px; }
  .best .t { font-size:24px; font-weight:700; } .best .s { color:#7ee787; font-size:14px; }
  .cand { border:1px solid #30363d; border-radius:10px; padding:12px; margin-bottom:10px; }
  .cand .top { display:flex; justify-content:space-between; font-weight:600; }
  .bar { height:6px; background:#21262d; border-radius:4px; margin:4px 0 10px; overflow:hidden; }
  .bar > i { display:block; height:100%; background:linear-gradient(90deg,#1f6feb,#2ea043); }
  .m { font-size:12px; margin:5px 0; }
  .m .tag { display:inline-block; min-width:74px; color:#8b949e; }
  .m .kp { color:#d2a8ff; } .m .pa { color:#79c0ff; }
  .m .pct { font-weight:600; }
  .pe { color:#8b949e; font-size:11px; margin-left:78px; }
  pre { white-space:pre-wrap; font-size:11px; color:#8b949e; background:#0d1117; padding:12px;
        border-radius:8px; border:1px solid #30363d; max-height:320px; overflow:auto; }
  .muted { color:#8b949e; font-size:12px; }
  .spin { color:#8b949e; }
  details summary { cursor:pointer; color:#58a6ff; font-size:12px; margin-top:8px; }
</style>
</head>
<body>
<header>
  <h1>Birth Time Rectification &mdash; Parashara + KP</h1>
  <p>Enter a recorded birth time and confirmed life events; the engine scans nearby times and ranks them.</p>
</header>

<div class="wrap">
  <div class="panel form">
    <h2>Birth details</h2>
    <label>Date &amp; time (recorded)</label>
    <input type="datetime-local" id="b_dt" step="1" value="1990-08-15T14:30:00"/>
    <div class="row">
      <div><label>Timezone (UTC offset)</label><input id="b_tz" type="number" step="0.25" value="5.5"/></div>
      <div><label>Place name</label><input id="b_place" value="New Delhi, India"/></div>
    </div>
    <div class="row">
      <div><label>Latitude</label><input id="b_lat" type="number" step="0.0001" value="28.6139"/></div>
      <div><label>Longitude</label><input id="b_lon" type="number" step="0.0001" value="77.2090"/></div>
    </div>

    <label>Expected Ascendant sign(s) &mdash; optional (comma separated)</label>
    <input id="lagna" placeholder="e.g. Scorpio" value="Scorpio"/>

    <div class="events-head">
      <h2 style="margin:0">Life events</h2>
      <button class="btn-ghost btn-sm" onclick="addEvent()">+ add event</button>
    </div>
    <div id="events"></div>

    <details>
      <summary>KP Ruling Planets (consultation moment) &amp; scan settings</summary>
      <label>Consultation date &amp; time (defaults to now)</label>
      <input type="datetime-local" id="c_dt"/>
      <div class="row">
        <div><label>Window &plusmn; min</label><input id="s_window" type="number" value="30"/></div>
        <div><label>Coarse step (s)</label><input id="s_coarse" type="number" value="240"/></div>
        <div><label>Fine step (s)</label><input id="s_fine" type="number" value="15"/></div>
      </div>
    </details>

    <button class="btn-primary" onclick="runRectify()">Rectify birth time</button>
    <button class="btn-ghost" style="width:100%;margin-top:8px;padding:10px" onclick="runChart()">Show chart for entered time</button>
  </div>

  <div class="panel results">
    <h2>Results</h2>
    <div id="out"><p class="muted">Fill the form and click &ldquo;Rectify birth time&rdquo;.</p></div>
  </div>
</div>

<script>
const EVENT_TYPES = ["marriage","child_birth","career_start","job_change","promotion",
  "foreign_travel","education","property_vehicle","father_death","mother_death",
  "own_health_crisis","financial_gain","loss_separation","spiritual_initiation"];

function addEvent(type="marriage", d="", w=1.0){
  const box=document.getElementById("events");
  const row=document.createElement("div"); row.className="event";
  const sel=document.createElement("select");
  EVENT_TYPES.forEach(t=>{const o=document.createElement("option");o.value=t;o.textContent=t.replace(/_/g,' ');if(t===type)o.selected=true;sel.appendChild(o);});
  const dt=document.createElement("input"); dt.type="date"; dt.value=d;
  const wt=document.createElement("input"); wt.type="number"; wt.step="0.1"; wt.value=w; wt.className="w"; wt.title="weight";
  const x=document.createElement("button"); x.className="x btn-sm"; x.textContent="x"; x.onclick=()=>row.remove();
  row.append(sel,dt,wt,x); box.appendChild(row);
}
// seed a few example events
addEvent("marriage","2018-02-10",1.5);
addEvent("child_birth","2020-06-01",1.2);
addEvent("career_start","2013-07-15",1.0);
addEvent("foreign_travel","2016-09-20",0.8);

// default consultation = now
(function(){const n=new Date();n.setSeconds(0);document.getElementById("c_dt").value=n.toISOString().slice(0,16);})();

function collect(){
  const events=[...document.querySelectorAll("#events .event")].map(r=>{
    const [sel,dt,wt]=r.querySelectorAll("select,input");
    return {type:sel.value, date:dt.value, weight:parseFloat(wt.value)||1.0};
  });
  const cdt=document.getElementById("c_dt").value;
  return {
    birth:{ datetime:document.getElementById("b_dt").value,
      tz:document.getElementById("b_tz").value, place:document.getElementById("b_place").value,
      latitude:document.getElementById("b_lat").value, longitude:document.getElementById("b_lon").value },
    expected_lagna_signs:document.getElementById("lagna").value.split(",").map(s=>s.trim()).filter(Boolean),
    events: events,
    consultation: cdt ? { datetime:cdt, tz:document.getElementById("b_tz").value } : null,
    scan:{ window:document.getElementById("s_window").value, coarse:document.getElementById("s_coarse").value,
           fine:document.getElementById("s_fine").value, top:5 },
    ayanamsa:"kp"
  };
}

function sysClass(s){return s==="KP"?"kp":"pa";}

async function runRectify(){
  const out=document.getElementById("out");
  out.innerHTML='<p class="spin">Scanning candidate times&hellip;</p>';
  try{
    const res=await fetch("/api/rectify",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(collect())});
    const d=await res.json();
    if(d.error){out.innerHTML='<pre>'+d.error+'</pre>';return;}
    let h=`<div class="best"><div class="s">Best rectified time &middot; confidence ${d.best_score}/100</div>
            <div class="t">${d.best_time}</div>
            <div class="muted">given: ${d.given_time}</div></div>`;
    d.candidates.forEach((c,i)=>{
      h+=`<div class="cand"><div class="top"><span>#${i+1} &nbsp; ${c.time}</span><span>${c.score}/100</span></div>
          <div class="bar"><i style="width:${c.score}%"></i></div>`;
      c.methods.forEach(m=>{
        h+=`<div class="m"><span class="tag ${sysClass(m.system)}">${m.system}</span>
             <span>${m.name.replace(/_/g,' ')}</span> &mdash; <span class="pct">${m.score}%</span>
             <span class="muted">(w=${m.weight})</span></div>`;
        (m.per_event||[]).forEach(pe=>{ h+=`<div class="pe">&bull; ${pe}</div>`; });
      });
      h+=`</div>`;
    });
    h+=`<details><summary>Plain-text report</summary><pre>${d.report_text.replace(/</g,'&lt;')}</pre></details>`;
    out.innerHTML=h;
  }catch(e){ out.innerHTML='<pre>'+e+'</pre>'; }
}

async function runChart(){
  const out=document.getElementById("out");
  out.innerHTML='<p class="spin">Computing chart&hellip;</p>';
  try{
    const res=await fetch("/api/chart",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(collect())});
    const d=await res.json();
    out.innerHTML='<pre>'+(d.report||d.error).replace(/</g,'&lt;')+'</pre>';
  }catch(e){ out.innerHTML='<pre>'+e+'</pre>'; }
}
</script>
</body>
</html>
"""


def main() -> None:
    import os
    port = int(os.environ.get("BTR_PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
