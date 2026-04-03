# app.py
# Streamlit App for Mental Health Stress Detection (Text + Voice)

import streamlit as st
from transformers import pipeline
from io import BytesIO
import textwrap
import os
import re
import hashlib

# ─── Optional API libraries (won't crash if not installed) ────────────────────
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

try:
    from groq import Groq as GroqClient
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from openai import OpenAI as OpenAIClient
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False

# Try loading whisper for audio transcription
try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

st.set_page_config(page_title="Mental Health Stress Detector", page_icon="🧠", layout="centered")
st.title("🧠 Mental Health Stress Detector – Text & Voice")
st.caption("Detect stress levels (0–100%) using AI + Provide Supportive Tips")

# ─── Fallback Chain Constants ─────────────────────────────────────────────────
VISION_MODEL_CHAIN = [
    "gemini-2.5-flash",   # PRIMARY — best quality
    "gemini-1.5-flash",   # FALLBACK — higher quota
    "gemini-1.5-flash-8b" # LAST RESORT
]
OPENROUTER_TEXT_MODEL  = "meta-llama/llama-3.3-70b-instruct:free"
GROQ_TEXT_MODELS = [
    "llama-3.1-8b-instant",   # 14,400 RPD free — fastest
    "llama-3.3-70b-versatile", # 1,000 RPD free — highest quality
]

# ─── Secret Reader (works on Streamlit Cloud AND localhost) ───────────────────
def _get_secret(name: str) -> str:
    try:
        if hasattr(st, "secrets") and name in st.secrets:
            val = st.secrets[name]
            if val:
                return str(val).strip()
    except Exception:
        pass
    try:
        if hasattr(st, "secrets"):
            val = st.secrets.get(name, "")
            if val:
                return str(val).strip()
    except Exception:
        pass
    val = os.environ.get(name, "")
    return val.strip() if val else ""

# ─── Configure Gemini (optional — app works without it) ──────────────────────
if GENAI_AVAILABLE:
    _gkey = _get_secret("GEMINI_API_KEY")
    if _gkey:
        try:
            genai.configure(api_key=_gkey)
        except Exception:
            pass

# ─── Client factories ─────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _get_groq_client():
    if not GROQ_AVAILABLE:
        return None
    key = _get_secret("GROQ_API_KEY")
    if not key:
        return None
    try:
        return GroqClient(api_key=key)
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def _get_openrouter_client():
    if not OPENAI_SDK_AVAILABLE:
        return None
    key = _get_secret("OPENROUTER_API_KEY")
    if not key:
        return None
    try:
        return OpenAIClient(base_url="https://openrouter.ai/api/v1", api_key=key)
    except Exception:
        return None

_groq_client      = _get_groq_client()
_openrouter_client = _get_openrouter_client()

# ─── Response Cache ───────────────────────────────────────────────────────────
_RESPONSE_CACHE: dict = {}
_CACHE_MAX = 100

def _make_cache_key(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

def _cache_get(key: str):
    return _RESPONSE_CACHE.get(key)

def _cache_set(key: str, value):
    global _RESPONSE_CACHE
    if len(_RESPONSE_CACHE) >= _CACHE_MAX:
        oldest = next(iter(_RESPONSE_CACHE))
        del _RESPONSE_CACHE[oldest]
    _RESPONSE_CACHE[key] = value

# ─── Quota / Transient Error Detector ────────────────────────────────────────
def _is_quota_err(e) -> bool:
    s = str(e).lower()
    return any(x in s for x in [
        "429", "quota", "rate limit", "resourceexhausted", "too many", "overloaded"
    ])

# ─── Single-model Gemini call with back-off ───────────────────────────────────
def _retry_generate(model_id: str, prompt: str, max_retries: int = 3) -> str:
    """Calls one Gemini model with retries. Quota errors skip immediately."""
    import time as _time
    if not GENAI_AVAILABLE:
        raise RuntimeError("google-generativeai not installed")
    last_err = None
    for attempt in range(max_retries):
        try:
            m = genai.GenerativeModel(model_id)
            resp = m.generate_content(prompt)
            text = getattr(resp, "text", "") or ""
            if text.strip():
                return text
            raise ValueError("Empty response from model")
        except Exception as e:
            last_err = e
            is_quota = _is_quota_err(e)
            is_transient = any(x in str(e).lower() for x in
                               ["500", "503", "internal", "unavailable",
                                "timeout", "deadline", "empty", "connection"])
            if is_quota:
                break  # Don't retry — move to next model immediately
            if is_transient and attempt < max_retries - 1:
                _time.sleep(2 ** attempt)  # 1s → 2s → 4s
                continue
            break
    raise last_err

# ─── Ultra-stable text fallback chain ─────────────────────────────────────────
def gemini_text_with_fallback(prompt: str) -> tuple:
    """
    Ultra-stable text call:
      1. Groq Llama-3.1-8B  (14,400 free RPD — fastest)
      2. Groq Llama-3.3-70B (1,000 free RPD — best quality)
      3. OpenRouter Llama-70B (free tier)
      4. Gemini 2.5 Flash → 1.5 Flash → 1.5 Flash-8B
    Returns (text, model_used).
    """
    import time as _time

    # 1. Groq
    gc = _groq_client or _get_groq_client()
    if gc:
        for gm in GROQ_TEXT_MODELS:
            for attempt in range(3):
                try:
                    resp = gc.chat.completions.create(
                        model=gm,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=1024,
                        temperature=0.5,
                        timeout=20,
                    )
                    text = (resp.choices[0].message.content or "").strip()
                    if text:
                        return text, f"Groq/{gm}"
                except Exception as e:
                    if _is_quota_err(e) and attempt < 2:
                        _time.sleep(2 * attempt)
                        continue
                    break

    # 2. OpenRouter
    or_live = _openrouter_client or _get_openrouter_client()
    if or_live:
        for attempt in range(2):
            try:
                resp = or_live.chat.completions.create(
                    model=OPENROUTER_TEXT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    timeout=25,
                )
                text = (resp.choices[0].message.content or "").strip()
                if text:
                    return text, "OpenRouter/Llama-70B"
            except Exception as e:
                if _is_quota_err(e) and attempt < 1:
                    _time.sleep(2)
                    continue
                break

    # 3. Gemini fallback chain
    for model_id in ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-flash-8b"]:
        try:
            text = _retry_generate(model_id, prompt, max_retries=3)
            return text, model_id
        except Exception as e:
            if _is_quota_err(e):
                _time.sleep(2)
            continue

    raise RuntimeError(
        "⏳ All AI models are temporarily at capacity. "
        "Please wait 60 seconds and try again."
    )

# ─── Load emotion model ───────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    return pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

emotion_model = load_model()


def get_stress_score(results):
    prob = {r['label']: r['score'] for r in results}
    score = prob.get("anger", 0) + prob.get("fear", 0) + prob.get("sadness", 0)
    return int(score * 100)


def get_tips(score):
    if score < 40:
        return (
            "• Practice deep breathing (4s inhale, 4s exhale).\n"
            "• Take a short walk or stretch.\n"
            "• Write your thoughts in a journal."
        )
    elif score < 70:
        return (
            "• Try grounding: 5 things you see, 4 you can touch, 3 you hear.\n"
            "• Talk to a trusted friend/family.\n"
            "• Listen to relaxing music or do guided breathing."
        )
    else:
        return (
            "• Take slow deep breaths and sit somewhere calm.\n"
            "• Stay connected with someone you trust.\n"
            "• Consider reaching out for professional help."
        )


def explain(text, score):
    if score < 40:
        base = "You seem to be experiencing mild stress or worry."
    elif score < 70:
        base = "You seem to be dealing with moderate stress or emotional difficulty."
    else:
        base = "You seem to be showing high signs of emotional stress or distress."

    short = textwrap.shorten(text, width=120, placeholder="...")
    return f"{base} Example from your message: '{short}'"


def transcribe_audio(data):
    if not WHISPER_AVAILABLE:
        return None, "Whisper not installed. Cannot transcribe audio."

    try:
        model = whisper.load_model("small")
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(data)
            temp_path = f.name
        result = model.transcribe(temp_path)
        os.remove(temp_path)
        return result.get("text", "").strip(), None
    except Exception as e:
        return None, str(e)


# ─── AI-Enhanced Tips (uses fallback chain, falls back to static tips) ────────
def get_ai_tips(user_text: str, score: int) -> tuple:
    """
    Returns (tips_text, model_used).
    Tries the AI fallback chain for personalized tips.
    If all models fail, silently falls back to the original static get_tips().
    """
    cache_key = _make_cache_key(f"tips:{score}:{user_text[:200]}")
    cached = _cache_get(cache_key)
    if cached:
        return cached

    if score < 40:
        level = "mild"
    elif score < 70:
        level = "moderate"
    else:
        level = "high"

    prompt = (
        f"A person shared the following about how they feel:\n\"{user_text[:400]}\"\n\n"
        f"Their stress score is {score}% ({level} stress level).\n\n"
        "Give them 3 short, warm, and practical stress-relief tips personalized to what they shared. "
        "Format as bullet points starting with •. Keep each tip under 2 sentences. "
        "Do NOT mention diagnosis, medication, or act as a doctor. "
        "Be compassionate and human."
    )

    try:
        text, model_used = gemini_text_with_fallback(prompt)
        result = (text.strip(), model_used)
        _cache_set(cache_key, result)
        return result
    except Exception:
        # Silent fallback to original static tips — user never sees an error
        return get_tips(score), "local"


# ─── Render results helper (avoids duplicating UI code) ──────────────────────
def render_results(user_text: str):
    results = emotion_model(user_text)[0]
    score = get_stress_score(results)
    explanation = explain(user_text, score)

    st.subheader("Stress Level")
    st.metric("Stress Score", f"{score}%")
    st.progress(score)

    st.subheader("Explanation")
    st.write(explanation)

    st.subheader("Tips to Relieve Stress")
    tips, model_used = get_ai_tips(user_text, score)
    st.write(tips)
    if model_used and model_used != "local":
        st.caption(f"✨ Tips personalized by AI ({model_used})")

    st.subheader("Important")
    st.write("I am not a medical professional. Please seek medical advice if needed.")
    st.write("Talk to your loved ones — sharing how you feel can help.")
    st.write("If you're overwhelmed, call the helpline: **1800-599-0019**")


# ─── Tabs ──────────────────────────────────────────────────────────────────────
text_tab, audio_tab = st.tabs(["Text Input", "Voice Input"])

# TEXT INPUT
with text_tab:
    user_text = st.text_area("Describe how you're feeling:")
    if st.button("Analyze Text"):
        if user_text.strip():
            render_results(user_text)
        else:
            st.warning("Please enter some text.")

# AUDIO INPUT
with audio_tab:
    file = st.file_uploader("Upload audio (wav/mp3/m4a)", type=["wav", "mp3", "m4a", "ogg"])
    if file:
        st.audio(file)

        if st.button("Transcribe & Analyze Audio"):
            data = file.read()
            text, err = transcribe_audio(data)

            if err:
                st.error("Transcription failed: " + err)
            else:
                st.success("Audio Transcribed:")
                st.write(text)
                render_results(text)
