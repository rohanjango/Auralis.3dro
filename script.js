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

// --- 1. HANDLE FILE UPLOAD ---
audioUpload.addEventListener("change", function() {
    if (this.files.length > 0) {
        initPlayer(this.files[0]);
    }
});

// Support Drag and Drop on the upload container
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

// --- 2. PLAYER LOGIC ---
playBtn.addEventListener("click", () => {
    if (audio.paused) {
        audio.play();
        playBtn.innerHTML = '<i class="fa-solid fa-pause"></i>';
        waveform.classList.add("active");
        bars.forEach(bar => bar.style.animationPlayState = "running");

        // Trigger Analysis Simulation if not already done
        if (result.classList.contains("hidden")) {
            startSimulation();
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

// --- 3. AI SIMULATION ---
function startSimulation() {
    loading.classList.remove("hidden");
    
    setTimeout(() => {
        // Mock Data
        locationText.textContent = "Urban / Metro Station";
        situationText.textContent = "Announcement & Footsteps";
        classText.textContent = "Public Transit";
        confidenceText.textContent = "94%";

        loading.classList.add("hidden");
        result.classList.remove("hidden");
    }, 2500); // 2.5s delay
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