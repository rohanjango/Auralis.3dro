const historyList = document.getElementById("historyList");
const clearBtn = document.getElementById("clearBtn");

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

// Escape quotes to prevent HTML breaking in onclick attributes
function escapeForOnclick(text) {
  return String(text ?? "").replace(/'/g, "\\'");
}

function loadHistory() {
  const history = getHistorySafe();
  historyList.innerHTML = ""; 

  if (history.length === 0) {
    historyList.innerHTML = `
        <div style="text-align: center; color: #555; margin-top: 50px;">
            <i class="fa-regular fa-folder-open" style="font-size: 40px; margin-bottom: 15px;"></i>
            <p>No analysis history found.</p>
        </div>
    `;
    return;
  }

  history.forEach(item => {
    const card = document.createElement("div");
    card.className = "result history-card"; 

    // Visual decoration
    let waveBars = '';
    for (let i = 0; i < 12; i++) {
      let h = Math.floor(Math.random() * 80) + 20; 
      waveBars += `<span style="height: ${h}%"></span>`;
    }

    const timestamp = item.timestamp || "Unknown time";
    const confidence = item.confidence || "--%";
    const location = item.location || "Unknown";
    const situation = item.situation || "Unknown";
    const soundType = item.soundType || "General Audio";

    const escLocation = escapeForOnclick(location);
    const escSituation = escapeForOnclick(situation);
    const escSound = escapeForOnclick(soundType);

    card.innerHTML = `
      <div class="result-header">
        <div class="meta-left">
             <div class="mini-waveform">${waveBars}</div>
             <span class="timestamp">${timestamp}</span>
        </div>
        <span class="badge-score">${confidence} Confidence</span>
      </div>

      <div class="result-grid">
        <div class="result-item">
          <i class="fa-solid fa-location-dot"></i>
          <div class="content-wrapper">
            <small>Location</small>
            <span>${location}</span>
          </div>
          <button class="copy-btn" onclick="copyText(this, '${escLocation}')" title="Copy">
            <i class="fa-regular fa-copy"></i>
          </button>
        </div>

        <div class="result-item">
          <i class="fa-solid fa-brain"></i>
          <div class="content-wrapper">
            <small>Context</small>
            <span>${situation}</span>
          </div>
          <button class="copy-btn" onclick="copyText(this, '${escSituation}')" title="Copy">
            <i class="fa-regular fa-copy"></i>
          </button>
        </div>

        <div class="result-item">
          <i class="fa-solid fa-volume-high"></i>
          <div class="content-wrapper">
            <small>Sound Class</small>
            <span>${soundType}</span>
          </div>
          <button class="copy-btn" onclick="copyText(this, '${escSound}')" title="Copy">
            <i class="fa-regular fa-copy"></i>
          </button>
        </div>
      </div>
    `;
    historyList.appendChild(card);
  });
}

window.copyText = function (btnElement, text) {
  navigator.clipboard.writeText(text).then(() => {
    const icon = btnElement.querySelector("i");
    const originalClass = icon.className;
    
    icon.className = "fa-solid fa-check";
    icon.style.color = "#28a745";

    setTimeout(() => {
      icon.className = originalClass;
      icon.style.color = "";
    }, 2000);
  });
};

// Initial load
loadHistory();

// Clear History
if (clearBtn) {
  clearBtn.addEventListener("click", () => {
    if (historyList.children.length === 0 || historyList.innerText.includes("No analysis")) return;
    if (confirm("Are you sure you want to clear all history?")) {
      localStorage.removeItem("auralisHistory");
      loadHistory();
    }
  });
}