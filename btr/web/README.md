# Web UI - Quick Start Guide

## Running the BTR Web UI

### Option 1: Using the console script (recommended)
```bash
btr-web
```

Then open your browser to: **http://localhost:8000**

### Option 2: Using Python module
```bash
python -m btr.web.app
```

Then open your browser to: **http://localhost:8000**

### Option 3: Custom port
```bash
BTR_PORT=9000 btr-web
```

Then open your browser to: **http://localhost:9000**

---

## Features

### 🌙 Birth Information Section
- **Date & Time**: Enter the recorded birth datetime
- **Timezone**: UTC offset (e.g., +5.5 for India)
- **Location**: Place name and geographic coordinates (latitude/longitude)
- **Ascendant Signs**: Optional constraint for expected lagna signs

### 📋 Life Events Manager
- Add multiple confirmed life events with dates
- Event types: Marriage, Child Birth, Career Start, Job Change, Promotion, Foreign Travel, Education, Property/Vehicle, Deaths, Health Crisis, Financial Gain, Loss/Separation, Spiritual Initiation
- Adjust importance weight for each event (0.1 to 10.0)
- Easy add/remove interface

### ⚙️ Advanced Settings
- **KP Ruling Planets**: Optional consultation datetime for KP method
- **Scan Window**: Time range to search (±minutes, default 30)
- **Coarse Step**: Initial scan resolution in seconds (default 240)
- **Fine Step**: Refinement resolution in seconds (default 15)

### 📊 Results Display

#### Best Rectified Time
- Confidence score (0-100)
- Comparison with given time

#### Ranked Candidates
- Top 5 candidate times by default
- Score bar visualization
- Method-by-method breakdown:
  - **KP Methods** (purple): Ruling Planets, Cuspal Sub-Lords, Significators
  - **Parashara Methods** (blue): Vimshottari Dasha, Varga Consistency, Special Points

#### Full Report
- Detailed text analysis of rectification
- Per-method scoring details
- Collapsible for space efficiency

---

## Keyboard Shortcuts

- **Ctrl+Enter** or **Cmd+Enter**: Submit rectification form

---

## API Endpoints

### POST /api/rectify
Runs birth time rectification analysis.

**Request:**
```json
{
  "birth": {
    "datetime": "1990-08-15T14:30:00",
    "tz": 5.5,
    "place": "New Delhi, India",
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "events": [
    {
      "type": "marriage",
      "date": "2018-02-10",
      "weight": 1.5
    }
  ],
  "expected_lagna_signs": ["Scorpio"],
  "consultation": {
    "datetime": "2026-06-27T15:00:00",
    "tz": 5.5
  },
  "scan": {
    "window": 30,
    "coarse": 240,
    "fine": 15,
    "top": 5
  }
}
```

**Response:**
```json
{
  "given_time": "1990-08-15 14:30:00 UTC+5:30",
  "best_time": "1990-08-15 14:32:15 UTC+5:30",
  "best_score": 87.3,
  "candidates": [
    {
      "time": "1990-08-15 14:32:15 UTC+5:30",
      "score": 87.3,
      "methods": [
        {
          "name": "ruling_planets_match",
          "system": "KP",
          "score": 92.5,
          "weight": 2.5,
          "detail": "Birth Asc & Moon harmonise with RP set",
          "per_event": []
        }
      ]
    }
  ],
  "report_text": "..."
}
```

### POST /api/chart
Computes a birth chart for a given time.

**Request:**
```json
{
  "birth": {
    "datetime": "1990-08-15T14:30:00",
    "tz": 5.5,
    "place": "New Delhi, India",
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "ayanamsa": "kp"
}
```

**Response:**
```json
{
  "report": "CHART  1990-08-15 14:30:00 (TZ +5.50) ayanamsa=krishnamurti (23.2415)\n..."
}
```

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## Environment Variables

- `BTR_PORT` (default: 8000) - Port to run the web server on
- `BTR_HOST` (default: 0.0.0.0) - Host to bind to
- `BTR_DEBUG` (default: false) - Enable Flask debug mode

Example:
```bash
BTR_PORT=9000 BTR_DEBUG=true btr-web
```

---

## Troubleshooting

### Port already in use
```bash
BTR_PORT=8001 btr-web
```

### Connection refused
- Ensure the server is running
- Check the port number
- Try `http://localhost:8000` instead of `127.0.0.1:8000`

### Form not loading
- Check browser console for JavaScript errors
- Ensure static files are being served (`/static/style.css`, `/static/app.js`)
- Clear browser cache and reload

### Rectification takes too long
- Reduce the `window` parameter (default 30 minutes)
- Increase the `coarse` step (default 240 seconds)
- Reduce the `fine` step accuracy if not needed

---

## Technical Details

### Architecture
- **Backend**: Flask web framework
- **Frontend**: Vanilla JavaScript with CSS Grid layout
- **Styling**: Dark GitHub-inspired theme
- **Responsive**: Works on desktop, tablet, and mobile

### Files
- `btr/web/app.py` - Flask application & API routes
- `btr/web/templates/base.html` - HTML template
- `btr/web/static/style.css` - Stylesheet (17.7 KB)
- `btr/web/static/app.js` - Client-side logic (10.8 KB)

### Browser Compatibility
- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

---

## Support

For issues, questions, or contributions, visit:
https://github.com/anilsabaji/Birth-Time-Rectification
