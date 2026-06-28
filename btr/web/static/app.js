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

// Global variable to store last rectification result
let lastRectificationData = null;

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
        native_name: document.getElementById("native_name").value,
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
 * Switch between result tabs
 */
function switchTab(tabName, event) {
    event.preventDefault();
    
    // Hide all tabs
    document.querySelectorAll(".tab-content").forEach(tab => {
        tab.classList.remove("active");
    });
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("active");
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add("active");
    event.target.classList.add("active");
}

/**
 * Show tabs after rectification
 */
function showTabs() {
    const tabsElement = document.getElementById("resultsTabs");
    if (tabsElement) {
        tabsElement.style.display = "flex";
    }
}

/**
 * Generate and display HTML report
 */
function generateHTMLReport(data) {
    const nativeName = document.getElementById("native_name").value || "Native";
    const birthPlace = document.getElementById("b_place").value;
    const birthTz = document.getElementById("b_tz").value;
    
    const htmlContent = `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Birth Time Rectification Report - ${nativeName}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 20px; }
        h1, h2, h3 { color: #2c3e50; }
        .header { border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; }
        .section { margin-bottom: 30px; page-break-inside: avoid; }
        .best-result { background: #e8f8f5; border-left: 4px solid #27ae60; padding: 15px; margin-bottom: 20px; }
        .candidate { background: #f8f9fa; border: 1px solid #dee2e6; padding: 12px; margin-bottom: 10px; border-radius: 4px; }
        .score-bar { width: 100%; height: 20px; background: #ddd; border-radius: 3px; overflow: hidden; margin: 8px 0; }
        .score-fill { height: 100%; background: linear-gradient(90deg, #e74c3c, #f39c12, #f1c40f, #2ecc71); }
        .method-item { padding: 5px 0; font-size: 0.9em; }
        .method-tag { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 0.85em; font-weight: bold; margin-right: 5px; }
        .kp { background: #9b59b6; color: white; }
        .parashara { background: #3498db; color: white; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #bdc3c7; padding: 10px; text-align: left; }
        th { background: #34495e; color: white; }
        .report-text { white-space: pre-wrap; background: #f5f5f5; padding: 10px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Birth Time Rectification Report</h1>
        <h3>Native: <strong>${escapeHtml(nativeName)}</strong></h3>
        <p class="timestamp"><strong>Generated:</strong> ${new Date().toLocaleString()}</p>
    </div>

    <div class="section">
        <h2>Birth Information</h2>
        <table>
            <tr><th>Field</th><th>Value</th></tr>
            <tr><td>Date & Time</td><td>${data.given_time}</td></tr>
            <tr><td>Place</td><td>${escapeHtml(birthPlace)}</td></tr>
            <tr><td>Timezone</td><td>UTC +${birthTz}</td></tr>
            <tr><td>Latitude/Longitude</td><td>${document.getElementById("b_lat").value}, ${document.getElementById("b_lon").value}</td></tr>
        </table>
    </div>

    <div class="section">
        <h2>Best Rectified Time</h2>
        <div class="best-result">
            <p><strong>Rectified Time:</strong> ${data.best_time}</p>
            <p><strong>Confidence Score:</strong> ${data.best_score}/100</p>
        </div>
    </div>

    <div class="section">
        <h2>Top 5 Candidates</h2>
        ${data.candidates.map((candidate, index) => `
            <div class="candidate">
                <h4>#${index + 1}: ${candidate.time} - Score: ${candidate.score}/100</h4>
                <div class="score-bar"><div class="score-fill" style="width: ${candidate.score}%"></div></div>
                <div>
                    ${candidate.methods.map(method => `
                        <div class="method-item">
                            <span class="method-tag ${method.system.toLowerCase()}">${method.system}</span>
                            <strong>${method.name}</strong>: ${method.score}%
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('')}
    </div>

    <div class="section">
        <h2>Detailed Analysis</h2>
        <div class="report-text">${escapeHtml(data.report_text)}</div>
    </div>
    
    <hr style="margin-top: 40px;">
    <p class="timestamp" style="text-align: center; margin-top: 20px;">Generated by BTR (Birth Time Rectification) Engine v0.2.0</p>
</body>
</html>
    `;
    return htmlContent;
}

/**
 * Download HTML report
 */
function downloadHTML() {
    if (!lastRectificationData) {
        alert("No data to export. Run rectification first.");
        return;
    }
    
    const nativeName = document.getElementById("native_name").value || "Native";
    const html = generateHTMLReport(lastRectificationData);
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `BTR_Report_${nativeName.replace(/\s+/g, "_")}_${new Date().getTime()}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

/**
 * Download PDF report
 */
function downloadPDF() {
    if (!lastRectificationData) {
        alert("No data to export. Run rectification first.");
        return;
    }
    
    const nativeName = document.getElementById("native_name").value || "Native";
    const htmlContent = generateHTMLReport(lastRectificationData);
    
    const element = document.createElement("div");
    element.innerHTML = htmlContent;
    
    const opt = {
        margin: 10,
        filename: `BTR_Report_${nativeName.replace(/\s+/g, "_")}.pdf`,
        image: { type: "jpeg", quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { orientation: "portrait", unit: "mm", format: "a4" },
    };
    
    html2pdf().set(opt).from(element).save();
}

/**
 * Copy content to clipboard
 */
function copyToClipboard(elementId) {
    if (!lastRectificationData) {
        alert("No content to copy. Run rectification first.");
        return;
    }
    
    const nativeName = document.getElementById("native_name").value || "Native";
    const html = generateHTMLReport(lastRectificationData);
    
    navigator.clipboard.writeText(html).then(() => {
        alert("HTML report copied to clipboard!");
    }).catch(() => {
        alert("Failed to copy to clipboard.");
    });
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

        // Store data for export
        lastRectificationData = data;
        
        // Show tabs
        showTabs();
        
        // Render results
        renderRectificationResults(data);
        
        // Generate export content
        const htmlReport = generateHTMLReport(data);
        document.getElementById("html-content").textContent = htmlReport;
        document.getElementById("html-placeholder").style.display = "none";
        document.getElementById("html-content").style.display = "block";
        
        document.getElementById("pdf-placeholder").style.display = "none";
        document.getElementById("pdf-content").style.display = "block";
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