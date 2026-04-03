import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import re
import json
import time
import tempfile
import os
from datetime import datetime, timedelta
from collections import Counter, defaultdict

# =========================
# GEMINI API KEY (Secrets)
# =========================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = None

if not GEMINI_API_KEY:
    st.error("⚠️ No GEMINI_API_KEY found. Add it to .streamlit/secrets.toml.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# =========================
#  PAGE CONFIG + CSS
# =========================
st.set_page_config(
    page_title="Mental Health Stress Detector - Dark Mode",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Space+Grotesk:wght@500;700&display=swap');
    .stApp {background: linear-gradient(120deg, #22223b, #4b3a62 65%, #22223b 100%);}
    .main-header {background:rgba(20,24,38,0.95);padding:2rem;border-radius:18px;text-align:center;margin-bottom:2rem;box-shadow:0 10px 25px #31185e60;}
    .main-header h1 {font-family:'Space Grotesk',sans-serif;font-size:2.8rem;font-weight:700;background:-webkit-linear-gradient(135deg,#00fff5,#bb86fc 80%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:1.2px;}
    .main-header p {color:#c9aaff;font-size:1.1rem;font-weight:400;letter-spacing:1px;}
    .info-card {background:rgba(49,24,94,0.65);padding:1.5rem;border-radius:16px;box-shadow:0 4px 18px #31185e40;margin-bottom:1.2rem;}
    .info-card h3 {color:#bb86fc;font-size:1.2rem;font-weight:600;}
    .stTextArea textarea {border-radius:12px!important;border:2px solid #bb86fc!important;background-color:#22223b!important;color:#fafafa!important;}
    .stButton > button {background:linear-gradient(90deg,#00fff5,#755edb);color:white;border:none;font-weight:700;padding:0.8rem 1.3rem;border-radius:22px;font-size:1.05rem;}
    .stButton > button:hover {background:linear-gradient(90deg,#755edb,#00fff5);}
    .response-area {background: linear-gradient(135deg,#211a33,#321c43 70%,#211a33 100%); padding:2rem;border-radius:18px;box-shadow:0 4px 16px #31185e40;}
    .response-area h3 {color:#00fff5;font-size:1.4rem;}
    .emergency-banner {background:linear-gradient(135deg,#f093fb,#f5576c);color:white;padding:1.2rem;border-radius:16px;text-align:center;font-weight:700;margin:1rem 0;font-size:1.1rem;}
    .stress-meter-container {display:flex;flex-direction:column;align-items:center;margin:1.5rem 0;}
    .circular-gauge {width:140px;height:140px;border-radius:50%;background:conic-gradient(#00ff88 0%,#ffc107 50%,#ff6b6b 90%,#31185e 100%);display:flex;align-items:center;justify-content:center;}
    .gauge-inner {width:100px;height:100px;border-radius:50%;background:#22223b;display:flex;flex-direction:column;align-items:center;justify-content:center;}
    .stress-percentage {font-size:2.8rem;font-weight:700;color:#00fff5;}
    .stress-label {font-size:0.95rem;color:#bb86fc;text-transform:uppercase;}
    .transcript-box {background:rgba(0,255,245,0.07);border:1px solid #00fff540;border-radius:10px;padding:0.8rem 1rem;color:#e8d6ff;font-size:0.95rem;margin-top:0.7rem;}
    .mood-tag-btn button {background:rgba(49,24,94,0.8)!important;border:1px solid #bb86fc!important;border-radius:20px!important;color:#e8d6ff!important;font-size:0.9rem!important;padding:0.3rem 0.9rem!important;margin:0.2rem!important;}
    .cooldown-bar {background:rgba(255,107,107,0.15);border:1px solid #ff6b6b60;border-radius:10px;padding:0.6rem 1rem;color:#ff6b6b;font-size:0.9rem;text-align:center;margin-bottom:0.5rem;}

    @keyframes breathe {
        0%   { transform: scale(1);   box-shadow: 0 0 0px #00fff580; }
        40%  { transform: scale(1.45); box-shadow: 0 0 38px #00fff5cc; }
        60%  { transform: scale(1.45); box-shadow: 0 0 38px #00fff5cc; }
        100% { transform: scale(1);   box-shadow: 0 0 0px #00fff580; }
    }
    .breathing-widget {
        display:flex; flex-direction:column; align-items:center;
        background:rgba(0,255,245,0.05); border:1px solid #00fff530;
        border-radius:18px; padding:1.5rem 1rem; margin:1.2rem 0;
    }
    .breathing-widget h4 { color:#00fff5; font-size:1rem; margin-bottom:0.8rem; letter-spacing:1px; }
    .breath-circle {
        width:90px; height:90px; border-radius:50%;
        background:radial-gradient(circle, #00fff540, #00fff510);
        border:2px solid #00fff5;
        animation: breathe 8s ease-in-out infinite;
        display:flex; align-items:center; justify-content:center;
    }
    .breath-inner { color:#00fff5; font-size:0.72rem; text-align:center; line-height:1.4; font-weight:600; letter-spacing:0.5px; }
    .breath-steps { color:#c9aaff; font-size:0.8rem; margin-top:0.7rem; text-align:center; line-height:1.8; }

    .feature-card {
        background: rgba(0,255,245,0.05);
        border: 1px solid rgba(0,255,245,0.20);
        border-radius: 14px;
        padding: 1rem;
        margin-top: 0.8rem;
        color: #e8d6ff;
    }
    .small-note {
        color:#c9aaff;
        font-size:0.88rem;
    }
    .section-title {
        color:#00fff5;
        font-size:1.15rem;
        font-weight:700;
        margin-top:1rem;
        margin-bottom:0.5rem;
    }
    .pill {
        display:inline-block;
        background: rgba(187,134,252,0.18);
        border:1px solid rgba(187,134,252,0.35);
        color:#f1dcff;
        padding:0.3rem 0.7rem;
        border-radius:999px;
        font-size:0.82rem;
        margin:0.2rem 0.25rem 0.2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ====== FILE PATHS ======
HISTORY_FILE = "stress_history.json"
JOURNAL_FILE = "journal_entries.json"

# ====== MODEL NAMES ======
PRIMARY_MODEL   = "models/gemini-1.5-flash"   # Primary
FALLBACK_MODEL  = "models/gemini-2.5-flash"   # Fallback

# ====== LANGUAGE CONFIG ======
LANGUAGES = {
    "English": "English",
    "Hindi (हिन्दी)": "Hindi",
    "Punjabi (ਪੰਜਾਬੀ)": "Punjabi",
    "Tamil (தமிழ்)": "Tamil",
    "Telugu (తెలుగు)": "Telugu",
    "Bengali (বাংলা)": "Bengali",
    "Marathi (मराठी)": "Marathi",
}

# ====== MOOD TAG CONFIG ======
MOOD_TAGS = {
    "😔 Sad": "I have been feeling very sad and low lately.",
    "😤 Angry": "I have been feeling very angry and frustrated.",
    "😰 Anxious": "I have been feeling extremely anxious and worried.",
    "😞 Hopeless": "I feel hopeless and like things won't get better.",
    "😴 Exhausted": "I am completely exhausted and have no energy.",
}

# ====== TOPIC CATEGORIES ======
TOPIC_KEYWORDS = {
    "Work": ["job", "work", "boss", "office", "deadline", "career", "coworker", "promotion"],
    "Relationships": ["partner", "relationship", "boyfriend", "girlfriend", "marriage", "family", "friend", "parents"],
    "Health": ["health", "illness", "pain", "doctor", "sleep", "tired", "fatigue", "panic", "anxiety"],
    "Finances": ["money", "loan", "debt", "rent", "bills", "finance", "salary", "fees"],
    "Exams": ["exam", "college", "study", "result", "assignment", "semester", "school", "class"],
}

# -------------------------
# JSON storage helpers
# -------------------------
def load_json_file(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json_file(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Could not save data to {path}: {e}")

def append_history_entry(entry):
    data = load_json_file(HISTORY_FILE, [])
    data.append(entry)
    save_json_file(HISTORY_FILE, data)

def append_journal_entry(entry):
    data = load_json_file(JOURNAL_FILE, [])
    data.append(entry)
    save_json_file(JOURNAL_FILE, data)

# -------------------------
# Safe generate wrapper
# -------------------------
def safe_generate(prompt, max_retries=2, backoff_base=2):
    """Try PRIMARY_MODEL (gemini-1.5-flash) first; fall back to FALLBACK_MODEL (gemini-2.5-flash)."""
    for model_id in [PRIMARY_MODEL, FALLBACK_MODEL]:
        attempt = 0
        while attempt <= max_retries:
            try:
                model = genai.GenerativeModel(model_id)
                return model.generate_content(prompt)
            except Exception as e:
                msg = str(e).lower()
                if "429" in msg or "quota" in msg or "rate limit" in msg:
                    if model_id == PRIMARY_MODEL:
                        st.warning("⚠️ Gemini 1.5 Flash quota reached — switching to Gemini 2.5 Flash fallback.")
                    break  # move to next model in chain
                attempt += 1
                time.sleep(backoff_base ** attempt * 0.5)
        # if we exited the while without returning, try next model
    st.error("AI request failed. Using offline fallback where possible.")
    return None

# -------------------------
# Transcribe audio via Gemini Files API
# -------------------------
def transcribe_audio(audio_bytes, model_id=None):
    if model_id is None:
        model_id = PRIMARY_MODEL
    tmp_path = None
    uploaded_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        uploaded_file = genai.upload_file(tmp_path, mime_type="audio/wav")

        model = genai.GenerativeModel(model_id)
        response = model.generate_content([
            "Transcribe the following audio recording exactly as spoken. "
            "Return only the transcribed words — no labels, no timestamps, no extra commentary.",
            uploaded_file
        ])

        if response and response.text:
            return response.text.strip()
        return None

    except Exception as e:
        st.error(f"🎙️ Transcription failed: {e}")
        return None

    finally:
        if uploaded_file:
            try:
                genai.delete_file(uploaded_file.name)
