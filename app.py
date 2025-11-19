import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import re

# =========================
#  Gemini API Configuration
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
#  Page Config and UI Theme
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

# ====== Helper: Gemini 2.0 Model Names ======
MODEL_NAMES = {
    "Gemini 2.0 Flash": "gemini-2.0-flash-latest",
    "Gemini 2.0 Pro": "gemini-2.0-pro-latest"
}
SIDEBAR_MODEL_KEYS = list(MODEL_NAMES.keys())

def get_stress_level(user_text, model_name):
    model = genai.GenerativeModel(model_name)
    prompt = (
        "You are an AI specialized in mental health. "
        "Analyze the user's message and reply with ONLY a single integer (0-100) representing the user's stress percentage. No words, no explanation—just the number between 0 and 100.\n"
        f"Text: {user_text}"
    )
    response = model.generate_content(prompt)
    match = re.search(r'\d+', response.text)
    if match:
        return min(100, max(0, int(match.group())))
    return 50

def get_stress_desc(level):
    if level < 25: return "😌 Minimal Stress — You seem quite calm."
    if level < 50: return "🙂 Mild Stress — Some tension, but manageable."
    if level < 75: return "😟 Moderate Stress — Pay attention to signs and consider healthy coping."
    return "😰 High Stress — Significant distress detected. Don't hesitate to seek help."

# ================
# UI Layout & App
# ================
st.markdown("""
<div class="main-header">
    <h1>🧠 Mental Health AI</h1>
    <p>Premium stress detector & crisis support tool</p>
</div>
""", unsafe_allow_html=True)

# --- Sidebar ---
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
            level = get_stress_level(input_text, model_id)
            st.markdown(f"""
            <div class="stress-meter-container">
                <div class="circular-gauge">
                    <div class="gauge-inner">
                        <div class="stress-percentage">{level}%</div>
                        <div class="stress-label">Stress</div>
                    </div>
                </div>
                <div style="color:#bb86fc;margin-top:10px;">{get_stress_desc(level)}</div>
            </div>
            """, unsafe_allow_html=True)
            # Compose AI Problem-Specific Response
            model = genai.GenerativeModel(model_id)
            if mode == "Crisis Detection":
                prompt = (
                    "You are a crisis detection AI. Analyze the following message for signs of emotional distress:\n"
                    f"{input_text}\n"
                    "1. Rate crisis level (LOW/MODERATE/HIGH/CRITICAL)\n"
                    "2. List key concerning phrases/patterns\n"
                    "3. Name the likely emotional state\n"
                    "4. Suggest 3-5 actionable next steps\n"
                    "5. List immediate helplines to contact"
                )
            elif mode == "Emotional Support":
                prompt = (
                    "You are a compassionate mental health companion. Review the following message:\n"
                    f"{input_text}\n"
                    "1. Validate and name specific emotions/feelings\n"
                    "2. Offer hope and relatable encouragement\n"
                    "3. List tangible coping skills or self-care steps"
                )
            else:  # Risk Assessment
                prompt = (
                    "You are a mental health safety specialist. Assess the following message:\n"
                    f"{input_text}\n"
                    "List:\n1. Risk factors detected\n2. Protective strengths\n3. Overall risk rating\n4. Suggestions for safe plans"
                )
            response = model.generate_content(prompt)
            st.markdown('<div class="response-area">', unsafe_allow_html=True)
            st.markdown(f"### AI Support\n{response.text}")
            st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="info-card"><h3>Why Mindful?</h3>- Modern, safe, and confidential\n- Up-to-date AI models\n- 24/7 crisis guidance\n- Attractive for school projects</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-card"><h3>Modes</h3>- Crisis Detection\n- Emotional Support\n- Risk Assessment</div>', unsafe_allow_html=True)
    st.markdown('<div class="emergency-banner">🚨 IN CRISIS? CALL KIRAN 1800-599-0019 🚨</div>', unsafe_allow_html=True)

st.markdown('---')
st.markdown("""
<div class="footer-dark">
    <p><strong>Disclaimer:</strong> This tool does not replace professional help. If you are in crisis, contact emergency services or the KIRAN helpline (1800-599-0019).</p>
    <p>Premium Mental Health Support — Powered by Gemini 2.0</p>
</div>
""", unsafe_allow_html=True)
