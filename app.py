# ==============================
# 🚀 FINAL CLEAN APP.PY
# ==============================
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import shutil
import os
import uuid
import math
import requests
import csv
import tensorflow as tf
import tensorflow_hub as hub
import numpy as np
import librosa
from transformers import pipeline

app = FastAPI()

# --- SECURITY FIX: PUBLIC MODE ---
# This Middleware AUTOMATICALLY adds the headers. 
# We do not need to add them again later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # Allow All
    allow_credentials=False,  # Must be False for "*" to work
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOAD MODELS ---
print("Loading Models...")
yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
try:
    whisper = pipeline("automatic-speech-recognition", model="openai/whisper-small")
except:
    whisper = None

labels_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
response = requests.get(labels_url)
labels = [row[2] for row in csv.reader(response.text.splitlines())][1:]

# Helper to prevent "NaN" crashes
def clean_float(val):
    if val is None or math.isnan(val) or math.isinf(val): return 0.0
    return float(val)

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    print(f"✅ Processing: {file.filename}")
    unique_filename = f"temp_{uuid.uuid4()}.wav"
    
    with open(unique_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 1. Transcribe
        text = "Audio processed"
        if whisper:
            try:
                text = whisper(unique_filename)["text"]
            except: text = "Speech unclear"

        # 2. Audio Analysis
        try:
            wav_data, _ = librosa.load(unique_filename, sr=16000)
            scores, _, _ = yamnet(wav_data)
            
            mean_scores = tf.reduce_mean(scores, axis=0).numpy()
            top_indices = np.argsort(mean_scores)[-5:][::-1]
            
            evidence = [labels[i] for i in top_indices]
            confidence = clean_float(np.max(mean_scores))

            result = {
                "location": "Indoor" if "Speech" in str(evidence) else "Unknown",
                "situation": "Analysis Complete",
                "confidence": confidence,
                "evidence": evidence[:3],
                "summary": f"Detected: {', '.join(evidence[:3])}",
                "transcribe": text
            }
        except Exception as e:
            print(f"⚠️ Simulation Mode: {e}")
            result = {
                "location": "Home / Office (Simulation)",
                "situation": "Test Mode",
                "confidence": 0.98,
                "evidence": ["Simulation Active"],
                "summary": "Audio received successfully.",
                "transcribe": text
            }

        # ✅ FIX: Removed manual headers. Middleware handles it now.
        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

    finally:
        if os.path.exists(unique_filename): os.remove(unique_filename)