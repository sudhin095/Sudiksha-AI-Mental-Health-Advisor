import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import os
import re
import time

# =========================
#  Gemini API Configuration
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY (or GOOGLE_API_KEY) not set! Please set it in your environment or Streamlit secrets.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)


# ================
#  Page Config & Custom CSS
# ================
st.set_page_config(
    page_title="Mental Health Crisis Support AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    * { font-family: 'Poppins', sans-serif; }
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .main-header { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 2rem; border-radius: 20px; text-align: center; margin-bottom: 2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
    .main-header h1 { color: white; font-size: 3rem; font-weight: 700; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
    .main-header p { color: #f0f0f0; font-size: 1.2rem; margin-top: 0.5rem; }
    .info-card { background: rgba(255, 255, 255, 0.95); padding: 2rem; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.2); margin-bottom: 1.5rem; backdrop-filter: blur(10px); border: 2px solid rgba(255,255,255,0.3); }
    .info-card h3 { color: #667eea; font-weight: 600; margin-bottom: 1rem; }
    .stTextArea textarea { border-radius: 15px !important; border: 2px solid #667eea !important; font-size: 1rem !important; padding: 1rem !important; }
    .stTextArea textarea:focus { border-color: #f5576c !important; box-shadow: 0 0 15px rgba(245, 87, 108, 0.3) !important; }
    .stButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.75rem 2rem; border-radius: 25px; font-weight: 600; font-size: 1.1rem; box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4); transition: all 0.3s ease; width: 100%; }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6); }
    div[data-testid="stVerticalBlock"] > div:has(iframe) { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1.5rem; border-radius: 15px; box-shadow: 0 5px 15px rgba(250, 112, 154, 0.4); }
    .response-area { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 2rem; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.2); margin-top: 1.5rem; }
    .response-area h3 { color: #667eea; font-weight: 700; margin-bottom: 1rem; }
    [data-testid="stSidebar"] { background: linear-gradient(180deg, #667eea 0%, #764ba2 100%); }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: white !important; }
    .emergency-banner { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 1.5rem; border-radius: 15px; text-align: center; font-weight: 600; margin-bottom: 1.5rem; box-shadow: 0 5px 15px rgba(245, 87, 108, 0.4); }
    .status-active { display: inline-block; width: 12px; height: 12px; background-color: #4ade80; border-radius: 50%; margin-right: 0.5rem; animation: pulse 2s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    .stTabs [data-baseweb="tab-list"] { gap: 1rem; }
    .stTabs [data-baseweb="tab"] { background-color: rgba(255, 255, 255, 0.2); border-radius: 10px; color: white; font-weight: 600; padding: 0.75rem 1.5rem; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
    .stSpinner > div { border-top-color: #f5576c !important; }
    .stSuccess, .stWarning, .stError { border-radius: 10px; }
    .stSuccess { background-color: rgba(74, 222, 128, 0.1); border-left: 5px solid #4ade80; }
    .stWarning { background-color: rgba(251, 191, 36, 0.1); border-left: 5px solid #fbbf24; }
    .stError { background-color: rgba(239, 68, 68, 0.1); border-left: 5px solid #ef4444; }
    
    /* Stress Meter Gauge Styling */
    .gauge-container { display: flex; justify-content: center; align-items: center; margin-top: 1.5rem; }
    .gauge { width: 200px; height: 100px; position: relative; overflow: hidden; }
    .gauge-arc { width: 200px; height: 100px; border-radius: 100px 100px 0 0; border: 20px solid #e6e6e6; border-bottom: 0; box-sizing: border-box; position: absolute; }
    .gauge-fill { width: 200px; height: 100px; border-radius: 100px 100px 0 0; border: 20px solid #f5576c; border-bottom: 0; box-sizing: border-box; position: absolute; clip: rect(0, 100px, 100px, 0); transform: rotate(0deg); transition: transform 1s ease-in-out; }
    .gauge-text { position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); font-size: 2rem; font-weight: 700; color: #667eea; }
</style>
""",
    unsafe_allow_html=True,
)

# ======================
#  Session State
# ======================
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []
if "stress_level" not in st.session_state:
    st.session_state.stress_level = 0

# ======================
#  Helper Functions
# ======================
def get_stress_level(text, model_name):
    """Calls Gemini to get a stress percentage."""
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""Analyze the stress level in the following text. Respond with ONLY a single integer number between 0 and 100, representing the percentage of stress. Do not add any other words, symbols, or explanations. Just the number. Text: '{text}'"""
        response = model.generate_content(prompt)
        
        # Use regex to find any number in the response to make it robust
        match = re.search(r'\d+', response.text)
        if match:
            return int(match.group(0))
        return None
    except Exception as e:
        st.warning(f"Could not calculate stress level: {e}")
        return None

# ================
#  Sidebar
# ================
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    # Model Selection
    gemini_model_name = st.selectbox(
        "Select Gemini Model:",
        ("gemini-1.5-flash-latest", "gemini-1.5-pro-latest"),
        help="Flash is faster, Pro is more powerful."
    )

    analysis_mode = st.radio(
        "Select Analysis Mode:",
        ["Crisis Detection", "Emotional Support", "Risk Assessment"],
    )

    st.markdown("---")
    st.markdown("### 🚨 Emergency Resources")
    st.markdown("**Immediate Help (India):**\n- **KIRAN Helpline:** 1800-599-0019\n- **Vandrevala Foundation:** 1860-2662-345\n- **iCall:** 9152987821")
    
    st.markdown("---")
    with st.expander("💡 How to Use"):
        st.markdown("1. **Select** a Gemini model\n2. **Type** or **Record** your message\n3. **Click Analyze** to get AI support\n4. Review the **stress meter** and guidance")

# ================
#  Main UI
# ================
st.markdown('<div class="main-header"><h1>🧠 Mental Health AI</h1><p><span class="status-active"></span>Crisis Detection & Support System</p></div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    tab1, tab2 = st.tabs(["✍️ Text Input", "🎤 Voice Input"])

    with tab1:
        st.markdown('<div class="info-card"><h3>Express Yourself</h3>', unsafe_allow_html=True)
        user_text = st.text_area("Share what's on your mind...", height=200, placeholder="Type your thoughts, feelings, or concerns here...", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="info-card"><h3>Speak Your Mind</h3>', unsafe_allow_html=True)
        st.info("🎙️ Click to start recording. For analysis, a transcription will be needed.")
        audio_data = mic_recorder(start_prompt="🎤 Start", stop_prompt="⏹️ Stop", just_once=False, use_container_width=True, key='mic')
        if audio_data:
            st.success("✅ Recording captured!")
            st.audio(audio_data['bytes'])
            st.info("💡 For now, please summarize what you said in the 'Text Input' tab for analysis.")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🔍 Analyze & Get Support", use_container_width=True):
        if user_text:
            # Placeholder for the stress meter
            gauge_placeholder = st.empty()
            
            with st.spinner("Analyzing... This may take a moment."):
                # 1. Get Stress Level
                stress_level = get_stress_level(user_text, gemini_model_name)
                st.session_state.stress_level = stress_level if stress_level is not None else 0

                # Animate the gauge
                gauge_placeholder.markdown(f"""
                <div class="gauge-container">
                    <div class="gauge">
                        <div class="gauge-arc"></div>
                        <div class="gauge-fill" style="transform: rotate({st.session_state.stress_level * 1.8}deg);"></div>
                        <div class="gauge-text">{st.session_state.stress_level}%</div>
                    </div>
                </div>
                <h3 style="text-align: center; color: white;">Stress Level</h3>
                """, unsafe_allow_html=True)
                
                # 2. Get Detailed Analysis
                try:
                    model = genai.GenerativeModel(gemini_model_name)
                    # Prompts remain the same as they are effective
                    if analysis_mode == "Crisis Detection":
                        prompt = f"You are a compassionate mental health crisis detection AI. Analyze the following message for crisis indicators.\n\nUser Message: \"\"\"{user_text}\"\"\"\n\nProvide a detailed, problem-specific response with these sections:\n\n1. **Crisis Level Assessment**: Rate as LOW/MODERATE/HIGH/CRITICAL with clear reasoning.\n2. **Key Concerns Identified**: List specific phrases or patterns that indicate distress.\n3. **Emotional State**: Describe the apparent emotional condition.\n4. **Immediate Recommendations**: 3-5 specific, actionable steps.\n5. **Support Resources**: Relevant helplines for their situation.\n6. **Follow-up Suggestions**: What to monitor."
                    elif analysis_mode == "Emotional Support":
                        prompt = f"You are a warm, supportive mental health companion. Provide emotional support for this message.\n\nUser Message: \"\"\"{user_text}\"\"\"\n\nProvide a compassionate, problem-specific response with:\n\n1. **Validation**: Acknowledge their feelings specifically.\n2. **Understanding**: Show you understand their unique situation.\n3. **Encouragement**: Provide hope related to their specific challenges.\n4. **Coping Strategies**: 4-5 techniques tailored to their situation.\n5. **Self-Care Actions**: Immediate things they can do today.\n6. **Positive Reframing**: Help them see their situation from a growth perspective."
                    else:  # Risk Assessment
                        prompt = f"You are a mental health risk assessment specialist. Evaluate potential risks in this message.\n\nUser Message: \"\"\"{user_text}\"\"\"\n\nProvide a structured, problem-specific assessment:\n\n1. **Risk Factors Present**: Identify specific concerning elements.\n2. **Protective Factors**: Highlight strengths and positive elements.\n3. **Overall Risk Level**: Low/Moderate/High/Critical.\n4. **Warning Signs to Monitor**: Specific behaviors or thoughts to watch for.\n5. **Safety Plan Components**: Tailored safety strategies.\n6. **Professional Help Indicators**: When and why to seek professional support."

                    response = model.generate_content(prompt)
                    
                    st.markdown('<div class="response-area">', unsafe_allow_html=True)
                    st.markdown(f"### 💙 {analysis_mode} Results")
                    st.markdown(response.text)
                    st.markdown("</div>", unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"⚠️ Error during detailed analysis: {e}")
        else:
            st.warning("⚠️ Please enter some text before analyzing.")

with col2:
    st.markdown('<div class="info-card"><h3>🌟 You\'re Not Alone</h3><p>- Confidential AI analysis<br>- 24/7 support available<br>- Professional crisis resources<br>- Compassionate, problem-specific guidance</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="info-card"><h3>📊 Analysis Modes</h3><p><b>Crisis Detection</b><br>Identifies urgent concerns<br><br><b>Emotional Support</b><br>Provides comfort & coping<br><br><b>Risk Assessment</b><br>Evaluates safety factors</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="emergency-banner">🚨 In Crisis? Call Now 🚨<br><strong>KIRAN: 1800-599-0019</strong></div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown('<div style="text-align: center; color: white; padding: 1rem;"><p><strong>Disclaimer:</strong> This AI tool is for support and not a replacement for professional care. If in crisis, please contact emergency services.</p><p>💜 Built with care for mental health awareness</p></div>', unsafe_allow_html=True)
