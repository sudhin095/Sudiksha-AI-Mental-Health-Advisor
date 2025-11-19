# Updated app.py with Qwen 2.5 72B + Mistral 7B fallback
# (Interface fully preserved)

# NOTE: Due to response length limits in this environment, 
# I will now produce the updated code in multiple steps if needed.

# --- START OF FILE ---

import streamlit as st
from streamlit_mic_recorder import mic_recorder
import re
import json
import time
import requests

# =========================
# MODEL ENDPOINTS (OpenRouter)
# =========================
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Load API keys
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = None

try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    OPENROUTER_API_KEY = None

if not OPENROUTER_API_KEY:
    st.error("⚠️ Missing OPENROUTER_API_KEY in secrets.")
    st.stop()

# Make the UI unchanged
st.set_page_config(
    page_title="Mental Health Stress Detector - Dark Mode",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =======================================
# CALL OPENROUTER MODEL (Qwen + Mistral)
# =======================================
def call_openrouter(model, prompt, max_tokens=300):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    try:
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=25)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return None
    except Exception:
        return None

# =======================================
# SAFE GENERATION WRAPPER
# Qwen 72B → fallback: Mistral 7B
# =======================================
def safe_generate(prompt):
    # 1️⃣ Try Qwen 2.5 72B (free + smart)
    qwen_output = call_openrouter("qwen/qwen2.5-72b-instruct", prompt)
    if qwen_output:
        return qwen_output

    # 2️⃣ Fallback to Mistral 7B (fast, always works)
    mistral_output = call_openrouter("mistralai/mistral-7b-instruct", prompt)
    if mistral_output:
        st.warning("⚠️ Using fallback model: Mistral 7B (Qwen quota or timeout).")
        return mistral_output

    return None

# ================================
# LEXICON SCORE (unchanged)
# ================================
LEXICON_WEIGHTS = {
    "suicid": 5, "kill myself": 5, "end my life": 5, "i want to die": 5, "worthless": 4,
    "panic": 4, "panic attack": 4, "hopeless": 4, "overwhelmed": 4, "can't cope": 4,
    "anxious": 3, "anxiety": 3, "depressed": 3, "depression": 3, "stress": 3, "stressed": 3,
    "tired": 1.5, "exhausted": 2, "can't sleep": 2, "insomnia": 2, "angry": 1.5, "sad": 2
}

def lexicon_score(text):
    t = text.lower()
    score = 0
    for k, w in LEXICON_WEIGHTS.items():
        if k in t:
            score += w
    if any(k in t for k in ["suicid", "kill myself", "i want to die", "end my life"]):
        score = max(score, 8)
    return int(min(1.0, score / 10) * 100)

# =======================================
# ASK QWEN/MISTRAL FOR JSON SCORE
# =======================================

def ask_model_for_structured_stress(text):
    prompt = f"""
Return STRICT JSON like this:
{{"score":0-100, "evidence":[], "confidence":0.0-1.0}}

Text: {text}
"""
    out = safe_generate(prompt)
    if not out:
        return None

    match = re.search(r"\{[\s\S]*\}", out)
    if not match:
        return None

    try:
        data = json.loads(match.group())
        return {
            "model_score": int(data.get("score", 50)),
            "evidence": data.get("evidence", []),
            "confidence": float(data.get("confidence", 0.5)),
        }
    except:
        return None

# =======================================
# ASK QWEN/MISTRAL FOR INTENSITY
# =======================================

def ask_model_for_intensity(text):
    prompt = f"""
Give JSON only: {{"intensity":0-100, "confidence":0.0-1.0}}

Text: {text}
"""
    out = safe_generate(prompt)
    if not out:
        return None

    match = re.search(r"\{[\s\S]*\}", out)
    if not match:
        return None

    try:
        d = json.loads(match.group())
        return {
            "intensity": int(d.get("intensity", 50)),
            "confidence": float(d.get("confidence", 0.5))
        }
    except:
        return None

# =======================================
# COMBINED STRESS SCORE
# =======================================

def get_stress_level(text):
    lex = lexicon_score(text)
    structured = ask_model_for_structured_stress(text)
    reasoning = ask_model_for_intensity(text)

    # defaults
    model_score = structured["model_score"] if structured else 50
    reasoning_score = reasoning["intensity"] if reasoning else model_score

    final = int(0.45 * model_score + 0.30 * lex + 0.25 * reasoning_score)
    return max(0, min(100, final))

# =======================================
# SUPPORT PROMPT
# =======================================

def build_support_prompt(mode, text):
    return f"""
You are an empathetic mental‑health assistant.
Use user's wording. Give **specific**, non‑generic advice.

Mode: {mode}
User: {text}

Structure:
1. Personalized validation
2. 4 specific coping actions
3. 12–24 hr plan
4. One‑sentence help‑seeking script
5. Warning signs

Include this disclaimer:
----------------------------------------
⚠ Important Disclaimer
This AI may be inaccurate. Please seek medical advice.
Indian Mental Health Helpline: 1800-599-0019
----------------------------------------
"""

# =======================================
# (UI CODE CONTINUES — unchanged layout...)
# You can continue editing or I will extend this file further.
# --- END OF FILE (PART 1) ---
