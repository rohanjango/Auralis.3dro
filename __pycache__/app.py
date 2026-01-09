
    
 # ==============================
# 📦 IMPORTS
# ==============================
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware # <--- NEW: Fixes connection error
from fastapi.responses import RedirectResponse
import librosa
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import csv
import requests
import shutil # <--- NEW: Better file saving
import os     # <--- NEW: For file cleanup
import uuid   # <--- NEW: Unique filenames

from transformers import pipeline

# ==============================
# 🚀 FASTAPI APP CREATE
# ==============================
app = FastAPI(title="Auralis API")

# --- NEW: ALLOW BROWSER CONNECTION (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all connections (Frontend, Postman, etc.)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return RedirectResponse(url="/docs")

# --- LOAD MODELS (Same as before) ---
whisper = pipeline("automatic-speech-recognition", model="openai/whisper-small")
yamnet = hub.load("https://tfhub.dev/google/yamnet/1")

# --- LOAD LABELS (Same as before) ---
labels_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
response = requests.get(labels_url)
labels = []
reader = csv.reader(response.text.splitlines())
next(reader)
for row in reader:
    labels.append(row[2])

# ==============================
# 🧠 INFERENCE ENGINE
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
        # Emergency Override
        return {
            "location": location,
            "situation": "Emergency",
            "confidence": 0.95,
            "confidence_reason": "High confidence due to emergency signals.",
            "evidence": sound_labels,
            "summary": "Emergency situation detected based on distress signals.",
            "transcribe": text  # <--- FIXED: Matches frontend key
        }
    
    summary = f"This audio likely comes from a {location.lower()} during {situation.lower()}, inferred from {' '.join(evidence)}."
    
    return {
        "location": location,
        "situation": situation,
        "confidence": round(confidence, 2),
        "evidence": evidence,
        "summary": summary,
        "transcribe": text # <--- FIXED: Matches frontend key
    }

# ==============================
# 🌐 API ENDPOINT (/analyze)
# ==============================
@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    print(f"File received: {file.filename}")

    # --- FIX 1: KEEP ORIGINAL FILE EXTENSION ---
    # If user uploads .m4a, we must save as .m4a so librosa knows how to read it.
    file_ext = os.path.splitext(file.filename)[1]
    if not file_ext:
        file_ext = ".wav" # Default fallback if no extension found
    
    unique_filename = f"temp_{uuid.uuid4()}{file_ext}"

    try:
        # Save uploaded file
        with open(unique_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 1. WHISPER (Audio -> Text)
        try:
            # Whisper handles most formats (m4a, mp3, wav) well
            whisper_result = whisper(unique_filename)
            text = whisper_result["text"]
        except Exception as e:
            print(f"Whisper Warning: {e}")
            text = "Could not transcribe."

        # 2. LOAD AUDIO (The part that was crashing)
        try:
            # Force 16k sample rate for YAMNet
            wav_data, _ = librosa.load(unique_filename, sr=16000)
        except Exception as e:
            print(f"Librosa Error: {e}")
            # --- FIX 2: PREVENT CRASH ---
            # If librosa fails, return a friendly error to the website instead of crashing
            return {
                "location": "Format Error",
                "situation": "Unreadable Audio",
                "confidence": 0,
                "evidence": ["Try a .WAV file"],
                "summary": "The system could not read this audio format. Please try converting it to .WAV.",
                "transcribe": "Error loading audio"
            }

        # 3. YAMNet (Audio -> Sounds)
        scores, _, _ = yamnet(wav_data)
        mean_scores = tf.reduce_mean(scores, axis=0).numpy()
        top_indices = np.argsort(mean_scores)[-10:][::-1]

        raw_sounds = {}
        for i in top_indices:
            raw_sounds[labels[i]] = float(mean_scores[i])

        # Filter keywords
        keywords = ["speech", "conversation", "crowd", "vehicle", "engine", "traffic", "aircraft", "siren", "glass", "alarm"]
        sounds = {k: v for k, v in raw_sounds.items() if any(x in k.lower() for x in keywords)}

        # Cleanup
        if os.path.exists(unique_filename):
            os.remove(unique_filename)

        # Return results
        result = analyze_audio(text, sounds)
        result['transcribe'] = result.pop('transcribed', text)
        return result

    except Exception as e:
        # Final Cleanup if major error
        if os.path.exists(unique_filename):
            os.remove(unique_filename)
        # Print the real error to terminal so you can see it
        print(f"CRITICAL ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # --- NEW: CLEANUP ---
        # Always delete the temp file, even if error occurs
        if os.path.exists(unique_filename):
            os.remove(unique_filename)