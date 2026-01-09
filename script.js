
const audio = document.getElementById("audio");
const playBtn = document.getElementById("playBtn");
const bars = document.querySelectorAll(".waveform span");
const waveform = document.getElementById("waveform");
const fileNameDisplay = document.getElementById("fileNameDisplay");

// Containers
const uploadContainer = document.getElementById("uploadContainer");
const playerContainer = document.getElementById("playerContainer");
const loading = document.getElementById("loading");
const result = document.getElementById("result");

// Data Elements
const locationText = document.getElementById("locationText");
const situationText = document.getElementById("situationText");
const confidenceText = document.getElementById("confidenceText"); 
const evidenceText = document.getElementById("evidenceText");
const summaryText = document.getElementById("summaryText");
const transcribeText = document.getElementById("transcribeText");
const saveBtn = document.getElementById("saveBtn");

// File Inputs
const audioUpload = document.getElementById("audioUpload");

// --- Variable to store the actual file for the API ---
let currentFile = null;

// --- 1. HANDLE FILE UPLOAD ---
audioUpload.addEventListener("change", function() {
    if (this.files.length > 0) {
        initPlayer(this.files[0]);
    }
});

// Support Drag and Drop
uploadContainer.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadContainer.style.borderColor = "#7f3cff";
});
uploadContainer.addEventListener("dragleave", (e) => {
    e.preventDefault();
    uploadContainer.style.borderColor = "#333";
});
uploadContainer.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadContainer.style.borderColor = "#333";
    if (e.dataTransfer.files.length > 0) {
        initPlayer(e.dataTransfer.files[0]);
    }
});

function initPlayer(file) {
    // Save file to global variable so we can send it to API later
    currentFile = file;

    // 1. Set File Name
    fileNameDisplay.textContent = file.name;
    
    // 2. Create Object URL
    const fileURL = URL.createObjectURL(file);
    audio.src = fileURL;

    // 3. Swap UI: Hide Upload, Show Player
    uploadContainer.classList.add("hidden");
    playerContainer.classList.remove("hidden");
    
    // 4. Hide old results if any
    result.classList.add("hidden");
    
    // 5. Reset Icon
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
}

// --- 2. PLAYER LOGIC & API TRIGGER ---
playBtn.addEventListener("click", () => {
    if (audio.paused) {
        audio.play();
        playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
        waveform.classList.add("active");
        bars.forEach(bar => bar.style.animationPlayState = "running");

        // --- Call Real API ---
        if (result.classList.contains("hidden")) {
            analyzeAudio(currentFile);
        }
    } else {
        audio.pause();
        playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
        waveform.classList.remove("active");
        bars.forEach(bar => bar.style.animationPlayState = "paused");
    }
});

audio.addEventListener("ended", () => {
    playBtn.innerHTML = '<i class="fa-solid fa-play"></i>';
    waveform.classList.remove("active");
    bars.forEach(bar => bar.style.animationPlayState = "paused");
});

// --- 3. REAL API INTEGRATION (UPDATED) ---
async function analyzeAudio(file) {
    if (!file) return;

    // Show Loading Animation
    loading.classList.remove("hidden");
    result.classList.add("hidden"); // Ensure result is hidden while loading
    
    // Create Form Data to send file
    const formData = new FormData();
    formData.append("file", file); 

    try {
        // --- FIX: Point to Localhost ---
        const response = await fetch("http://127.0.0.1:8000/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        // Get Data from API
        const data = await response.json();
        console.log("API Response:", data); 

        // Update UI with Real Data
        locationText.textContent = data.location || "Unknown";
        situationText.textContent = data.situation || "Analyzing context...";
        
        // Handle Evidence (Array or String)
        if (Array.isArray(data.evidence)) {
            evidenceText.textContent = data.evidence.join(", ");
        } else {
            evidenceText.textContent = data.evidence || "No evidence";
        }

        summaryText.textContent = data.summary || "No summary";
        
        // --- FIX: Handle key mismatch (transcribed vs transcribe) ---
        transcribeText.textContent = data.transcribed || data.transcribe || "No transcription";

        // Handle Confidence (Format as percentage)
        let conf = data.confidence;
        if (conf) {
            // If API returns 0.94, convert to 94%
            if (conf < 1) conf = Math.round(conf * 100);
            confidenceText.textContent = conf + "%";
        } else {
            confidenceText.textContent = "--%";
        }

        // Hide Loading, Show Result
        loading.classList.add("hidden");
        result.classList.remove("hidden");

    } catch (error) {
        console.error("Analysis Failed:", error);
        loading.innerHTML = `<p style="color:#ff4444;">Error: Could not connect to API. Is backend running?</p>`;
        alert("Could not connect to backend. Run 'uvicorn app:app --reload' in terminal.");
    }
}

// --- 4. SAVE LOGIC ---
saveBtn.addEventListener("click", () => {
    const historyItem = {
        location: locationText.textContent,
        situation: situationText.textContent,
        confidence: confidenceText.textContent,
        evidence: evidenceText.textContent,
        summary: summaryText.textContent,
        transcribe: transcribeText.textContent,
        timestamp: new Date().toLocaleString() // Added timestamp for dashboard
    };

    const existingHistory = JSON.parse(localStorage.getItem("auralisHistory")) || [];
    existingHistory.unshift(historyItem);
    localStorage.setItem("auralisHistory", JSON.stringify(existingHistory));

    const originalHTML = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Saved!';
    saveBtn.style.background = "#28a745";
    
    setTimeout(() => {
        saveBtn.innerHTML = originalHTML;
        saveBtn.style.background = "#7f3cff";
    }, 2000);
});