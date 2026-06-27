# BTR — Birth Time Rectification (Parashara + KP)

A computational engine that **rectifies an uncertain birth time** by scoring
candidate times against confirmed life events and physical traits, using both
the **Parashara** (traditional Vedic) and **KP** (Krishnamurti Paddhati)
systems. Astronomy is provided by the Swiss Ephemeris (`pyswisseph`) using the
built-in Moshier model, so **no external ephemeris data files are required**.

> Disclaimer: this is software for exploring an esoteric discipline. It computes
> the traditional indicators faithfully but makes no claim about the predictive
> validity of astrology itself.

## What it implements

Each rectification method discussed in the two systems maps to a scorer:

| System | Method | Module | What it tests |
|---|---|---|---|
| KP | **Ruling Planets** | `kp/ruling_planets.py` + `score_ruling_planets` | Birth Asc & Moon (sign/star/sub lords) must harmonise with the RP set taken at the rectification moment |
| KP | **Cuspal Sub-Lord + Significators** | `kp/cuspal.py`, `kp/significators.py` + `score_kp_cuspal_events` | The event's cuspal sub-lord must signify the event houses, and the dasha lords at the event must be significators |
| KP | **Sub / Sub-Sub / Nadi-Ansa** | `kp/sublord.py` | Sign→Star→Sub→Sub-Sub→Nadi lordship of any longitude (the 249-table granularity used to pinpoint the Ascendant) |
| Parashara | **Dasha–Event correlation** | `dasha/vimshottari.py` + `score_dasha_correlation` | Running Maha/Antar/Pratyantar lords must signify each event's houses |
| Parashara | **Divisional (Varga) consistency** | `charts/divisional.py` + `score_varga_consistency` | Dasha lords must activate the event houses in the relevant varga (D9 marriage, D7 children, D10 career, D12 parents, …) |
| Parashara | **Pranapada** | `charts/special_points.py` + `score_pranapada` | Pranapada should fall in an auspicious bhava (1/4/5/7/9/10/11) |
| Parashara | **Gulika / Mandi** | `charts/special_points.py` + `score_gulika` | Gulika's sub-lord should relate to the active event houses |
| Both | **Lagna trait match** | `score_lagna_traits` | Ascendant sign / nakshatra vs. stated traits |

A weighted blend of all the above produces a single **0–100 confidence** per
candidate time. The engine scans coarse-to-fine (≈4-minute coarse pass, then a
seconds-level refinement approaching Nadi-Ansa precision).

## Install

```bash
uv venv --python 3.11
. .venv/bin/activate
uv pip install -e .
```

## Usage

### Command line

```bash
# Full chart for the birth time in a case file
python -m btr.cli chart examples/sample_case.json --ayanamsa kp

# Rectify against the events in the case file
python -m btr.cli rectify examples/sample_case.json --window 30 --coarse 240 --fine 10 --top 5
```

The case-file schema is documented by `examples/sample_case.json`: a `birth`
block, an optional `consultation` block (for KP Ruling Planets), an `events`
list (`type` from the `EventType` enum + ISO `date`), optional
`expected_lagna_signs`, and optional `method_weights` overrides.

### Programmatic

```python
from datetime import date
from btr.api import make_birth_moment, rectify
from btr.rectification.context import RectificationContext
from btr.rectification.events import EventType, LifeEvent

birth = make_birth_moment(1990, 8, 15, 14, 30, 0, 5.5, 28.6139, 77.2090, "Delhi")
ctx = RectificationContext(
    birth_tz=5.5,
    events=[LifeEvent(EventType.MARRIAGE, date(2018, 2, 10))],
    expected_lagna_signs=["Scorpio"],
)
report = rectify(birth, ctx, window_minutes=30)
print(report.render())
```

See `examples/rectify_example.py` for a complete run.

## Architecture

```
btr/
  core/          ephemeris wrapper, ayanamsa, time/JD, constants
  charts/        divisional charts (vargas), special points (Pranapada, Gulika)
  dasha/         Vimshottari Maha/Antar/Pratyantar tree
  kp/            sub-lords, cuspal sub-lords, ruling planets, significators
  rectification/ event model, per-method scoring, coarse-to-fine engine
  api.py         high-level facade
  cli.py         command-line interface
```

## Tests

```bash
. .venv/bin/activate
python -m pytest -q
```

## Notes on conventions

- **Ayanamsa:** Lahiri for Parashara charts/dasha, Krishnamurti for KP work.
- **Nodes:** the *true* node is used for Rahu; Ketu is exactly 180° opposite.
- **Houses:** Placidus cusps for KP; whole-sign bhavas for Parashara significators.
- **Vimshottari year:** 365.2425 days by default (configurable).
- Traditions differ on Gulika vs. Mandi; here Mandi = Ascendant at the *start*
  of Saturn's eighth-part, Gulika = Ascendant at its *end*.
```
