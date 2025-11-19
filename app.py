import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import os
import re

# =========================
#  Gemini API Configuration
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not GEMINI_API_KEY:
    st.error("⚠️ GEMINI_API_KEY not set! Please configure it in Streamlit secrets or environment variables.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# ================
#  Page Config
# ================
st.set_page_config(
    page_title="Mental Health AI - Dark Mode",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ================
#  Dark Theme Custom CSS
# ================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Space+Grotesk:wght@500;700&display=swap');
    
    /* Global Dark Theme */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main Dark Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
        color: #e0e0e0;
    }
    
    /* Header with Neon Glow */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 2.5rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(0, 255, 255, 0.3);
        border: 2px solid rgba(0, 255, 255, 0.2);
    }
    
    .main-header h1 {
        color: #00fff5;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 3.5rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 0 0 20px rgba(0, 255, 255, 0.8), 0 0 40px rgba(0, 255, 255, 0.4);
        letter-spacing: 2px;
    }
    
    .main-header p {
        color: #a8dadc;
        font-size: 1.3rem;
        margin-top: 0.8rem;
        font-weight: 300;
    }
    
    /* Dark Cards with Glow */
    .info-card {
        background: rgba(26, 26, 46, 0.85);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(138, 43, 226, 0.2);
        margin-bottom: 1.5rem;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(138, 43, 226, 0.3);
    }
    
    .info-card h3 {
        color: #bb86fc;
        font-weight: 600;
        margin-bottom: 1rem;
        font-size: 1.4rem;
    }
    
    /* Input Styling Dark */
    .stTextArea textarea {
        border-radius: 15px !important;
        border: 2px solid #bb86fc !important;
        background-color: #1a1a2e !important;
        color: #e0e0e0 !important;
        font-size: 1.05rem !important;
        padding: 1.2rem !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #00fff5 !important;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.5) !important;
    }
    
    /* Neon Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: 2px solid #bb86fc;
        padding: 0.9rem 2.5rem;
        border-radius: 30px;
        font-weight: 700;
        font-size: 1.15rem;
        box-shadow: 0 5px 25px rgba(138, 43, 226, 0.5);
        transition: all 0.3s ease;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.02);
        box-shadow: 0 10px 40px rgba(138, 43, 226, 0.8), 0 0 30px rgba(0, 255, 255, 0.5);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Response Area with Gradient Border */
    .response-area {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
        margin-top: 2rem;
        border: 2px solid;
        border-image: linear-gradient(135deg, #bb86fc, #00fff5) 1;
    }
    
    .response-area h3 {
        color: #00fff5;
        font-weight: 700;
        margin-bottom: 1.2rem;
        font-size: 1.8rem;
    }
    
    /* Dark Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #302b63 100%);
        border-right: 2px solid rgba(138, 43, 226, 0.3);
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {
        color: #e0e0e0 !important;
    }
    
    /* Emergency Banner Dark */
    .emergency-banner {
        background: linear-gradient(135deg, #d32f2f 0%, #c2185b 100%);
        color: white;
        padding: 1.8rem;
        border-radius: 20px;
        text-align: center;
        font-weight: 700;
        margin-bottom: 1.5rem;
        box-shadow: 0 5px 25px rgba(211, 47, 47, 0.6);
        border: 2px solid rgba(255, 82, 82, 0.5);
        font-size: 1.1rem;
    }
    
    /* Animated Status Indicator */
    .status-active {
        display: inline-block;
        width: 14px;
        height: 14px;
        background-color: #00ff88;
        border-radius: 50%;
        margin-right: 0.7rem;
        animation: pulse-glow 2s infinite;
        box-shadow: 0 0 10px #00ff88;
    }
    
    @keyframes pulse-glow {
        0%, 100% { 
            opacity: 1;
            box-shadow: 0 0 10px #00ff88;
        }
        50% { 
            opacity: 0.6;
            box-shadow: 0 0 20px #00ff88;
        }
    }
    
    /* Dark Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.2rem;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(26, 26, 46, 0.6);
        border-radius: 12px;
        color: #a8dadc;
        font-weight: 600;
        padding: 0.9rem 1.8rem;
        border: 1px solid rgba(138, 43, 226, 0.3);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #bb86fc;
        box-shadow: 0 5px 20px rgba(138, 43, 226, 0.5);
    }
    
    /* Loading Animation */
    .stSpinner > div {
        border-top-color: #00fff5 !important;
    }
    
    /* Dark Success/Warning/Error Messages */
    .stSuccess {
        background-color: rgba(0, 255, 136, 0.15);
        border-left: 5px solid #00ff88;
        border-radius: 12px;
        color: #00ff88;
    }
    
    .stWarning {
        background-color: rgba(255, 193, 7, 0.15);
        border-left: 5px solid #ffc107;
        border-radius: 12px;
        color: #ffc107;
    }
    
    .stError {
        background-color: rgba(244, 67, 54, 0.15);
        border-left: 5px solid #f44336;
        border-radius: 12px;
        color: #ff6b6b;
    }
    
    .stInfo {
        background-color: rgba(0, 255, 245, 0.15);
        border-left: 5px solid #00fff5;
        border-radius: 12px;
        color: #00fff5;
    }
    
    /* Radio Buttons Dark */
    .stRadio > label {
        color: #e0e0e0 !important;
        font-weight: 600;
    }
    
    /* Select Box Dark */
    .stSelectbox > label {
        color: #e0e0e0 !important;
        font-weight: 600;
    }
    
    /* ============================= */
    /* STRESS METER - Circular Gauge */
    /* ============================= */
    .stress-meter-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin: 2rem 0;
        padding: 2rem;
        background: rgba(26, 26, 46, 0.8);
        border-radius: 20px;
        border: 2px solid rgba(138, 43, 226, 0.4);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
    }
    
    .stress-meter-title {
        color: #bb86fc;
        font-size: 1.8rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .circular-gauge {
        position: relative;
        width: 250px;
        height: 250px;
        border-radius: 50%;
        background: conic-gradient(
            from 0deg,
            #00ff88 0%,
            #ffc107 33%,
            #ff6b6b 66%,
            #d32f2f 100%
        );
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 40px rgba(138, 43, 226, 0.6);
    }
    
    .gauge-inner {
        width: 200px;
        height: 200px;
        border-radius: 50%;
        background: #1a1a2e;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.5);
    }
    
    .stress-percentage {
        font-size: 4rem;
        font-weight: 700;
        color: #00fff5;
        text-shadow: 0 0 20px rgba(0, 255, 255, 0.8);
        line-height: 1;
    }
    
    .stress-label {
        font-size: 1.2rem;
        color: #a8dadc;
        margin-top: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 2px;
    }
    
    .stress-description {
        text-align: center;
        color: #e0e0e0;
        font-size: 1.1rem;
        margin-top: 1.5rem;
        padding: 1rem;
        background: rgba(138, 43, 226, 0.1);
        border-radius: 10px;
        max-width: 400px;
    }
    
    /* Footer Dark */
    .footer-dark {
        text-align: center;
        color: #a8dadc;
        padding: 2rem;
        background: rgba(15, 12, 41, 0.6);
        border-radius: 15px;
        margin-top: 3rem;
        border: 1px solid rgba(138, 43, 226, 0.2);
    }
</style>
""", unsafe_allow_html=True)

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
    """Extract stress percentage from text using Gemini."""
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""You are a mental health AI analyzing stress levels. Based on the following text, provide ONLY a single integer number between 0 and 100 representing the stress percentage. 

0 = No stress/calm
25 = Mild stress
50 = Moderate stress
75 = High stress
100 = Extreme stress/crisis

Respond with ONLY the number, nothing else.

Text to analyze: '{text}'"""
        
        response = model.generate_content(prompt)
        match = re.search(r'\d+', response.text)
        if match:
            stress_val = int(match.group(0))
            return min(100, max(0, stress_val))  # Clamp between 0-100
        return 50  # Default to moderate if parsing fails
    except Exception as e:
        st.warning(f"Stress calculation warning: {e}")
        return 50

def get_stress_description(level):
    """Return description based on stress level."""
    if level < 25:
        return "😌 Minimal Stress - You seem relatively calm and balanced."
    elif level < 50:
        return "😐 Mild Stress - Some tension present but manageable."
    elif level < 75:
        return "😟 Moderate Stress - Noticeable stress that needs attention."
    else:
        return "😰 High Stress - Significant distress detected. Please seek support."

# ================
#  Header
# ================
st.markdown("""
<div class="main-header">
    <h1>🧠 MENTAL HEALTH AI</h1>
    <p><span class="status-active"></span>Advanced Crisis Detection & Support System</p>
</div>
""", unsafe_allow_html=True)

# ================
#  Sidebar
# ================
with st.sidebar:
    st.markdown("## ⚙️ SETTINGS")
    
    # Model Selection
    gemini_model = st.selectbox(
        "🤖 Select Gemini Model:",
        ("gemini-1.5-flash-latest", "gemini-1.5-pro-latest"),
        help="Flash: Faster response | Pro: More powerful analysis"
    )
    
    st.markdown("---")
    
    # Analysis Mode
    analysis_mode = st.radio(
        "📊 Analysis Mode:",
        ["Crisis Detection", "Emotional Support", "Risk Assessment"],
        help="Choose the type of analysis you need"
    )
    
    st.markdown("---")
    
    # Emergency Contacts
    st.markdown("### 🚨 EMERGENCY RESOURCES")
    st.markdown("""
**24/7 Helplines (India):**
- 🆘 **KIRAN:** 1800-599-0019
- 💬 **Vandrevala:** 1860-2662-345
- 📞 **iCall:** 9152987821
    """)
    
    st.markdown("---")
    
    # How to Use
    with st.expander("💡 HOW TO USE"):
        st.markdown("""
1. Select your preferred Gemini model
2. Choose an analysis mode
3. Type or record your message
4. Click 'Analyze' to get insights
5. Review stress meter & guidance
        """)
    
    # Analysis History
    if st.session_state.analysis_history:
        st.markdown("---")
        st.markdown("### 📈 SESSION STATS")
        st.info(f"Analyses: {len(st.session_state.analysis_history)}")

# ================
#  Main Content
# ================
col1, col2 = st.columns([2, 1])

with col1:
    # Input Tabs
    tab1, tab2 = st.tabs(["✍️ TEXT INPUT", "🎤 VOICE INPUT"])
    
    with tab1:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### Express Your Thoughts")
        user_text = st.text_area(
            "Share what's on your mind...",
            height=220,
            placeholder="Type your thoughts, feelings, or concerns here. All conversations are confidential.",
            label_visibility="collapsed",
            key="text_input"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### Record Your Voice")
        st.info("🎙️ Click below to record. Speak clearly and take your time.")
        
        audio_data = mic_recorder(
            start_prompt="🎤 START RECORDING",
            stop_prompt="⏹️ STOP RECORDING",
            just_once=False,
            use_container_width=True,
            key='mic_recorder'
        )
        
        if audio_data is not None:
            st.success("✅ Recording captured successfully!")
            st.audio(audio_data['bytes'], format='audio/wav')
            st.info("💡 **Next Step:** Transcribe this audio or type a summary in the Text Input tab for AI analysis. You can integrate speech-to-text APIs for automatic transcription.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Analyze Button
    if st.button("🔍 ANALYZE & GET SUPPORT", use_container_width=True):
        if user_text.strip():
            # Placeholders
            stress_placeholder = st.empty()
            analysis_placeholder = st.empty()
            
            with st.spinner("🤔 Analyzing your message with AI-powered empathy..."):
                # Step 1: Calculate Stress Level
                stress_level = get_stress_level(user_text, gemini_model)
                st.session_state.stress_level = stress_level
                
                # Display Stress Meter
                stress_desc = get_stress_description(stress_level)
                stress_placeholder.markdown(f"""
                <div class="stress-meter-container">
                    <div class="stress-meter-title">STRESS ANALYSIS</div>
                    <div class="circular-gauge">
                        <div class="gauge-inner">
                            <div class="stress-percentage">{stress_level}%</div>
                            <div class="stress-label">STRESS</div>
                        </div>
                    </div>
                    <div class="stress-description">{stress_desc}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Step 2: Detailed Analysis
                try:
                    model = genai.GenerativeModel(gemini_model)
                    
                    # Build mode-specific prompts
                    if analysis_mode == "Crisis Detection":
                        prompt = f"""You are a compassionate mental health crisis detection AI. Analyze the following message for crisis indicators and provide problem-specific guidance.

**User Message:**
"{user_text}"

**Provide a detailed response with these sections:**

1. **Crisis Level Assessment**: Rate as LOW/MODERATE/HIGH/CRITICAL with clear reasoning
2. **Key Concerns Identified**: Specific phrases or patterns indicating distress
3. **Emotional State Analysis**: Describe the apparent emotional condition
4. **Immediate Action Steps**: 3-5 specific, actionable recommendations
5. **Support Resources**: Relevant helplines and resources for this specific situation
6. **Follow-Up Guidance**: What to monitor and when to seek additional help

Be empathetic, specific, and solution-focused. Address their exact concerns using their own words."""

                    elif analysis_mode == "Emotional Support":
                        prompt = f"""You are a warm, supportive mental health companion providing emotional support.

**User Message:**
"{user_text}"

**Provide a compassionate response with:**

1. **Validation**: Acknowledge their specific feelings and experiences
2. **Understanding**: Show you understand their unique situation
3. **Encouragement**: Provide hope tailored to their challenges
4. **Coping Strategies**: 4-5 practical techniques for their situation
5. **Self-Care Actions**: Immediate, doable steps they can take today
6. **Growth Perspective**: Help reframe challenges as opportunities

Be gentle, non-judgmental, and address what they specifically shared."""

                    else:  # Risk Assessment
                        prompt = f"""You are a mental health risk assessment specialist. Evaluate potential risks and provide structured guidance.

**User Message:**
"{user_text}"

**Provide a comprehensive assessment:**

1. **Risk Factors Present**: Specific concerning elements identified
2. **Protective Factors**: Strengths and positive elements mentioned
3. **Overall Risk Level**: Low / Moderate / High / Critical
4. **Warning Signs**: Specific behaviors or thoughts to monitor
5. **Safety Plan Components**: Tailored strategies for this person
6. **Professional Help Indicators**: When and why to seek professional support
7. **Support Network Actions**: How friends/family can help

Be thorough, specific, and provide clear, actionable guidance."""
                    
                    response = model.generate_content(prompt)
                    
                    # Store in history
                    st.session_state.analysis_history.append({
                        'mode': analysis_mode,
                        'input_preview': user_text[:80] + "..." if len(user_text) > 80 else user_text,
                        'stress_level': stress_level
                    })
                    
                    # Display Analysis
                    analysis_placeholder.markdown(f'<div class="response-area">', unsafe_allow_html=True)
                    st.markdown(f"### 💙 {analysis_mode} Results")
                    st.markdown(response.text)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Action Buttons
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("🔄 NEW ANALYSIS"):
                            st.rerun()
                    with col_b:
                        if st.button("💾 SAVE TO HISTORY"):
                            st.success("✅ Analysis saved!")
                    with col_c:
                        if st.button("📞 EMERGENCY HELP"):
                            st.info("👈 Check sidebar for emergency resources")
                    
                except Exception as e:
                    st.error(f"⚠️ API Error: {str(e)}")
                    st.info("""
**Troubleshooting:**
- Verify GEMINI_API_KEY is correctly set
- Check your API quota and permissions
- Ensure the model name is valid
- Try switching between Flash and Pro models
                    """)
        else:
            st.warning("⚠️ Please enter some text or record a message before analyzing.")

with col2:
    # Info Cards
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("### 🌟 YOU'RE NOT ALONE")
    st.markdown("""
- 🔒 **100% Confidential** AI analysis
- 🌙 **24/7 Available** support
- 👥 **Professional** crisis resources
- 💜 **Compassionate** guidance
- 🎯 **Problem-specific** insights
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("### 📊 ANALYSIS MODES")
    st.markdown("""
**🚨 Crisis Detection**
Identifies urgent concerns and provides immediate guidance.

**💚 Emotional Support**
Offers comfort, validation, and coping strategies.

**⚠️ Risk Assessment**
Evaluates safety factors and recommends next steps.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Emergency Banner
    st.markdown("""
    <div class="emergency-banner">
        🚨 IN CRISIS? CALL NOW 🚨<br>
        <strong>KIRAN HELPLINE</strong><br>
        1800-599-0019
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer-dark">
    <p><strong>⚠️ DISCLAIMER:</strong> This AI tool provides supportive guidance but is NOT a replacement for professional mental health care. If you're experiencing a mental health crisis, please contact emergency services or a crisis helpline immediately.</p>
    <p style="margin-top: 1rem; font-size: 0.95rem;">💜 Built with care for mental health awareness | Powered by Google Gemini AI</p>
</div>
""", unsafe_allow_html=True)
