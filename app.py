import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import os
import re

# =========================
#  Gemini API Configuration
# =========================
# Using st.secrets for Streamlit Cloud deployment
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
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
        padding
