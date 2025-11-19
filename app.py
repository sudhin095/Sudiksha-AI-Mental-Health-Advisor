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

# ====== FIXED MODEL NAMES ======
MODEL_NAMES = {
    "Gemini 2.5 Pro": "models/gemini-2.5-pro",
    "Gemini 2.5 Flash": "models/gemini-2.5-flash"
}
SIDEBAR_MODEL_KEYS = list(MODEL_NAMES.keys())

# -------------------------
# QUOTA-SAFE GENERATOR
# -------------------------
def safe_generate(model_id, prompt):
    """Prevents crashes + switches to Flash if Pro is out of quota."""
    try:
        model = genai.GenerativeModel(model_id)
        return model.generate_content(prompt)
    except Exception as e:
        if "429" in str(e) or "quota" in str(e).lower():
            st.warning("⚠️ Model quota exceeded. Switching to Gemini-2.5-Flash.")
            try:
                fallback = "models/gemini-2.5-flash"
                model = genai.GenerativeModel(fallback)
                return model.generate_content(prompt)
            except:
                return None
        return None

# -------------------------
# Lexicon scoring
# -------------------------
LEXICON_WEIGHTS = {
    "suicid": 5, "kill myself": 5, "end my life": 5, "i want to die": 5, "worthless": 4,
    "panic": 4, "panic attack": 4, "hopeless": 4, "overwhelmed": 4, "can't cope": 4,
    "anxious": 3, "anxiety": 3, "depressed": 3, "depression": 3, "stress": 3, "stressed": 3,
    "tired": 1.5, "exhausted": 2, "can't sleep": 2, "insomnia": 2, "angry": 1.5, "sad": 2
}

def lexicon_score(text):
    t = text.lower()
    score = 0.0
    for kw, w in LEXICON_WEIGHTS.items():
        if kw in t:
            score += w
    if any(k in t for k in ["suicid", "kill myself", "i want to die", "end my life"]):
        score = max(score, 8.0)
    return int(round(min(1.0, score / 10.0) * 100))

# -------------------------
# Structured stress extraction
# -------------------------
def ask_model_for_structured_stress(user_text, model_id):
    prompt = (
        "Return ONLY a JSON object with keys: score, evidence, confidence.\n"
        f"Text: {user_text}"
    )
    response = safe_generate(model_id, prompt)
    if not response:
        return None
    try:
        match = re.search(r'\{[\s\S]*\}', response.text)
        if not match:
            return None
        data = json.loads(match.group())
        return {
            "model_score": int(data.get("score", 50)),
            "evidence": data.get("evidence", []),
            "confidence": float(data.get("confidence", 0.5)),
        }
    except:
        return None

def get_stress_level(user_text, model_id):
    structured = ask_model_for_structured_stress(user_text, model_id)
    lex_score = lexicon_score(user_text)

    if structured:
        model_score = structured["model_score"]
        conf = structured["confidence"]
        weight_model = 0.6 * conf + 0.2
        final = int(round(model_score * weight_model + lex_score * (1 - weight_model)))
        return max(0, min(100, final)), structured

    return lex_score, {"model_score": None, "evidence": [], "confidence": None}

def get_stress_desc(level):
    if level < 25: return "😌 Minimal Stress — You seem calm."
    if level < 50: return "🙂 Mild Stress — Manageable tension."
    if level < 75: return "😟 Moderate Stress — Consider coping tools."
    return "😰 High Stress — Strong distress detected."

# -------------------------
# Support message builder
# -------------------------
def build_support_prompt(mode, text):
    return f"""
You are a deeply empathetic professional mental-health assistant.
Your response must be:
• VERY specific to the user's message
• Detailed, organized in bullet points
• Supportive and actionable

User text:
{text}

Mode: {mode}

Write a long, structured response including:
1. Emotional understanding (specific to the message)
2. Realistic coping strategies
3. What they can do in the next 12–24 hours
4. How to talk to someone they trust
5. A gentle reminder that help is available
"""

# -------------------------
# UI HEADER
# -------------------------
st.markdown("""
<div class="main-header">
    <h1>🧠 Mental Health AI</h1>
    <p>Premium stress detector & crisis support tool</p>
</div>
""", unsafe_allow_html=True)

# QUOTES
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
“If you're going through hell, keep going.”<br>
“If there is something that means a lot to you, do not postpone it.”
</div>
""", unsafe_allow_html=True)

# -------------------------
# SIDEBAR
# -------------------------
with st.sidebar:
    st.write("## Settings")
    chosen_model_name = st.selectbox("Choose AI Model", SIDEBAR_MODEL_KEYS)
    model_id = MODEL_NAMES[chosen_model_name]

    mode = st.radio("Analysis Mode", ["Crisis Detection", "Emotional Support", "Risk Assessment"])

    st.write("### Emergency Resources")
    st.info("**KIRAN:** 1800-599-0019\n**Vandrevala:** 1860-2662-345\n**iCall:** 9152987821")

# -------------------------
# MAIN UI
# -------------------------
col1, col2 = st.columns([2, 1])

with col1:
    tab1, tab2 = st.tabs(["✍️ Text", "🎤 Voice"])
    input_text = ""

    with tab1:
        st.markdown('<div class="info-card"><h3>Write your feelings</h3>', unsafe_allow_html=True)
        input_text = st.text_area("Describe your feelings.", height=160)
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="info-card"><h3>Speak your mind</h3>', unsafe_allow_html=True)
        audio_data = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹ Stop")
        if audio_data:
            st.audio(audio_data["bytes"], format="audio/wav")
            st.success("Voice recorded! (Type a summary in text box for analysis.)")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🔍 Analyze & Get Support", use_container_width=True) and input_text.strip():
        with st.spinner("Analyzing..."):

            # Stress level
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

            # Support response
            prompt = build_support_prompt(mode, input_text)
            response = safe_generate(model_id, prompt)

            st.markdown('<div class="response-area">', unsafe_allow_html=True)
            if response:
                st.markdown("### AI Support\n" + response.text)
            else:
                st.error("AI could not generate a response due to quota limits.")
            st.markdown('</div>', unsafe_allow_html=True)

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
