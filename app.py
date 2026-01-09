# ==============================
# 📦 IMPORTS — Tools uthaa raha hu
# ==============================

from fastapi import FastAPI, UploadFile, File, HTTPException
# --- FIX: Added CORS Middleware ---
from fastapi.middleware.cors import CORSMiddleware 
from fastapi.responses import RedirectResponse

import librosa
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import csv
import requests
from transformers import pipeline

# --- FIX: Added for file handling ---
import shutil
import os
import uuid

# ==============================
# 🚀 FASTAPI APP CREATE
# ==============================

app = FastAPI(title="Auralis API")

# --- FIX: ALLOW BROWSER CONNECTION (CORS) ---
# This is required for the website to talk to the server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
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

# Load Labels
labels_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
response = requests.get(labels_url)
labels = []
reader = csv.reader(response.text.splitlines())
next(reader)
for row in reader:
    labels.append(row[2])


# ==============================
# 🧠 INFERENCE ENGINE (DIMAG)
# ==============================

def analyze_audio(text, sounds):
    text = text.lower()
    sound_labels = [s.lower() for s in sounds.keys()]

    # Keywords
    airport_words = ["flight", "boarding", "gate", "airport"]
    rail_words = ["train", "platform", "coach"]
    emergency_words = ["help", "fire", "emergency","police","accident"]
    emergency_sounds = ["siren","scream","alarm","glass","shouting"]
    public_sounds = ["crowd", "conversation"]
    vehicle_sounds = ["vehicle", "engine", "traffic", "horn"]

    # Defaults
    location = "Unknown"
    situation = "Unknown"
    evidence = []          
    confidence = 0.3       
    summary = "none"
    
    # Logic Rules
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

    # Emergency Override
    if is_emergency_text or is_emergency_sound:
        return {
            "location": location,
            "situation": "Emergency",
            "confidence": 0.95,
            "evidence": sound_labels,
            "summary": "Emergency situation detected based on distress signals.",
            "transcribe": text # Fixed key name
        }

    summary = f"This audio likely comes from a {location.lower()} during {situation.lower()}."
    return {
        "location": location,
        "situation": situation,
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "summary": summary,
        "transcribe": text # Fixed key name
    }


# ==============================
# 🌐 API ENDPOINT (/analyze)
# ==============================

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    print(f"File received: {file.filename}")

    # --- FIX: Handle File Extensions & Unique Names ---
    # Prevents crashing if user uploads .m4a or if multiple users upload at once
    file_ext = os.path.splitext(file.filename)[1]
    if not file_ext: 
        file_ext = ".wav"
        
    unique_filename = f"temp_{uuid.uuid4()}{file_ext}"

    try:
        # Save file safely
        with open(unique_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. WHISPER (Audio -> Text)
        try:
            whisper_result = whisper(unique_filename)
            text = whisper_result["text"]
        except Exception as e:
            print(f"Whisper Error: {e}")
            text = "Audio unclear"

        # 2. LOAD AUDIO (With Error Check)
        try:
            wav_data, _ = librosa.load(unique_filename, sr=16000)
        except Exception as e:
            # If librosa fails (e.g. format not supported), delete file and return error
            if os.path.exists(unique_filename): os.remove(unique_filename)
            return {
                "location": "Format Error",
                "situation": "Unreadable Audio",
                "confidence": 0,
                "evidence": ["Try a .WAV file"],
                "summary": "Could not read audio format.",
                "transcribe": "Error"
            }

        # 3. YAMNet (Audio -> Sounds)
        scores, _, _ = yamnet(wav_data)
        mean_scores = tf.reduce_mean(scores, axis=0).numpy()
        top_indices = np.argsort(mean_scores)[-10:][::-1]

        raw_sounds = {}
        for i in top_indices:
            raw_sounds[labels[i]] = float(mean_scores[i])

        # Filter Important Sounds
        keywords = ["speech", "conversation", "crowd", "vehicle", "engine", "traffic", "aircraft", "siren", "glass", "alarm"]
        sounds = {k: v for k, v in raw_sounds.items() if any(x in k.lower() for x in keywords)}

        # --- FIX: Cleanup Temp File ---
        if os.path.exists(unique_filename):
            os.remove(unique_filename)

        # Return Result
        return analyze_audio(text, sounds)

    except Exception as e:
        # Emergency Cleanup
        if os.path.exists(unique_filename):
            os.remove(unique_filename)
        print(f"SERVER ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))