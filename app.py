import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import os

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Set your API key in Streamlit secrets
genai.configure(api_key=GOOGLE_API_KEY)

# Page Configuration
st.set_page_config(
    page_title="Mental Health Crisis Support",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for attractive UI
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Poppins', sans-serif;
    }
    
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 2rem;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    
    .main-header h1 {
        color: white;
        font-size: 3rem;
        font-weight: 700;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .main-header p {
        color: #f0f0f0;
        font-size: 1.2rem;
        margin-top: 0.5rem;
    }
    
    /* Card Styling */
    .info-card {
        background: rgba(255, 255, 255, 0.95);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        margin-bottom: 1.5rem;
        backdrop-filter: blur(10px);
        border: 2px solid rgba(255,255,255,0.3);
    }
    
    .info-card h3 {
        color: #667eea;
        font-weight: 600;
        margin-bottom: 1rem;
    }
    
    /* Input Area */
    .stTextArea textarea {
        border-radius: 15px !important;
        border: 2px solid #667eea !important;
        font-size: 1rem !important;
        padding: 1rem !important;
    }
    
    .stTextArea textarea:focus {
        border-color: #f5576c !important;
        box-shadow: 0 0 15px rgba(245, 87, 108, 0.3) !important;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 25px;
        font-weight: 600;
        font-size: 1.1rem;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Microphone Button Styling */
    div[data-testid="stVerticalBlock"] > div:has(iframe) {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(250, 112, 154, 0.4);
    }
    
    /* Response Area */
    .response-area {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        margin-top: 1.5rem;
    }
    
    .response-area h3 {
        color: #667eea;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p {
        color: white !important;
    }
    
    /* Emergency Banner */
    .emergency-banner {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        font-weight: 600;
        margin-bottom: 1.5rem;
        box-shadow: 0 5px 15px rgba(245, 87, 108, 0.4);
    }
    
    /* Status Indicator */
    .status-active {
        display: inline-block;
        width: 12px;
        height: 12px;
        background-color: #4ade80;
        border-radius: 50%;
        margin-right: 0.5rem;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        color: white;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    
    /* Loading Animation */
    .stSpinner > div {
        border-top-color: #f5576c !important;
    }
    
    /* Success/Warning Messages */
    .stSuccess {
        background-color: rgba(74, 222, 128, 0.1);
        border-left: 5px solid #4ade80;
        border-radius: 10px;
    }
    
    .stWarning {
        background-color: rgba(251, 191, 36, 0.1);
        border-left: 5px solid #fbbf24;
        border-radius: 10px;
    }
    
    .stError {
        background-color: rgba(239, 68, 68, 0.1);
        border-left: 5px solid #ef4444;
        border-radius: 10px;
    }
    
    /* Radio Buttons */
    .stRadio > label {
        color: white !important;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []

# Header
st.markdown("""
<div class="main-header">
    <h1>🧠 Mental Health Crisis Support AI</h1>
    <p><span class="status-active"></span>AI-Powered Crisis Detection & Support System</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    # Mode Selection
    analysis_mode = st.radio(
        "Select Analysis Mode:",
        ["Crisis Detection", "Emotional Support", "Risk Assessment"],
        help="Choose the type of analysis you need"
    )
    
    st.markdown("---")
    
    # Emergency Contacts
    st.markdown("### 🚨 Emergency Resources")
    st.markdown("""
    **Immediate Help:**
    - **KIRAN Helpline:** 1800-599-0019
    - **Vandrevala Foundation:** 1860-2662-345
    - **iCall:** 9152987821
    
    **Available 24/7**
    """)
    
    st.markdown("---")
    
    # Quick Tips
    with st.expander("💡 How to Use"):
        st.markdown("""
        1. **Type** your message in the text area
        2. **OR Record** using the microphone
        3. Click **Analyze** to get AI support
        4. Review personalized guidance
        """)
    
    # History
    if st.session_state.analysis_history:
        st.markdown("---")
        st.markdown("### 📊 Analysis History")
        st.info(f"Total Analyses: {len(st.session_state.analysis_history)}")

# Main Content Area
col1, col2 = st.columns([2, 1])

with col1:
    # Input Tabs
    tab1, tab2 = st.tabs(["✍️ Text Input", "🎤 Voice Input"])
    
    with tab1:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### Express Yourself")
        user_text = st.text_area(
            "Share what's on your mind...",
            height=200,
            placeholder="Type your thoughts, feelings, or concerns here. Everything is confidential.",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="info-card">', unsafe_allow_html=True)
        st.markdown("### Speak Your Mind")
        st.info("🎙️ Click the button below to start recording. Speak clearly and take your time.")
        
        # Microphone Recorder
        audio_data = mic_recorder(
            start_prompt="🎤 Start Recording",
            stop_prompt="⏹️ Stop Recording",
            just_once=False,
            use_container_width=True,
            key='mic_recorder'
        )
        
        # Handle audio data
        if audio_data is not None:
            st.success("✅ Recording captured! Processing...")
            st.audio(audio_data['bytes'], format='audio/wav')
            
            # Here you would implement speech-to-text
            # For now, we'll prompt the user
            st.info("💡 Tip: Use the text input tab to type what you recorded for analysis.")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Analyze Button
    if st.button("🔍 Analyze & Get Support", use_container_width=True):
        if user_text:
            with st.spinner("🤔 Analyzing your message with empathy and care..."):
                try:
                    # Configure the model
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    
                    # Create problem-specific prompt based on mode
                    if analysis_mode == "Crisis Detection":
                        prompt = f"""You are a compassionate mental health crisis detection AI. Analyze the following message for crisis indicators.

User Message: {user_text}

Provide a detailed, problem-specific response with these sections:

1. **Crisis Level Assessment**: Rate as LOW/MODERATE/HIGH/CRITICAL with clear reasoning
2. **Key Concerns Identified**: List specific phrases or patterns that indicate distress
3. **Emotional State**: Describe the apparent emotional condition
4. **Immediate Recommendations**: 3-5 specific, actionable steps
5. **Support Resources**: Relevant helplines and resources for their specific situation
6. **Follow-up Suggestions**: What to monitor and when to seek additional help

Be empathetic, specific, and solution-focused. Address their exact concerns."""

                    elif analysis_mode == "Emotional Support":
                        prompt = f"""You are a warm, supportive mental health companion. Provide emotional support for this message.

User Message: {user_text}

Provide a compassionate, problem-specific response with:

1. **Validation**: Acknowledge their feelings specifically
2. **Understanding**: Show you understand their unique situation
3. **Encouragement**: Provide hope related to their specific challenges
4. **Coping Strategies**: 4-5 techniques tailored to their situation
5. **Self-Care Actions**: Immediate things they can do today
6. **Positive Reframing**: Help them see their situation from a growth perspective

Be warm, personal, and directly address what they shared."""

                    else:  # Risk Assessment
                        prompt = f"""You are a mental health risk assessment specialist. Evaluate potential risks in this message.

User Message: {user_text}

Provide a structured, problem-specific assessment:

1. **Risk Factors Present**: Identify specific concerning elements
2. **Protective Factors**: Highlight strengths and positive elements
3. **Risk Level**: Overall assessment (Low/Moderate/High/Critical)
4. **Warning Signs to Monitor**: Specific behaviors or thoughts to watch for
5. **Safety Plan Components**: Tailored safety strategies
6. **Professional Help Indicators**: When and why to seek professional support
7. **Supportive Actions**: What friends/family can do to help

Be thorough, specific, and provide clear actionable guidance."""

                    # Generate response
                    response = model.generate_content(prompt)
                    
                    # Store in history
                    st.session_state.analysis_history.append({
                        'mode': analysis_mode,
                        'input': user_text[:100] + "...",
                        'timestamp': st.session_state.get('timestamp', 'Now')
                    })
                    
                    # Display response
                    st.markdown('<div class="response-area">', unsafe_allow_html=True)
                    st.markdown(f"### 💙 {analysis_mode} Results")
                    st.markdown(response.text)
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Additional support buttons
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button("🔄 Analyze Again"):
                            st.rerun()
                    with col_b:
                        if st.button("💾 Save Analysis"):
                            st.success("Analysis saved to history!")
                    with col_c:
                        if st.button("📞 Find Help"):
                            st.info("Check Emergency Resources in sidebar →")
                    
                except Exception as e:
                    st.error(f"⚠️ Error: {str(e)}")
                    st.info("Please check your API key configuration.")
        else:
            st.warning("⚠️ Please enter some text or record a message before analyzing.")

with col2:
    # Quick Info Cards
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("### 🌟 You're Not Alone")
    st.markdown("""
    - **Confidential** AI analysis
    - **24/7** support available
    - **Professional** crisis resources
    - **Compassionate** guidance
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    st.markdown("### 📊 Analysis Modes")
    st.markdown("""
    **Crisis Detection**
    Identifies urgent concerns
    
    **Emotional Support**
    Provides comfort & coping
    
    **Risk Assessment**
    Evaluates safety factors
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Emergency Banner
    st.markdown("""
    <div class="emergency-banner">
        🚨 In Crisis? Call Now 🚨<br>
        <strong>KIRAN: 1800-599-0019</strong>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: white; padding: 1rem;">
    <p><strong>Disclaimer:</strong> This AI tool provides supportive guidance but is NOT a replacement for professional mental health care. 
    If you're in crisis, please contact emergency services or a crisis helpline immediately.</p>
    <p>💜 Built with care for mental health awareness</p>
</div>
""", unsafe_allow_html=True)

