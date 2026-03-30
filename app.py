import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import re
import json
import time
import tempfile
import os

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

    /* ---- Breathing Widget ---- */
    @keyframes breathe {
        0%   { transform: scale(1);   box-shadow: 0 0 0px #00fff580; }
        40%  { transform: scale(1.45); box-shadow: 0 0 38px #00fff5cc; }
        60%  { transform: scale(1.45); box-shadow: 0 0 38px #00fff5cc; }
        100% { transform: scale(1);   box-shadow: 0 0 0px #00fff580; }
    }
    @keyframes breatheText {
        0%,100% { opacity:0.5; content:"Breathe In…"; }
        40%,60% { opacity:1;   content:"Hold…"; }
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
</style>
""", unsafe_allow_html=True)

# ====== MODEL NAMES ======
MODEL_NAMES = {
    "Gemini 2.5 Pro": "models/gemini-2.5-pro",
    "Gemini 2.5 Flash": "models/gemini-2.5-flash"
}
SIDEBAR_MODEL_KEYS = list(MODEL_NAMES.keys())

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

# -------------------------
# Safe generate wrapper
# -------------------------
def safe_generate(model_id, prompt, max_retries=2, backoff_base=2):
    attempt = 0
    while attempt <= max_retries:
        try:
            model = genai.GenerativeModel(model_id)
            return model.generate_content(prompt)
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "quota" in msg or "rate limit" in msg:
                if model_id == "models/gemini-2.5-flash":
                    return None
                st.warning("⚠️ Model quota/rate limit reached. Switching to Gemini 2.5 Flash as fallback.")
                try:
                    model_id = "models/gemini-2.5-flash"
                    model = genai.GenerativeModel(model_id)
                    return model.generate_content(prompt)
                except Exception:
                    return None
            attempt += 1
            time.sleep(backoff_base ** attempt * 0.5)
    st.error("AI request failed. Using offline fallback where possible.")
    return None

# -------------------------
# Transcribe audio via Gemini Files API
# -------------------------
def transcribe_audio(audio_bytes, model_id):
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
            # multi-word phrase match fallback
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

    crisis_keywords = ["suicid", "kill myself", "i want to die", "end my life"]
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
            score = max(score, 8.0)

    return int(round(min(1.0, score / 10.0) * 100))

# -------------------------
# Deep reasoning check
# -------------------------
def ask_model_for_intensity(user_text, model_id):
    prompt = (
        "You are an evaluator that gives a concise numeric emotional intensity score.\n"
        "Reply with ONLY valid JSON: {\"intensity\": <0-100>, \"confidence\": <0.0-1.0>}.\n\n"
        f"Text: {user_text}\n"
    )
    resp = safe_generate(model_id, prompt)
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
        "Return ONLY a single JSON object with keys:\n"
        "score: integer 0-100\n"
        "evidence: array of brief verbatim phrases from the user's text\n"
        "confidence: float 0.0-1.0\n\n"
        f"User text:\n{user_text}\n\n"
        "Example: {\"score\":72, \"evidence\": [\"I can't sleep\"], \"confidence\":0.83}"
    )
    resp = safe_generate(model_id, prompt)
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
    return {"model_score": score, "evidence": evidence, "confidence": confidence}

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

    if structured:
        model_score = structured["model_score"]
        model_conf = structured.get("confidence", 0.5)
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

    meta = {
        "model_score": ms if model_score is not None else None,
        "model_conf": model_conf if model_score is not None else None,
        "lex_score": lex,
        "reasoning_score": rs if reasoning_score is not None else None,
        "weights": {"model": round(w_model, 3), "lex": round(w_lex, 3), "reason": round(w_reason, 3)}
    }
    return final, meta

def get_stress_desc(level):
    if level < 25: return "😌 Minimal Stress — You seem calm."
    if level < 50: return "🙂 Mild Stress — Manageable tension."
    if level < 75: return "😟 Moderate Stress — Consider coping tools."
    return "😰 High Stress — Strong distress detected."

# -------------------------
# Support message builder (language-aware)
# -------------------------
def build_support_prompt(mode, text, lang="English"):
    lang_instruction = (
        f"Respond entirely in {lang}. "
        if lang != "English"
        else ""
    )
    return f"""
You are a deeply empathetic professional mental-health assistant.
{lang_instruction}Use the user's exact phrases where relevant. Be specific and avoid generic stock responses.

User text:
{text}

Mode: {mode}

Produce a structured response in Markdown with these sections:
- Brief personalized validation (quote exact phrases)
- 4 tailored coping actions (why each helps for this user)
- Immediate 12-24 hour plan (3 items)
- How to phrase asking for help to a loved one (one-sentence script)
- Warning signs to monitor and when to seek professional help

End with the exact disclaimer block (do not vary):
----------------------------------------
⚠ **Important Disclaimer**
This AI may be inaccurate. Please seek medical advice from a professional.
Talk to your loved ones for support.
**Indian Mental Health Helpline:** 1800-599-0019
----------------------------------------
"""

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
# SIDEBAR
# -------------------------
with st.sidebar:
    st.write("## Settings")
    chosen_model_name = st.selectbox("Choose AI Model", SIDEBAR_MODEL_KEYS, index=1)
    model_id = MODEL_NAMES[chosen_model_name]
    mode = st.radio("Analysis Mode", ["Crisis Detection", "Emotional Support", "Risk Assessment"])

    st.write("### 🌐 Language")
    chosen_lang_label = st.selectbox("Response Language", list(LANGUAGES.keys()), index=0)
    selected_lang = LANGUAGES[chosen_lang_label]

    st.write("### Emergency Resources")
    st.info("**KIRAN:** 1800-599-0019\n**Vandrevala:** 1860-2662-345\n**iCall:** 9152987821")

# -------------------------
# Session state init
# -------------------------
if "voice_transcript" not in st.session_state:
    st.session_state["voice_transcript"] = ""
if "last_request_time" not in st.session_state:
    st.session_state["last_request_time"] = 0.0
if "mood_prefill" not in st.session_state:
    st.session_state["mood_prefill"] = ""

# -------------------------
# MAIN UI
# -------------------------
col1, col2 = st.columns([2, 1])

with col1:
    tab1, tab2 = st.tabs(["✍️ Text", "🎤 Voice"])
    input_text = ""

    with tab1:
        st.markdown('<div class="info-card"><h3>Write your feelings</h3>', unsafe_allow_html=True)

        # ── Mood Tag Buttons ──
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
        # Clear prefill after it's been rendered into the text area
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

    # Resolve final input
    if not input_text.strip() and st.session_state.get("voice_transcript"):
        input_text = st.session_state["voice_transcript"]

    # ── Cooldown check ──
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

            # ── Auto-trigger breathing widget when stress > 70 ──
            if final_level > 70:
                show_breathing_widget()

            support_prompt = build_support_prompt(mode, input_text, lang=selected_lang)
            response = safe_generate(model_id, support_prompt)

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

        st.session_state["voice_transcript"] = ""

with col2:
    st.markdown('<div class="info-card"><h3>Why Mindful?</h3>- Modern\n- Gemini 2.5 models\n- 24/7 support</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-card"><h3>Modes</h3>- Crisis Detection\n- Emotional Support\n- Risk Assessment</div>', unsafe_allow_html=True)
    st.markdown('<div class="emergency-banner">🚨 IN CRISIS? CALL KIRAN 1800-599-0019 🚨</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer-dark">
<p><strong>Disclaimer:</strong> This tool does not replace professional help.
If you are in crisis, contact emergency services or the KIRAN helpline (1800-599-0019).</p>
</div>
""", unsafe_allow_html=True)
