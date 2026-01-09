const historyList = document.getElementById("historyList");
const clearBtn = document.getElementById("clearBtn");

function loadHistory() {
  const history = JSON.parse(localStorage.getItem("auralisHistory")) || [];

  historyList.innerHTML = ""; // Clear current list

  if (history.length === 0) {
    historyList.innerHTML = `
        <div style="text-align: center; color: #555; margin-top: 50px;">
            <i class="fa-regular fa-folder-open" style="font-size: 40px; margin-bottom: 15px;"></i>
            <p>No analysis history found.</p>
        </div>
    `;
    return;
  }

  // Loop through history and create cards
  history.forEach(item => {
    const card = document.createElement("div");
    card.className = "result history-card"; // Added 'history-card' class
    
    // Generate Mini Waveform (Visual decoration)
    // We create a random seed visual for each card to make it look unique
    let waveBars = '';
    for(let i=0; i<12; i++) {
        let h = Math.floor(Math.random() * 80) + 20; // random height %
        waveBars += `<span style="height: ${h}%"></span>`;
    }

    card.innerHTML = `
      <div class="result-header">
        <div class="meta-left">
             <div class="mini-waveform">${waveBars}</div>
             <span class="timestamp">${item.timestamp}</span>
        </div>
        <span class="badge-score">${item.confidence} Confidence</span>
      </div>
      
      <div class="result-grid">
        
        <div class="result-item">
          <i class="fa-solid fa-location-dot"></i>
          <div class="content-wrapper">
            <small>Location</small>
            <span>${item.location}</span>
          </div>
          <button class="copy-btn" onclick="copyText(this, '${item.location}')" title="Copy Location">
            <i class="fa-regular fa-copy"></i>
          </button>
        </div>

        <div class="result-item">
          <i class="fa-solid fa-brain"></i>
          <div class="content-wrapper">
            <small>Context</small>
            <span>${item.situation}</span>
          </div>
          <button class="copy-btn" onclick="copyText(this, '${item.situation}')" title="Copy Context">
            <i class="fa-regular fa-copy"></i>
          </button>
        </div>

        <div class="result-item">
          <i class="fa-solid fa-volume-high"></i>
          <div class="content-wrapper">
            <small>Sound Class</small>
            <span>${item.soundType}</span>
          </div>
          <button class="copy-btn" onclick="copyText(this, '${item.soundType}')" title="Copy Class">
            <i class="fa-regular fa-copy"></i>
          </button>
        </div>

      </div>
    `;

    historyList.appendChild(card);
  });
}

// --- NEW: Copy to Clipboard Function ---
window.copyText = function(btnElement, text) {
    navigator.clipboard.writeText(text).then(() => {
        // Visual Feedback
        const icon = btnElement.querySelector("i");
        icon.className = "fa-solid fa-check";
        icon.style.color = "#28a745";
        
        setTimeout(() => {
            icon.className = "fa-regular fa-copy";
            icon.style.color = "";
        }, 2000);
    });
}

// Load on startup
loadHistory();

// Clear History Logic
if(clearBtn) {
    clearBtn.addEventListener("click", () => {
        if(historyList.children.length === 0 || historyList.innerText.includes("No analysis")) return;
        
        if(confirm("Are you sure you want to clear all history?")) {
            localStorage.removeItem("auralisHistory");
            loadHistory();
        }
    });
}