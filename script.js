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
const classText = document.getElementById("classText");
const confidenceText = document.getElementById("confidenceText");
const saveBtn = document.getElementById("saveBtn");

// File Inputs
const audioUpload = document.getElementById("audioUpload");

// --- NEW: Variable to store the actual file for the API ---
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

        // --- CHANGED: Call Real API instead of Simulation ---
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

// --- 3. REAL API INTEGRATION (Replaces Simulation) ---
async function analyzeAudio(file) {
    if (!file) return;

    // Show Loading Animation
    loading.classList.remove("hidden");
    
    // Create Form Data to send file
    const formData = new FormData();
    formData.append("file", file); // API expects key 'file'

    try {
        // --- THE REAL API CALL ---
        const response = await fetch("https://animated-sniffle-97xp45r7j74xc7666-8000.app.github.dev/analyze", {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }

        // Get Data from API
        const data = await response.json();
        console.log("API Response:", data); // Check console if data is missing

        // Update UI with Real Data
        // (Note: I am assuming the API returns keys like location, situation, etc. 
        // If the keys are different, e.g. 'predicted_class', change them below)
        locationText.textContent = data.location || "Unknown";
        situationText.textContent = data.situation || "Analyzing context...";
        classText.textContent = data.audio_class || data.class || "Detected Sound";
        
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
        loading.innerHTML = `<p style="color:#ff4444;">Error: Could not connect to API.</p>`;
    }
}

// --- 4. SAVE LOGIC ---
saveBtn.addEventListener("click", () => {
    const historyItem = {
        id: Date.now(),
        location: locationText.textContent,
        situation: situationText.textContent,
        soundType: classText.textContent,
        confidence: confidenceText.textContent,
        timestamp: new Date().toLocaleString()
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