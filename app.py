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
# Fallback chain: primary → secondary → tertiary
MODEL_CHAIN = [
    "gemini-1.5-flash",      # Primary: fast, free-tier friendly
    "gemini-2.0-flash",      # Secondary: newer, reliable fallback
    "gemini-1.5-flash-8b",   # Tertiary: highest free-tier quota
]
PRIMARY_MODEL  = MODEL_CHAIN[0]
FALLBACK_MODEL = MODEL_CHAIN[1]

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
def safe_generate(prompt, max_retries=2, backoff_base=1.5):
    """
    Try each model in MODEL_CHAIN in order.
    Chain: gemini-1.5-flash → gemini-2.0-flash → gemini-1.5-flash-8b
    """
    _last_error = ""
    for _idx, _model_id in enumerate(MODEL_CHAIN):
        attempt = 0
        while attempt < max_retries:
            try:
                _model = genai.GenerativeModel(_model_id)
                _resp = _model.generate_content(prompt)
                return _resp
            except Exception as _e:
                _last_error = str(_e)
                _msg = _last_error.lower()
                _is_quota = ("429" in _msg or "quota" in _msg
                             or "rate limit" in _msg or "resource_exhausted" in _msg)
                if _is_quota:
                    # Quota hit — move to next model immediately
                    _next = MODEL_CHAIN[_idx + 1] if _idx + 1 < len(MODEL_CHAIN) else None
                    if _next:
                        st.warning(f"⚠️ {_model_id} quota reached — switching to {_next}.")
                    break  # break while loop, outer for-loop picks next model
                elif ("not found" in _msg or "404" in _msg
                      or "invalid" in _msg or "unsupported" in _msg):
                    # Model unavailable — skip to next immediately
                    break
                else:
                    # Transient error — retry with backoff
                    attempt += 1
                    time.sleep(backoff_base ** attempt)
    # All models in chain exhausted
    st.warning(
        "⚠️ All AI models are temporarily unavailable (quota or network issue). "
        "Please wait a minute and try again."
    )
    return None

# -------------------------
# Transcribe audio via Gemini Files API
# -------------------------
def transcribe_audio(audio_bytes, model_id=None):
    # Use first available model in chain for transcription
    _transcribe_model = MODEL_CHAIN[0]
    tmp_path = None
    uploaded_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        uploaded_file = genai.upload_file(tmp_path, mime_type="audio/wav")
        model = genai.GenerativeModel(_transcribe_model)
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
            except Exception:
                pass
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

# -------------------------
# Negation-aware Lexicon scoring
# -------------------------
LEXICON_WEIGHTS = {
    "suicid": 5, "kill myself": 5, "end my life": 5, "i want to die": 5, "worthless": 4,
    "panic": 4, "panic attack": 4, "hopeless": 4, "overwhelmed": 4, "can't cope": 4,
    "anxious": 3, "anxiety": 3, "depressed": 3, "depression": 3, "stress": 3, "stressed": 3,
    "tired": 1.5, "exhausted": 2, "can't sleep": 2, "insomnia": 2, "angry": 1.5, "sad": 2
}

NEGATION_WORDS = {
    "not", "no", "never", "don't", "doesn't", "didn't", "isn't", "aren't",
    "wasn't", "weren't", "can't", "cannot", "won't", "wouldn't", "shouldn't",
    "hardly", "barely", "scarcely"
}

DISTANCING_PHRASES = [
    "my friend", "my sister", "my brother", "my colleague", "someone i know",
    "i read about", "i heard about", "i learned about", "i watched", "a person",
    "they feel", "he feels", "she feels", "in a movie", "in a book", "in the news"
]

def lexicon_score(text):
    t = text.lower()
    tokens = re.split(r'\W+', t)
    score = 0.0

    distancing = any(phrase in t for phrase in DISTANCING_PHRASES)
    dist_factor = 0.25 if distancing else 1.0

    for kw, w in LEXICON_WEIGHTS.items():
        if kw not in t:
            continue

        kw_tokens = kw.split()
        kw_pos = -1
        for i in range(len(tokens) - len(kw_tokens) + 1):
            if tokens[i:i + len(kw_tokens)] == kw_tokens:
                kw_pos = i
                break

        if kw_pos == -1:
            if kw in t:
                kw_pos = 999

        negated = False
        if kw_pos != -1 and kw_pos != 999:
            window_start = max(0, kw_pos - 4)
            preceding_tokens = tokens[window_start:kw_pos]
            if any(neg in preceding_tokens for neg in NEGATION_WORDS):
                negated = True

        if not negated:
            score += w * dist_factor

    crisis_keywords = [
        "suicid", "kill myself", "i want to die", "end my life",
        "want to die", "take my life", "don't want to live",
        "no reason to live", "better off dead", "end it all"
    ]
    has_crisis = any(k in t for k in crisis_keywords)
    if has_crisis:
        crisis_tokens = re.split(r'\W+', t)
        crisis_negated = False
        for k in crisis_keywords:
            if k in t:
                k_tokens = k.split()
                for i in range(len(crisis_tokens) - len(k_tokens) + 1):
                    if crisis_tokens[i:i + len(k_tokens)] == k_tokens:
                        window_start = max(0, i - 4)
                        preceding = crisis_tokens[window_start:i]
                        if any(neg in preceding for neg in NEGATION_WORDS):
                            crisis_negated = True
        if not crisis_negated:
            score = max(score, 9.5)  # crisis floor → minimum 95%

    return int(round(min(1.0, score / 10.0) * 100))

# -------------------------
# Deep reasoning check
# -------------------------
def ask_model_for_intensity(user_text, model_id):
    prompt = (
        "You are a clinical emotional intensity evaluator.\n"
        "CRITICAL RULE: Any text containing suicidal ideation, self-harm, or phrases like"
        " 'want to die', 'kill myself', 'end my life' MUST receive intensity >= 95.\n"
        "Reply with ONLY valid JSON: {\"intensity\": <0-100>, \"confidence\": <0.0-1.0>}.\n\n"
        f"Text: {user_text}\n"
    )
    resp = safe_generate(prompt)
    if not resp:
        return None
    txt = resp.text.strip()
    match = re.search(r"\{[\s\S]*?\}", txt)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        intensity = int(max(0, min(100, int(data.get("intensity", 50)))))
        confidence = float(max(0.0, min(1.0, float(data.get("confidence", 0.5)))))
        return {"intensity": intensity, "confidence": confidence}
    except Exception:
        return None

# -------------------------
# Model structured stress extraction
# -------------------------
def ask_model_for_structured_stress(user_text, model_id):
    prompt = (
        "You are a clinical mental-health risk scoring system.\n"
        "CRITICAL RULE: If the text contains ANY suicidal ideation, self-harm intent, or phrases like 'want to die',"
        " 'kill myself', 'end my life', 'no reason to live', 'better off dead' — "
        "you MUST return score >= 95 and confidence >= 0.95.\n"
        "Return ONLY a single JSON object with keys:\n"
        "score: integer 0-100 (0=no stress, 100=maximum crisis)\n"
        "evidence: array of verbatim phrases from the text that drove the score\n"
        "confidence: float 0.0-1.0\n"
        "emotion: short label (e.g. suicidal, despairing, anxious, overwhelmed)\n\n"
        f"User text:\n{user_text}\n\n"
        "Crisis example: {\"score\":97,\"evidence\":[\"I want to die\"],\"confidence\":0.98,\"emotion\":\"suicidal\"}\n"
        "Normal example: {\"score\":62,\"evidence\":[\"can't sleep\"],\"confidence\":0.80,\"emotion\":\"anxious\"}"
    )
    resp = safe_generate(prompt)
    if not resp:
        return None
    txt = resp.text.strip()
    match = re.search(r'\{[\s\S]*\}', txt)
    if not match:
        cleaned = txt.replace("'", '"')
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if not match:
            return None
    json_text = match.group()
    try:
        data = json.loads(json_text)
    except Exception:
        repaired = re.sub(r'(\w+):', r'"\1":', json_text)
        try:
            data = json.loads(repaired)
        except Exception:
            return None
    score = int(max(0, min(100, int(data.get("score", 50)))))
    evidence = data.get("evidence", [])
    confidence = float(max(0.0, min(1.0, float(data.get("confidence", 0.5)))))
    emotion = str(data.get("emotion", "unknown")).strip()
    return {"model_score": score, "evidence": evidence, "confidence": confidence, "emotion": emotion}

# -------------------------
# Combined scoring
# -------------------------
def get_stress_level(user_text, model_id):
    lex = lexicon_score(user_text)
    structured = ask_model_for_structured_stress(user_text, model_id)
    reasoning = ask_model_for_intensity(user_text, model_id)

    model_score = None
    model_conf = 0.0
    reasoning_score = None
    reasoning_conf = 0.0
    emotion = "unknown"
    evidence = []

    if structured:
        model_score = structured["model_score"]
        model_conf = structured.get("confidence", 0.5)
        emotion = structured.get("emotion", "unknown")
        evidence = structured.get("evidence", [])
    if reasoning:
        reasoning_score = reasoning["intensity"]
        reasoning_conf = reasoning.get("confidence", 0.5)

    w_model_base = 0.45
    w_lex_base = 0.30
    w_reason_base = 0.25

    model_conf_factor = model_conf if model_conf is not None else 0.0
    reason_conf_factor = reasoning_conf if reasoning_conf is not None else 0.0

    w_model = w_model_base * (0.5 + 0.5 * model_conf_factor)
    w_reason = w_reason_base * (0.5 + 0.5 * reason_conf_factor)
    w_lex = 1.0 - (w_model + w_reason)
    if w_lex < 0.1:
        w_lex = 0.1
        total = w_model + w_reason + w_lex
        w_model /= total
        w_reason /= total
        w_lex /= total

    if model_score is None:
        w_model = 0.0
        w_lex = 0.75
        w_reason = 0.25
    if reasoning_score is None:
        if model_score is None:
            w_reason = 0.0
        else:
            w_model += w_reason * 0.6
            w_lex += w_reason * 0.4
            w_reason = 0.0

    ms = model_score if model_score is not None else 50
    rs = reasoning_score if reasoning_score is not None else ms

    final = int(round(ms * w_model + lex * w_lex + rs * w_reason))
    final = max(0, min(100, final))

    # ── Crisis hard-override: suicidal text always scores ≥ 95 ──────────────
    _crisis_override_phrases = [
        "suicid", "kill myself", "i want to die", "end my life",
        "want to die", "take my life", "don't want to live",
        "no reason to live", "better off dead", "end it all"
    ]
    _t = user_text.lower()
    _ct = re.split(r'\W+', _t)
    _crisis_hit = False
    for _kw in _crisis_override_phrases:
        if _kw in _t:
            _kp = _kw.split()
            for _i in range(len(_ct) - len(_kp) + 1):
                if _ct[_i:_i + len(_kp)] == _kp:
                    _prec = _ct[max(0, _i - 4):_i]
                    if not any(_n in _prec for _n in NEGATION_WORDS):
                        _crisis_hit = True
                        break
        if _crisis_hit:
            break
    if _crisis_hit:
        final = max(final, 95)
        if emotion in ("unknown", ""):
            emotion = "suicidal/crisis"
    # ─────────────────────────────────────────────────────────────────────

    meta = {
        "model_score": ms if model_score is not None else None,
        "model_conf": model_conf if model_score is not None else None,
        "lex_score": lex,
        "reasoning_score": rs if reasoning_score is not None else None,
        "weights": {"model": round(w_model, 3), "lex": round(w_lex, 3), "reason": round(w_reason, 3)},
        "emotion": emotion,
        "evidence": evidence
    }
    return final, meta

def get_stress_desc(level):
    if level < 25: return "😌 Minimal Stress — You seem calm."
    if level < 50: return "🙂 Mild Stress — Manageable tension."
    if level < 75: return "😟 Moderate Stress — Consider coping tools."
    if level < 90: return "😰 High Stress — Strong distress detected."
    return "🚨 CRISIS LEVEL — Please call KIRAN 1800-599-0019 immediately."

# -------------------------
# NEW FEATURE: topic detection
# -------------------------
def detect_topics(text):
    text_lower = text.lower()
    found = defaultdict(list)
    for topic, keywords in TOPIC_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                found[topic].append(kw)
    return dict(found)

def highlight_detected_phrases(text, topics_found):
    highlighted = text
    all_keywords = []
    for kws in topics_found.values():
        all_keywords.extend(kws)
    all_keywords = sorted(set(all_keywords), key=len, reverse=True)
    for kw in all_keywords:
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        highlighted = pattern.sub(lambda m: f"`{m.group(0)}`", highlighted)
    return highlighted

# -------------------------
# NEW FEATURE: trend scoring
# -------------------------
def compute_trends(history):
    if not history:
        return None

    today = datetime.now()
    last_7 = []
    prev_7 = []
    last_30 = []
    prev_30 = []

    for item in history:
        try:
            dt = datetime.fromisoformat(item["timestamp"])
            score = item["score"]
            delta = today - dt

            if delta.days < 7:
                last_7.append(score)
            elif 7 <= delta.days < 14:
                prev_7.append(score)

            if delta.days < 30:
                last_30.append(score)
            elif 30 <= delta.days < 60:
                prev_30.append(score)
        except Exception:
            continue

    result = {}
    if last_7:
        avg7 = sum(last_7) / len(last_7)
        result["avg_7"] = round(avg7, 1)
        if prev_7:
            prev_avg7 = sum(prev_7) / len(prev_7)
            if prev_avg7 > 0:
                result["change_7"] = round(((avg7 - prev_avg7) / prev_avg7) * 100, 1)

    if last_30:
        avg30 = sum(last_30) / len(last_30)
        result["avg_30"] = round(avg30, 1)
        if prev_30:
            prev_avg30 = sum(prev_30) / len(prev_30)
            if prev_avg30 > 0:
                result["change_30"] = round(((avg30 - prev_avg30) / prev_avg30) * 100, 1)
    return result

# -------------------------
# Support message builder (language-aware)
# -------------------------
def build_support_prompt(mode, text, lang="English"):
    lang_instruction = (
        f"Respond entirely in {lang}. "
        if lang != "English"
        else ""
    )
    _crisis_phrases = [
        "suicid", "kill myself", "i want to die", "end my life",
        "want to die", "take my life", "don't want to live",
        "no reason to live", "better off dead", "end it all"
    ]
    _is_crisis = any(p in text.lower() for p in _crisis_phrases)
    _crisis_block = ""
    if _is_crisis:
        _crisis_block = """
## 🚨 IMMEDIATE CRISIS RESPONSE — READ THIS FIRST
This message contains suicidal or self-harm ideation. Before anything else:
1. **Call KIRAN helpline NOW: 1800-599-0019** (free, 24/7, multilingual)
2. **Do NOT be alone** — go to a trusted person, family member, or friend right now
3. **If in immediate danger**, call emergency services (112) or go to the nearest hospital
Write this as the VERY FIRST section in bold with maximum urgency.
"""
    return f"""
You are a deeply empathetic, clinically-informed mental-health assistant.
{lang_instruction}
STRICT RULES:
- Quote the user's EXACT phrases when validating — never paraphrase generically
- Each coping action MUST be 4-6 sentences: explain WHAT it is, HOW to do it step-by-step right now, and WHY it directly helps this person's specific situation
- Never write one-liners for coping actions — depth and personalization are mandatory
- For crisis/suicidal content, ALWAYS show emergency resources as the very first section
{_crisis_block}
User text:
{text}

Mode: {mode}

Produce a full structured Markdown response with ALL sections below:

### 💬 Validation
Write 3-4 sentences quoting the user's exact words. Reflect the emotional weight they carry. Make them feel genuinely heard.

### 🛠️ 4 Detailed Coping Actions
For EACH of the 4 actions:
- Give a descriptive title
- Write 4-6 sentences: what the technique is, step-by-step instructions to do it right now, and specifically why it addresses what this person described (quote their words)

### 📅 Immediate 12-24 Hour Action Plan
List 4-5 specific, time-bound actions for the next 24 hours. Be precise, not generic.

### 🗣️ How to Ask a Loved One for Help
A complete 2-3 sentence script the user can say word-for-word to a trusted person.

### ⚠️ Warning Signs & When to Seek Help
List 5-6 specific warning signs. State clearly when to call a professional or helpline.

End with the exact disclaimer block (do not vary):
----------------------------------------
⚠ **Important Disclaimer**
This AI may be inaccurate. Please seek medical advice from a professional.
Talk to your loved ones for support.
**Indian Mental Health Helpline:** 1800-599-0019
**Vandrevala Foundation:** 1860-2662-345 (24/7)
**iCall:** 9152987821
----------------------------------------
"""

# -------------------------
# Adaptive suggestions
# -------------------------
def get_adaptive_suggestions(level):
    if level < 30:
        return {
            "band": "Low",
            "items": [
                "Read a short note on how normal stress works in the body.",
                "Take a 5-minute stretch or hydration break.",
                "Do a quick check-in tonight: what went well today?"
            ]
        }
    elif level < 70:
        return {
            "band": "Moderate",
            "items": [
                "Use the breathing exercise for 3–5 cycles.",
                "Try a grounding exercise like 5-4-3-2-1.",
                "Break your biggest problem into one tiny next step."
            ]
        }
    else:
        return {
            "band": "High",
            "items": [
                "Pause and contact a trusted person today.",
                "Use breathing + grounding before making major decisions.",
                "If distress gets stronger or you feel unsafe, contact a helpline immediately."
            ]
        }

# -------------------------
# Breathing widget renderer
# -------------------------
def show_breathing_widget():
    st.markdown("""
    <div class="breathing-widget">
        <h4>🌬️ Breathing Exercise — Try This Now</h4>
        <div class="breath-circle">
            <div class="breath-inner">Breathe<br>In &amp; Out</div>
        </div>
        <div class="breath-steps">
            ● Inhale slowly — <strong>4 seconds</strong><br>
            ● Hold gently — <strong>4 seconds</strong><br>
            ● Exhale fully — <strong>6 seconds</strong><br>
            ● Repeat 4–6 cycles
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------
# Grounding / relaxation tools
# -------------------------
def show_toolkit():
    st.markdown('<div class="section-title">🧰 Toolkit of Exercises</div>', unsafe_allow_html=True)
    t1, t2, t3 = st.tabs(["5-4-3-2-1 Grounding", "Muscle Relaxation", "Journal Prompt"])

    with t1:
        st.markdown("""
**5-4-3-2-1 Grounding**
- 5 things you can see
- 4 things you can feel
- 3 things you can hear
- 2 things you can smell
- 1 thing you can taste
""")

    with t2:
        st.markdown("""
**Progressive Muscle Relaxation**
1. Tighten your shoulders for 5 seconds, then release.  
2. Clench your fists for 5 seconds, then release.  
3. Tighten your legs for 5 seconds, then release.  
4. Notice the difference between tension and relaxation.
""")

    with t3:
        prompts = [
            "What is the one thing bothering me most right now?",
            "What do I need today instead of what I think I 'should' do?",
            "If I spoke to myself like a friend, what would I say?"
        ]
        day_index = datetime.now().day % len(prompts)
        st.markdown(f"**Prompt of the Day:** {prompts[day_index]}")
        st.text_area("Write your answer here", height=120, key="journal_prompt_box")

# -------------------------
# Dashboard rendering
# -------------------------
def show_dashboard(history, journal_entries):
    st.markdown('<div class="section-title">📈 Personal Dashboard</div>', unsafe_allow_html=True)
    if not history:
        st.info("No saved history yet. Analyze at least one entry to build your dashboard.")
        return

    scores = []
    dates = []
    emotions = []
    topics = []

    for item in history[-30:]:
        scores.append(item.get("score", 0))
        dates.append(item.get("timestamp", "")[:10])
        emotions.append(item.get("emotion", "unknown"))
        topics.extend(item.get("topics", []))

    chart_data = {"Date": dates, "Stress Score": scores}
    st.line_chart(chart_data, x="Date", y="Stress Score")

    emotion_counts = Counter([e for e in emotions if e and e != "unknown"]).most_common(3)
    topic_counts = Counter(topics).most_common(3)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Top 3 Recurring Emotions**")
        if emotion_counts:
            for emotion, cnt in emotion_counts:
                st.markdown(f"- {emotion}: {cnt}")
        else:
            st.markdown("- Not enough data yet")

    with c2:
        st.markdown("**Most Common Stress Topics**")
        if topic_counts:
            for topic, cnt in topic_counts:
                st.markdown(f"- {topic}: {cnt}")
        else:
            st.markdown("- Not enough data yet")

    if journal_entries:
        st.markdown("**Recent Journal Tags**")
        recent_tags = []
        for entry in journal_entries[-10:]:
            recent_tags.extend(entry.get("tags", []))
        tag_counts = Counter(recent_tags).most_common(6)
        if tag_counts:
            st.markdown(" ".join([f"<span class='pill'>{tag} ({cnt})</span>" for tag, cnt in tag_counts]), unsafe_allow_html=True)

# -------------------------
# Reminder banner
# -------------------------
def show_reminder_banner(history):
    if not history:
        return
    try:
        last_dt = datetime.fromisoformat(history[-1]["timestamp"])
        days_gap = (datetime.now() - last_dt).days
        if days_gap >= 3:
            st.info(f"🔔 You haven’t checked in for {days_gap} days. Want a quick 1-minute check-in?")
    except Exception:
        pass

# -------------------------
# UI HEADER
# -------------------------
st.markdown("""
<div class="main-header">
    <h1>🧠 Mental Health AI</h1>
    <p>Premium stress detector & crisis support tool</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="
    background:rgba(49,24,94,0.55);
    padding:1rem 1.4rem;
    border-radius:14px;
    color:#e8d6ff;
    margin-top:-1rem;
    margin-bottom:1.5rem;
    box-shadow:0 4px 14px #31185e50;
    font-size:0.95rem;
    font-style:italic;">
"If you're going through hell, keep going."<br>
"If there is something that means a lot to you, do not postpone it."
</div>
""", unsafe_allow_html=True)

# -------------------------
# Load persisted data
# -------------------------
history_data = load_json_file(HISTORY_FILE, [])
journal_data = load_json_file(JOURNAL_FILE, [])

# -------------------------
# SIDEBAR
# -------------------------
with st.sidebar:
    st.write("## Settings")
    st.info("🤖 **AI Engine**\n\nPrimary: Gemini 1.5 Flash\nFallback: Gemini 2.5 Flash (auto)")
    model_id = PRIMARY_MODEL  # kept for audio transcription compatibility
    mode = st.radio("Analysis Mode", ["Crisis Detection", "Emotional Support", "Risk Assessment"])

    st.write("### 🌐 Language")
    chosen_lang_label = st.selectbox("Response Language", list(LANGUAGES.keys()), index=0)
    selected_lang = LANGUAGES[chosen_lang_label]

    st.write("### Emergency Resources")
    st.info("**KIRAN:** 1800-599-0019\n**Vandrevala:** 1860-2662-345\n**iCall:** 9152987821")

    st.write("### 🔐 Data & Privacy")
    st.caption("Stored locally: text summary, score, timestamp, tags, emotion, topics.")
    st.caption("Use 'Clear my saved data' to remove local history and journal entries.")
    if st.button("🗑 Clear my saved data"):
        save_json_file(HISTORY_FILE, [])
        save_json_file(JOURNAL_FILE, [])
        st.success("Saved local data cleared.")

# -------------------------
# Session state init
# -------------------------
if "voice_transcript" not in st.session_state:
    st.session_state["voice_transcript"] = ""
if "last_request_time" not in st.session_state:
    st.session_state["last_request_time"] = 0.0
if "mood_prefill" not in st.session_state:
    st.session_state["mood_prefill"] = ""
if "last_analysis_result" not in st.session_state:
    st.session_state["last_analysis_result"] = None

# -------------------------
# Reminder
# -------------------------
show_reminder_banner(history_data)

# -------------------------
# MAIN UI
# -------------------------
col1, col2 = st.columns([2, 1])

with col1:
    app_tabs = st.tabs(["✍️ Analyze", "📈 Dashboard", "🧾 Journal", "🧰 Tools"])

    with app_tabs[0]:
        tab1, tab2 = st.tabs(["✍️ Text", "🎤 Voice"])
        input_text = ""

        with tab1:
            st.markdown('<div class="info-card"><h3>Write your feelings</h3>', unsafe_allow_html=True)

            st.markdown("**Quick Mood Tags** — tap to pre-fill:")
            mood_cols = st.columns(len(MOOD_TAGS))
            for idx, (tag_label, tag_text) in enumerate(MOOD_TAGS.items()):
                with mood_cols[idx]:
                    if st.button(tag_label, key=f"mood_{idx}"):
                        st.session_state["mood_prefill"] = tag_text

            prefill_value = st.session_state.get("mood_prefill", "")
            input_text = st.text_area(
                "Describe your feelings.",
                value=prefill_value,
                height=160,
                key="text_input_area"
            )
            if prefill_value:
                st.session_state["mood_prefill"] = ""

            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown('<div class="info-card"><h3>Speak your mind</h3>', unsafe_allow_html=True)
            audio_data = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹ Stop")

            if audio_data and audio_data.get("bytes"):
                st.audio(audio_data["bytes"], format="audio/wav")

                with st.spinner("🔄 Transcribing your voice with Gemini..."):
                    transcript = transcribe_audio(audio_data["bytes"], model_id)

                if transcript:
                    st.session_state["voice_transcript"] = transcript
                    st.success("✅ Voice transcribed successfully!")
                    st.markdown(
                        f'<div class="transcript-box">📝 <strong>Transcript:</strong> {transcript}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.warning("⚠️ Could not transcribe audio. Please try again or use the text tab.")
                    st.session_state["voice_transcript"] = ""

            elif st.session_state.get("voice_transcript"):
                st.markdown(
                    f'<div class="transcript-box">📝 <strong>Last Transcript:</strong> {st.session_state["voice_transcript"]}</div>',
                    unsafe_allow_html=True
                )

            st.markdown('</div>', unsafe_allow_html=True)

        if not input_text.strip() and st.session_state.get("voice_transcript"):
            input_text = st.session_state["voice_transcript"]

        now = time.time()
        elapsed = now - st.session_state["last_request_time"]
        cooldown_seconds = 5
        on_cooldown = elapsed < cooldown_seconds

        if on_cooldown:
            remaining = int(cooldown_seconds - elapsed) + 1
            st.markdown(
                f'<div class="cooldown-bar">⏳ Please wait {remaining}s before analyzing again.</div>',
                unsafe_allow_html=True
            )

        analyze_clicked = st.button(
            "🔍 Analyze & Get Support",
            use_container_width=True,
            disabled=on_cooldown
        )

        if analyze_clicked and input_text.strip() and not on_cooldown:
            st.session_state["last_request_time"] = time.time()

            with st.spinner("Analyzing..."):
                final_level, meta = get_stress_level(input_text, model_id)

                st.markdown(f"""
                <div class="stress-meter-container">
                    <div class="circular-gauge">
                        <div class="gauge-inner">
                            <div class="stress-percentage">{final_level}%</div>
                            <div class="stress-label">Stress</div>
                        </div>
                    </div>
                    <div style="color:#bb86fc;margin-top:10px;">{get_stress_desc(final_level)}</div>
                </div>
                """, unsafe_allow_html=True)

                if final_level > 70:
                    show_breathing_widget()

                topics_found = detect_topics(input_text)
                highlighted_text = highlight_detected_phrases(input_text, topics_found)

                st.markdown('<div class="feature-card">', unsafe_allow_html=True)
                st.markdown("### 🧠 Context-Aware Trigger Detection")
                if topics_found:
                    st.markdown(f"**Detected phrases:** {highlighted_text}")
                    st.markdown("**Likely stress areas:**")
                    for topic, kws in topics_found.items():
                        st.markdown(f"- **{topic}**: {', '.join(sorted(set(kws)))}")
                else:
                    st.markdown("No strong topic category detected from the current input.")
                st.markdown('</div>', unsafe_allow_html=True)

                support_prompt = build_support_prompt(mode, input_text, lang=selected_lang)
                response = safe_generate(support_prompt)

                st.markdown('<div class="response-area">', unsafe_allow_html=True)
                if response:
                    st.markdown("### AI Support\n" + response.text)
                else:
                    fallback_text = f"""
### AI Support (Fallback)
- **Validation:** I hear that you're saying: "{input_text[:120]}..." — that sounds distressing and important.
- **Immediate steps (tailored):**
  1. Take 3 minutes of diaphragmatic breathing (inhale 4s, hold 4s, exhale 6s).
  2. Write the single most urgent problem and one tiny step you can take now.
  3. Reach out to one trusted person with this exact line: "I need to talk — I haven't been okay lately."
- **12-24 hour plan:** sleep hygiene, short walk outside, limit caffeine, connect with someone.
- **When to seek help:** if you have thoughts of harming yourself, call a helpline immediately.
----------------------------------------
⚠ **Important Disclaimer**
This AI may be inaccurate. Please seek medical advice from a professional.
Talk to your loved ones for support.
**Indian Mental Health Helpline:** 1800-599-0019
----------------------------------------
"""
                    st.markdown(fallback_text)
                st.markdown('</div>', unsafe_allow_html=True)

                adaptive = get_adaptive_suggestions(final_level)
                st.markdown('<div class="feature-card">', unsafe_allow_html=True)
                st.markdown(f"### 🎯 Adaptive Suggestions ({adaptive['band']} Stress)")
                for item in adaptive["items"]:
                    st.markdown(f"- {item}")
                st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('<div class="feature-card">', unsafe_allow_html=True)
                st.markdown("### ✅ Goal & Habit Cards")
                goal1 = st.checkbox("Drink a glass of water", key=f"goal_water_{time.time()}")
                goal2 = st.checkbox("Take a 5-minute walk", key=f"goal_walk_{time.time()}")
                goal3 = st.checkbox("Text one trusted person", key=f"goal_text_{time.time()}")
                completed = sum([goal1, goal2, goal3])
                st.markdown(f"**Completed today:** {completed}/3")
                st.markdown('</div>', unsafe_allow_html=True)

                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "score": final_level,
                    "emotion": meta.get("emotion", "unknown"),
                    "topics": list(topics_found.keys()),
                    "input_preview": input_text[:180]
                }
                append_history_entry(entry)
                history_data = load_json_file(HISTORY_FILE, [])

                trends = compute_trends(history_data)
                if trends:
                    st.markdown('<div class="feature-card">', unsafe_allow_html=True)
                    st.markdown("### 📊 Trend-Based Risk Scoring")
                    if "avg_7" in trends:
                        st.markdown(f"- **7-day average:** {trends['avg_7']}")
                    if "change_7" in trends:
                        direction = "higher" if trends["change_7"] > 0 else "lower"
                        st.markdown(f"- Your stress is **{abs(trends['change_7'])}% {direction}** than last week.")
                    if "avg_30" in trends:
                        st.markdown(f"- **30-day average:** {trends['avg_30']}")
                    if "change_30" in trends:
                        direction = "higher" if trends["change_30"] > 0 else "lower"
                        st.markdown(f"- Your stress is **{abs(trends['change_30'])}% {direction}** than the previous 30-day period.")
                    st.markdown('</div>', unsafe_allow_html=True)

                st.session_state["last_analysis_result"] = {
                    "score": final_level,
                    "emotion": meta.get("emotion", "unknown"),
                    "topics": list(topics_found.keys()),
                    "text": input_text
                }

            st.session_state["voice_transcript"] = ""

    with app_tabs[1]:
        show_dashboard(history_data, journal_data)

    with app_tabs[2]:
        st.markdown('<div class="section-title">🧾 Journaling & Tags</div>', unsafe_allow_html=True)
        journal_text = st.text_area("Write a journal entry", height=140, key="journal_entry_text")
        tag_options = ["Work", "Family", "Exams", "Health", "Finances", "Relationships"]
        selected_tags = st.multiselect("Tags", tag_options)
        if st.button("💾 Save Journal Entry"):
            if journal_text.strip():
                append_journal_entry({
                    "timestamp": datetime.now().isoformat(),
                    "text": journal_text.strip(),
                    "tags": selected_tags
                })
                st.success("Journal entry saved.")
                journal_data = load_json_file(JOURNAL_FILE, [])
            else:
                st.warning("Write something before saving.")

        st.markdown("### Recent Entries")
        if journal_data:
            for item in reversed(journal_data[-5:]):
                st.markdown(f"**{item['timestamp'][:16]}**")
                st.markdown(item["text"])
                if item.get("tags"):
                    st.markdown(" ".join([f"<span class='pill'>{t}</span>" for t in item["tags"]]), unsafe_allow_html=True)
                st.markdown("---")
        else:
            st.info("No journal entries yet.")

    with app_tabs[3]:
        show_toolkit()

with col2:
    st.markdown('<div class="info-card"><h3>Why Mindful?</h3>- Modern\n- Gemini 2.5 models\n- 24/7 support</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-card"><h3>Modes</h3>- Crisis Detection\n- Emotional Support\n- Risk Assessment</div>', unsafe_allow_html=True)
    st.markdown('<div class="emergency-banner">🚨 IN CRISIS? CALL KIRAN 1800-599-0019 🚨</div>', unsafe_allow_html=True)

    if st.session_state.get("last_analysis_result"):
        st.markdown('<div class="info-card"><h3>Last Analysis Snapshot</h3>', unsafe_allow_html=True)
        lr = st.session_state["last_analysis_result"]
        st.markdown(f"- **Score:** {lr['score']}")
        st.markdown(f"- **Emotion:** {lr['emotion']}")
        if lr["topics"]:
            st.markdown(f"- **Topics:** {', '.join(lr['topics'])}")
        st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer-dark">
<p><strong>Disclaimer:</strong> This tool does not replace professional help.
If you are in crisis, contact emergency services or the KIRAN helpline (1800-599-0019).</p>
</div>
""", unsafe_allow_html=True)
