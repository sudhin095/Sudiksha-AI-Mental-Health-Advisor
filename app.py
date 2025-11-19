import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import re
import json

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
</style>
""", unsafe_allow_html=True)

# ====== FIXED MODEL NAMES (working models) ======
MODEL_NAMES = {
    "Gemini 2.5 Pro": "models/gemini-2.5-pro",
    "Gemini 2.5 Flash": "models/gemini-2.5-flash"
}
SIDEBAR_MODEL_KEYS = list(MODEL_NAMES.keys())

# -------------------------
# Lexicon based scoring helpers
# -------------------------
# Weighted keywords: higher weight -> stronger contribution to stress
LEXICON_WEIGHTS = {
    # severe
    "suicid": 5, "kill myself": 5, "end my life": 5, "i want to die": 5, "worthless": 4,
    # high
    "panic": 4, "panic attack": 4, "hopeless": 4, "overwhelmed": 4, "can't cope": 4,
    # moderate
    "anxious": 3, "anxiety": 3, "depressed": 3, "depression": 3, "stress": 3, "stressed": 3,
    # low
    "tired": 1.5, "exhausted": 2, "can't sleep": 2, "insomnia": 2, "angry": 1.5, "sad": 2
}

def lexicon_score(text):
    """
    Simple rule-based score from 0-100 based on presence and weight of keywords.
    Normalizes by a heuristic maximum.
    """
    t = text.lower()
    score = 0.0
    for kw, w in LEXICON_WEIGHTS.items():
        if kw in t:
            score += w
    # If suicidal keywords present, cap high
    if any(k in t for k in ["suicid", "kill myself", "i want to die", "end my life"]):
        # ensure high immediate lexicon signal
        score = max(score, 8.0)
    # heuristic normalization: assume 10 weight corresponds to 100%
    normalized = min(1.0, score / 10.0)
    return int(round(normalized * 100))

# -------------------------
# Model-assisted structured stress extraction
# -------------------------
def ask_model_for_structured_stress(user_text, model_id):
    """
    Requests the model to output a strict JSON object with:
    { "score": int (0-100), "evidence": [short verbatim phrases], "confidence": float 0-1 }
    If the model doesn't follow format, returns None.
    """
    model = genai.GenerativeModel(model_id)
    # explicit instruction to produce JSON only (no extra commentary)
    prompt = (
        "You are a precise assistant that analyzes emotional language. "
        "Return ONLY a single valid JSON object (no explanation) with keys:\n"
        "score: integer 0-100 estimating stress level\n"
        "evidence: array of 1-6 short verbatim excerpts (<=6 words) from the user's text that support the score\n"
        "confidence: number 0.0-1.0 expressing how confident you are (0.0 low, 1.0 high)\n\n"
        "User text:\n"
        f"{user_text}\n\n"
        "Example output (ONLY JSON):\n"
        '{"score": 72, "evidence": ["I can’t sleep","I feel hopeless"], "confidence": 0.84}\n'
    )
    try:
        response = model.generate_content(prompt)
        txt = response.text.strip()
        # try to find the first JSON object in the response
        match = re.search(r'\{[\s\S]*\}', txt)
        if not match:
            return None
        json_text = match.group()
        data = json.loads(json_text)
        # basic validation
        if "score" in data and isinstance(data["score"], int):
            return {
                "model_score": max(0, min(100, int(data["score"]))),
                "evidence": data.get("evidence", []),
                "confidence": float(data.get("confidence", 0.0))
            }
    except Exception:
        return None
    return None

def get_stress_level(user_text, model_name):
    """
    Combined approach:
      - Ask model for structured JSON score (if possible)
      - Compute lexicon score
      - Combine: final = round(model*weight_model + lex*weight_lex)
    We keep weights conservative (model 0.6, lex 0.4) but if model confidence is low, lean more on lex.
    """
    # ask model for structured output
    structured = ask_model_for_structured_stress(user_text, model_name)
    lex_score = lexicon_score(user_text)

    if structured:
        model_score = structured["model_score"]
        confidence = structured.get("confidence", 0.5)
        # adapt weight by confidence
        weight_model = 0.6 * confidence + 0.2  # ensures at least 0.2
        weight_lex = 1.0 - weight_model
        final = int(round(model_score * weight_model + lex_score * weight_lex))
        # clamp
        final = max(0, min(100, final))
        return final, {"model_score": model_score, "model_confidence": confidence, "lex_score": lex_score, "evidence": structured.get("evidence", [])}
    else:
        # fallback: ask model for a plain integer if structured failed
        try:
            model = genai.GenerativeModel(model_name)
            prompt = (
                "Analyze the following text and reply with ONLY a single integer (0-100) that represents the user's stress percentage. "
                "No words, only the number.\n\n"
                f"Text: {user_text}"
            )
            response = model.generate_content(prompt)
            match = re.search(r'\d+', response.text)
            model_score = int(match.group()) if match else 50
        except Exception:
            model_score = 50
        # combine with lexicon, give more weight to lexicon if model returned default 50
        if model_score == 50:
            weight_model = 0.35
        else:
            weight_model = 0.6
        final = int(round(model_score * weight_model + lex_score * (1-weight_model)))
        final = max(0, min(100, final))
        return final, {"model_score": model_score, "model_confidence": None, "lex_score": lex_score, "evidence": []}


def get_stress_desc(level):
    if level < 25: return "😌 Minimal Stress — You seem quite calm."
    if level < 50: return "🙂 Mild Stress — Some tension, but manageable."
    if level < 75: return "😟 Moderate Stress — Pay attention and consider coping strategies."
    return "😰 High Stress — Significant distress detected. Consider reaching out for help."

# -------------------------
# Improved support prompts (must be problem-specific)
# -------------------------
def build_support_prompt(mode, input_text):
    """
    Return a detailed prompt asking the model to be specific, reference exact phrases,
    and output a structured markdown answer.
    """
    base = (
        "You are a highly empathetic, specific mental health assistant. "
        "Read the user's message and respond with a problem-specific, non-generic answer. "
        "Do NOT use stock phrases like 'you're not alone' without tying them to the user's words. "
        "Explicitly quote short verbatim phrases from the text to justify your interpretation.\n\n"
        "Structure your response in clear sections using markdown and bullet points. Use the user's exact words in quotes where relevant.\n\n"
        "Make the response actionable and tailored: give 3–5 immediate steps the user can try, each tied to what they mentioned.\n\n"
        "Also include a short 'what to monitor' list and when to seek professional help.\n\n"
        "User message:\n"
        f"{input_text}\n\n"
    )
    if mode == "Crisis Detection":
        base += (
            "Now provide these sections:\n"
            "1) Crisis level (LOW/MODERATE/HIGH/CRITICAL) with explicit justification citing user's phrases.\n"
            "2) Key concerning phrases (3–6) quoted exactly.\n"
            "3) Immediate specific actions (3 items) tied to the user's situation.\n"
            "4) Precise helpline and safety steps (if relevant).\n"
        )
    elif mode == "Emotional Support":
        base += (
            "Now provide these sections:\n"
            "1) Validation and naming of the emotions you detect, quoting user phrases.\n"
            "2) 3 personalized coping strategies connected to the user's details.\n"
            "3) A short, specific rehearsal script the user can use to tell a trusted person how they feel (one sentence).\n"
        )
    else:  # Risk Assessment
        base += (
            "Now provide these sections:\n"
            "1) Risk factors detected (explicitly tie to text).\n"
            "2) Protective factors or strengths observed.\n"
            "3) Clear, specific safety plan items (3–5) relevant to the user's context.\n"
        )
    base += ("\nReturn the answer in Markdown. Keep it concise but specific; avoid generic lists that could apply to anyone.")
    return base

# -------------------------
# App UI (unchanged)
# -------------------------
st.markdown("""
<div class="main-header">
    <h1>🧠 Mental Health AI</h1>
    <p>Premium stress detector & crisis support tool</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.write("## Settings")
    chosen_model_name = st.selectbox(
        "Choose AI Model",
        SIDEBAR_MODEL_KEYS,
        index=0)
    model_id = MODEL_NAMES[chosen_model_name]
    st.write("### Analysis Mode")
    mode = st.radio(
        "",
        ["Crisis Detection","Emotional Support","Risk Assessment"]
    )
    st.write("### Emergency Resources")
    st.info(
        "**KIRAN Helpline:** 1800-599-0019\n"
        "**Vandrevala:** 1860-2662-345\n"
        "**iCall:** 9152987821"
    )

col1, col2 = st.columns([2, 1])

with col1:
    tab1, tab2 = st.tabs(["✍️ Text", "🎤 Voice"])
    input_text = ""

    with tab1:
        st.markdown('<div class="info-card"><h3>Write your feelings</h3>', unsafe_allow_html=True)
        input_text = st.text_area(
            "Describe your feelings, challenges, or thoughts.", height=160, key="txt_input")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="info-card"><h3>Speak your mind</h3>', unsafe_allow_html=True)
        st.info("Click start/stop to record and playback your message.")
        audio_data = mic_recorder(
            start_prompt="🎤 Start Recording",
            stop_prompt="⏹️ Stop",
            just_once=False,
            use_container_width=True,
            key="mic"
        )
        if audio_data is not None:
            st.audio(audio_data["bytes"], format="audio/wav")
            st.success("✅ Recording saved! (Please type a summary in 'Text' if you want AI analysis of your voice)")
        st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🔍 Analyze & Get Support", use_container_width=True) and input_text.strip():
        with st.spinner("Analyzing message for stress..."):
            # new combined stress calculation
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

            # Build specific support prompt (more targeted)
            model = genai.GenerativeModel(model_id)
            support_prompt = build_support_prompt(mode, input_text)
            response = model.generate_content(support_prompt)

            # Show the AI support output (now more specific)
            st.markdown('<div class="response-area">', unsafe_allow_html=True)
            st.markdown(f"### AI Support\n{response.text}")
            st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="info-card"><h3>Why Mindful?</h3>- Modern, safe, and confidential\n- Gemini 2.5 AI models\n- 24/7 crisis guidance\n- Attractive for school projects</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-card"><h3>Modes</h3>- Crisis Detection\n- Emotional Support\n- Risk Assessment</div>', unsafe_allow_html=True)
    st.markdown('<div class="emergency-banner">🚨 IN CRISIS? CALL KIRAN 1800-599-0019 🚨</div>', unsafe_allow_html=True)

st.markdown('---')
st.markdown("""
<div class="footer-dark">
    <p><strong>Disclaimer:</strong> This tool does not replace professional help. If you are in crisis, contact emergency services or the KIRAN helpline (1800-599-0019).</p>
    <p>Premium Mental Health Support — Powered by Gemini 2.5</p>
</div>
""", unsafe_allow_html=True)
