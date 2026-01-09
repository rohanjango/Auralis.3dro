# ==============================
# 📦 IMPORTS
# ==============================
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import librosa
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import csv
import requests
import shutil
import os
import uuid
from transformers import pipeline

# ==============================
# 🚀 FASTAPI APP & SECURITY
# ==============================
app = FastAPI(title="Auralis API")

# --- SECURITY PASS (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return RedirectResponse(url="/docs")

# ==============================
# 🤖 LOAD MODELS
# ==============================
print("Loading Whisper Model...")
whisper = pipeline("automatic-speech-recognition", model="openai/whisper-small")

print("Loading YAMNet Model...")
yamnet = hub.load("https://tfhub.dev/google/yamnet/1")

# Load Class Labels
labels_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
response = requests.get(labels_url)
labels = []
reader = csv.reader(response.text.splitlines())
next(reader)
for row in reader:
    labels.append(row[2])

# ==============================
# 🧠 LOGIC ENGINE
# ==============================
def analyze_audio(text, sounds):
    text = text.lower()
    sound_labels = [s.lower() for s in sounds.keys()]

    airport_words = ["flight", "boarding", "gate", "airport"]
    rail_words = ["train", "platform", "coach"]
    emergency_words = ["help", "fire", "emergency", "police", "accident"]
    emergency_sounds = ["siren", "scream", "alarm", "glass", "shouting"]
    public_sounds = ["crowd", "conversation"]
    vehicle_sounds = ["vehicle", "engine", "traffic", "horn"]

    location = "Unknown"
    situation = "Unknown"
    evidence = []
    confidence = 0.3
    summary = "none"

    is_emergency_text = any(w in text for w in emergency_words)
    is_emergency_sound = any(any(es in s for es in emergency_sounds) for s in sound_labels)

    if any(w in text for w in airport_words) and any(s in sound_labels for s in public_sounds):
        location = "Airport"
        situation = "Boarding"
        evidence += ["Flight-related speech", "Public crowd sounds"]
        confidence = 0.85
    elif any(w in text for w in rail_words) and any(s in sound_labels for s in public_sounds):
        location = "Railway Station"
        situation = "Waiting / Boarding"
        evidence += ["Train-related speech", "Crowd sounds"]
        confidence = 0.8
    elif any(s in sound_labels for s in vehicle_sounds):
        location = "Road"
        situation = "Traffic"
        evidence += ["Vehicle sounds detected"]
        confidence = 0.7

    if is_emergency_text or is_emergency_sound:
        return {
            "location": location,
            "situation": "Emergency",
            "confidence": 0.95,
            "evidence": sound_labels,
            "summary": "Emergency situation detected.",
            "transcribe": text
        }
    
    summary = f"This audio likely comes from a {location.lower()} during {situation.lower()}."
    return {
        "location": location,
        "situation": situation,
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "summary": summary,
        "transcribe": text
    }

# ==============================
# 🌐 API ENDPOINT
# ==============================
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    print(f"File received: {file.filename}")

    # 1. Handle File Extension
    file_ext = os.path.splitext(file.filename)[1]
    if not file_ext: file_ext = ".wav"
    unique_filename = f"temp_{uuid.uuid4()}{file_ext}"

    try:
        # 2. Save File
        with open(unique_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 3. Transcribe
        try:
            whisper_result = whisper(unique_filename)
            text = whisper_result["text"]
        except:
            text = "Transcription failed"

        # 4. Analyze Sound (Load as WAV 16k)
        try:
            wav_data, _ = librosa.load(unique_filename, sr=16000)
        except Exception as e:
            if os.path.exists(unique_filename): os.remove(unique_filename)
            return {
                "location": "Format Error",
                "situation": "Unreadable Audio",
                "confidence": 0,
                "evidence": ["Try converting to .WAV"],
                "summary": "Could not process audio format. Windows needs FFmpeg for .m4a files.",
                "transcribe": "Error"
            }

        # 5. YAMNet Inference
        scores, _, _ = yamnet(wav_data)
        mean_scores = tf.reduce_mean(scores, axis=0).numpy()
        top_indices = np.argsort(mean_scores)[-10:][::-1]

        raw_sounds = {}
        for i in top_indices:
            raw_sounds[labels[i]] = float(mean_scores[i])

        keywords = ["speech", "conversation", "crowd", "vehicle", "engine", "traffic", "aircraft", "siren", "glass", "alarm"]
        sounds = {k: v for k, v in raw_sounds.items() if any(x in k.lower() for x in keywords)}

        # 6. Cleanup & Return
        if os.path.exists(unique_filename):
            os.remove(unique_filename)

        result = analyze_audio(text, sounds)
        return result

    except Exception as e:
        if os.path.exists(unique_filename):
            os.remove(unique_filename)
        print(f"SERVER ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))