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
    card.className = "result"; // Re-using the CSS class from style.css
    card.style.marginTop = "0";
    card.style.marginBottom = "20px";

    card.innerHTML = `
      <div class="result-header">
        <div style="display:flex; gap:10px; align-items:center;">
             <span style="color: #666; font-size: 12px;">${item.timestamp}</span>
        </div>
        <span class="badge-score">${item.confidence} Confidence</span>
      </div>
      
      <div class="result-grid">
        <div class="result-item">
          <i class="fa-solid fa-location-dot"></i>
          <div>
            <small>Location</small>
            <span>${item.location}</span>
          </div>
        </div>
        <div class="result-item">
          <i class="fa-solid fa-brain"></i>
          <div>
            <small>Context</small>
            <span>${item.situation}</span>
          </div>
        </div>
        <div class="result-item">
          <i class="fa-solid fa-volume-high"></i>
          <div>
            <small>Sound Class</small>
            <span>${item.soundType}</span>
          </div>
        </div>
      </div>
    `;

    historyList.appendChild(card);
  });
}

// Load on startup
loadHistory();

// Clear History Logic
clearBtn.addEventListener("click", () => {
    if(confirm("Are you sure you want to clear all history?")) {
        localStorage.removeItem("auralisHistory");
        loadHistory();
    }
});