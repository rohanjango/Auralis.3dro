// ===============================
// ✅ Auralis Dashboard.js
// ✅ Fixes:
//  - Safe localStorage parsing
//  - Clear history confirm
//  - Better empty state
//  - Accessible rendering
// ===============================

const historyList = document.getElementById("historyList");
const clearBtn = document.getElementById("clearBtn");

function showEmptyState() {
  if (!historyList) return;
  historyList.innerHTML = `
    <div class="history-empty">
      <i class="fa-solid fa-inbox"></i>
      <h3>No saved analysis yet</h3>
      <p>Go to Home → upload audio → Save to Dashboard.</p>
      <a class="btn btn-hover" href="index.html" style="margin-top:12px; display:inline-flex; align-items:center; gap:8px;">
        <i class="fa-solid fa-arrow-left"></i> Back to Home
      </a>
    </div>
  `;
}

// ✅ Safe parse (dashboard never crashes)
function getHistorySafe() {
  try {
    const raw = localStorage.getItem("auralisHistory");
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    console.warn("⚠️ Corrupted history data. Resetting...", e);
    localStorage.removeItem("auralisHistory");
    return [];
  }
}

function escapeHtml(str) {
  return String(str || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// Render history cards
function renderHistory() {
  const history = getHistorySafe();

  if (!historyList) return;

  if (!history.length) {
    showEmptyState();
    return;
  }

  historyList.innerHTML = "";

  history.forEach((item) => {
    const timestamp = escapeHtml(item.timestamp || "Unknown time");
    const location = escapeHtml(item.location || "Unknown");
    const situation = escapeHtml(item.situation || "Unknown");
    const confidence = escapeHtml(item.confidence || "0%");
    const soundType = escapeHtml(item.soundType || "Audio");
    const fileName = escapeHtml(item.fileName || "Unknown file");
    const transcription = escapeHtml(item.transcription || "");

    // mini waveform bars
    const waveBars = new Array(14).fill(0).map(() => "<span></span>").join("");

    const card = document.createElement("div");
    card.className = "history-card";

    card.innerHTML = `
      <div class="result-header">
        <div class="meta-left">
          <div class="mini-waveform" aria-hidden="true">${waveBars}</div>
          <span class="timestamp">${timestamp}</span>
        </div>
        <span class="badge-score">${confidence} Confidence</span>
      </div>

      <div class="result-grid">
        <div class="result-item">
          <i class="fa-solid fa-location-dot"></i>
          <div class="content-wrapper">
            <small>Location</small>
            <p>${location}</p>
          </div>
        </div>

        <div class="result-item">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <div class="content-wrapper">
            <small>Situation</small>
            <p>${situation}</p>
          </div>
        </div>

        <div class="result-item">
          <i class="fa-solid fa-wave-square"></i>
          <div class="content-wrapper">
            <small>Sound Type</small>
            <p>${soundType}</p>
          </div>
        </div>

        <div class="result-item">
          <i class="fa-solid fa-file-audio"></i>
          <div class="content-wrapper">
            <small>File</small>
            <p>${fileName}</p>
          </div>
        </div>
      </div>

      <div class="transcription-box">
        <small>Transcription</small>
        <p>${transcription || "<i style='opacity:0.7'>No transcription saved.</i>"}</p>
      </div>
    `;

    historyList.appendChild(card);
  });
}

// Clear history
clearBtn?.addEventListener("click", () => {
  const ok = confirm("Are you sure you want to clear all dashboard history?");
  if (!ok) return;
  localStorage.removeItem("auralisHistory");
  renderHistory();
});

renderHistory();
