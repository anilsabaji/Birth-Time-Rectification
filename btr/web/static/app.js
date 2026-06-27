/**
 * BTR Web UI Application
 * Handles form interaction, API calls, and result rendering
 */

// Event types available in the system
const EVENT_TYPES = [
    "marriage",
    "child_birth",
    "career_start",
    "job_change",
    "promotion",
    "foreign_travel",
    "education",
    "property_vehicle",
    "father_death",
    "mother_death",
    "own_health_crisis",
    "financial_gain",
    "loss_separation",
    "spiritual_initiation",
];

/**
 * Convert event type identifier to human-readable label
 */
function eventTypeLabel(type) {
    return type.replace(/_/g, " ");
}

/**
 * Get system classification (KP or Parashara)
 */
function getSystemClass(system) {
    return system === "KP" ? "kp" : "parashara";
}

/**
 * Initialize the form with example events and set consultation time to now
 */
function initializeForm() {
    // Add example events
    addEvent("marriage", "2018-02-10", 1.5);
    addEvent("child_birth", "2020-06-01", 1.2);
    addEvent("career_start", "2013-07-15", 1.0);
    addEvent("foreign_travel", "2016-09-20", 0.8);

    // Set consultation time to now
    const now = new Date();
    now.setSeconds(0);
    document.getElementById("c_dt").value = now.toISOString().slice(0, 16);
}

/**
 * Add a new event row to the events list
 */
function addEvent(type = "marriage", date = "", weight = 1.0) {
    const container = document.getElementById("events");
    const row = document.createElement("div");
    row.className = "event-row";

    // Event type selector
    const typeSelect = document.createElement("select");
    EVENT_TYPES.forEach((t) => {
        const option = document.createElement("option");
        option.value = t;
        option.textContent = eventTypeLabel(t);
        if (t === type) option.selected = true;
        typeSelect.appendChild(option);
    });

    // Date input
    const dateInput = document.createElement("input");
    dateInput.type = "date";
    dateInput.value = date;

    // Weight input
    const weightInput = document.createElement("input");
    weightInput.type = "number";
    weightInput.step = "0.1";
    weightInput.value = weight;
    weightInput.title = "Event weight (importance)";

    // Remove button
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn-remove";
    removeBtn.textContent = "✕";
    removeBtn.onclick = () => row.remove();

    row.appendChild(typeSelect);
    row.appendChild(dateInput);
    row.appendChild(weightInput);
    row.appendChild(removeBtn);
    container.appendChild(row);
}

/**
 * Collect form data into a payload object
 */
function collectFormData() {
    // Collect events
    const events = [...document.querySelectorAll("#events .event-row")].map((row) => {
        const [typeSelect, dateInput, weightInput] = row.querySelectorAll("select, input[type='date'], input[type='number']");
        return {
            type: typeSelect.value,
            date: dateInput.value,
            weight: parseFloat(weightInput.value) || 1.0,
        };
    });

    // Collect consultation datetime
    const consultationDt = document.getElementById("c_dt").value;

    return {
        birth: {
            datetime: document.getElementById("b_dt").value,
            tz: document.getElementById("b_tz").value,
            place: document.getElementById("b_place").value,
            latitude: document.getElementById("b_lat").value,
            longitude: document.getElementById("b_lon").value,
        },
        expected_lagna_signs: document
            .getElementById("lagna")
            .value.split(",")
            .map((s) => s.trim())
            .filter(Boolean),
        events: events,
        consultation: consultationDt
            ? {
                  datetime: consultationDt,
                  tz: document.getElementById("b_tz").value,
              }
            : null,
        scan: {
            window: document.getElementById("s_window").value,
            coarse: document.getElementById("s_coarse").value,
            fine: document.getElementById("s_fine").value,
            top: 5,
        },
        ayanamsa: "kp",
    };
}

/**
 * Display loading spinner in results area
 */
function showLoading(message = "Processing...") {
    const out = document.getElementById("out");
    out.innerHTML = `
        <div class="loading">
            <span class="spinner"></span>
            <span>${message}</span>
        </div>
    `;
}

/**
 * Display error message in results area
 */
function showError(message) {
    const out = document.getElementById("out");
    out.innerHTML = `
        <div class="error-message">
            <strong>⚠️ Error</strong>
            <div class="error-code">${escapeHtml(message)}</div>
        </div>
    `;
}

/**
 * Escape HTML special characters for safe display
 */
function escapeHtml(text) {
    const map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
    };
    return text.replace(/[&<>"']/g, (m) => map[m]);
}

/**
 * Format a method score display with color coding
 */
function formatMethodScore(methodScore) {
    const systemClass = getSystemClass(methodScore.system);
    const methodName = eventTypeLabel(methodScore.name);

    let html = `
        <div class="method-item">
            <span class="method-tag ${systemClass}">${methodScore.system}</span>
            <span class="method-name">${methodName}</span>
            <span class="method-score">${methodScore.score}%</span>
        </div>
    `;

    // Add per-event details if available
    if (methodScore.per_event && methodScore.per_event.length > 0) {
        methodScore.per_event.forEach((detail) => {
            html += `<div class="per-event-detail">${escapeHtml(detail)}</div>`;
        });
    }

    return html;
}

/**
 * Format a candidate time card
 */
function formatCandidateCard(candidate, index) {
    const scorePercent = Math.min(100, Math.max(0, candidate.score));

    let html = `
        <div class="candidate-card">
            <div class="candidate-header">
                <span>
                    <span class="candidate-rank">#${index + 1}</span>
                    <span class="candidate-time">${candidate.time}</span>
                </span>
                <span class="candidate-score">${candidate.score}/100</span>
            </div>
            <div class="score-bar">
                <div class="score-bar-fill" style="width: ${scorePercent}%"></div>
            </div>
            <div class="method-scores">
    `;

    // Add method scores
    if (candidate.methods && candidate.methods.length > 0) {
        candidate.methods.forEach((method) => {
            html += formatMethodScore(method);
        });
    }

    html += `</div></div>`;

    return html;
}

/**
 * Run rectification analysis
 */
async function runRectify() {
    const payload = collectFormData();

    if (!payload.birth.datetime) {
        showError("Please enter a birth date and time.");
        return;
    }

    if (payload.events.length === 0) {
        showError("Please add at least one life event.");
        return;
    }

    showLoading("🔍 Scanning candidate times...");

    try {
        const response = await fetch("/api/rectify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        // Render results
        renderRectificationResults(data);
    } catch (error) {
        showError(`Request failed: ${error.message}`);
        console.error("Rectification error:", error);
    }
}

/**
 * Render rectification results
 */
function renderRectificationResults(data) {
    const out = document.getElementById("out");
    let html = "";

    // Best result box
    html += `
        <div class="best-result">
            <div class="label">✓ Best Rectified Time</div>
            <div class="time">${data.best_time}</div>
            <div class="score">Confidence: ${data.best_score}/100</div>
            <div class="given-time">Given time: ${data.given_time}</div>
        </div>
    `;

    // Candidate cards
    if (data.candidates && data.candidates.length > 0) {
        data.candidates.forEach((candidate, index) => {
            html += formatCandidateCard(candidate, index);
        });
    }

    // Report section
    if (data.report_text) {
        html += `
            <details class="report-section">
                <summary>📋 Full Text Report</summary>
                <pre class="report-text">${escapeHtml(data.report_text)}</pre>
            </details>
        `;
    }

    out.innerHTML = html;
}

/**
 * Show chart for the entered birth time
 */
async function runChart() {
    const payload = collectFormData();

    if (!payload.birth.datetime) {
        showError("Please enter a birth date and time.");
        return;
    }

    showLoading("📊 Computing chart...");

    try {
        const response = await fetch("/api/chart", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        // Render chart report as preformatted text
        const out = document.getElementById("out");
        out.innerHTML = `
            <details class="report-section" open>
                <summary>📊 Chart Report</summary>
                <pre class="report-text">${escapeHtml(data.report || data.error)}</pre>
            </details>
        `;
    } catch (error) {
        showError(`Request failed: ${error.message}`);
        console.error("Chart error:", error);
    }
}

/**
 * Handle keyboard shortcuts
 */
document.addEventListener("DOMContentLoaded", function () {
    // Initialize form
    initializeForm();

    // Keyboard shortcuts
    document.addEventListener("keydown", function (e) {
        // Ctrl+Enter or Cmd+Enter to rectify
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            runRectify();
        }
    });

    // Handle Enter key in inputs to trigger rectification
    const inputs = document.querySelectorAll("input, select");
    inputs.forEach((input) => {
        input.addEventListener("keypress", function (e) {
            if (e.key === "Enter" && e.ctrlKey) {
                runRectify();
            }
        });
    });
});
