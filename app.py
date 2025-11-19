# app.py
# Premium Mental Health Stress Detector (Streamlit)
# - Text + audio (Whisper optional) input
# - Stress percentage (0-100)
# - Problem-specific, organized bullet responses
# - Highlighted disclaimer + helpline 1800-599-0019 at bottom

import streamlit as st
from transformers import pipeline
import re
import textwrap
from io import BytesIO

# Optional Whisper (local) for audio transcription
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# --- Page Config ---
st.set_page_config(page_title="Mindful AI — Dark Mode", page_icon="🧠", layout="centered")

# --- Aesthetic Dark Theme CSS ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Space+Grotesk:wght@500;700&display=swap');
    
    /* --- ROOT VARIABLES --- */
    :root {
        --dark-bg1: #0f0c29;
        --dark-bg2: #302b63;
        --dark-bg3: #24243e;
        --glow-cyan: #00fff5;
        --glow-purple: #bb86fc;
        --text-color: #e0e0e0;
        --text-muted: #a8dadc;
    }
    
    /* --- GLOBAL STYLES --- */
    body {
        background: linear-gradient(135deg, var(--dark-bg1) 0%, var(--dark-bg2) 50%, var(--dark-bg3) 100%);
        color: var(--text-color);
        font-family: 'Inter', sans-serif;
    }
    
    /* --- MAIN CARD LAYOUT --- */
    .card {
        background: rgba(26, 26, 46, 0.85);
        padding: 32px;
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5), 0 0 30px rgba(187, 134, 252, 0.2);
        backdrop-filter: blur(15px);
        border: 1px solid rgba(187, 134, 252, 0.3);
        max-width: 900px;
        margin: 20px auto;
    }
    
    /* --- TYPOGRAPHY --- */
    .title {
        color: var(--glow-cyan);
        font-family: 'Space Grotesk', sans-serif;
        font-size: 38px;
        font-weight: 700;
        text-shadow: 0 0 15px rgba(0, 255, 245, 0.6), 0 0 30px rgba(0, 255, 245, 0.3);
        letter-spacing: 1.5px;
        text-align: center;
        margin-bottom: 8px;
    }
    
    .subtitle {
        color: var(--text-muted);
        text-align: center;
        font-weight: 300;
        margin-bottom: 24px;
        font-size: 16px;
    }
    
    /* --- INTERACTIVE ELEMENTS --- */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: 2px solid var(--glow-purple);
        padding: 12px 28px;
        border-radius: 30px;
        font-weight: 700;
        font-size: 16px;
        box-shadow: 0 5px 20px rgba(187, 134, 252, 0.4);
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) scale(1.03);
        box-shadow: 0 8px 30px rgba(187, 134, 252, 0.7), 0 0 25px rgba(0, 255, 245, 0.4);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 16px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(26, 26, 46, 0.6);
        border-radius: 10px;
        color: var(--text-muted);
        font-weight: 600;
        padding: 12px 20px;
        border: 1px solid rgba(187, 134, 252, 0.3);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: var(--glow-purple);
        box-shadow: 0 5px 15px rgba(187, 134, 252, 0.4);
    }
    
    /* --- RESPONSE & DISCLAIMER --- */
    .response {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 24px;
        border-radius: 15px;
        margin-top: 24px;
        border: 1px solid;
        border-image: linear-gradient(135deg, var(--glow-purple), var(--glow-cyan)) 1;
    }
    
    .disclaimer {
        background: rgba(255, 184, 77, 0.1);
        border-left: 6px solid #ffb84d;
        padding: 16px;
        border-radius: 10px;
        margin-top: 24px;
        font-weight: 600;
        color: #ffdd99;
    }
    
    .emergency {
        background: linear-gradient(90deg, #f093fb, #f5576c);
        color: white;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        font-weight: 700;
        box-shadow: 0 5px 20px rgba(245, 87, 108, 0.5);
    }
    
    /* --- CIRCULAR STRESS GAUGE --- */
    .stress-meter-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        margin-top: 16px;
        margin-bottom: 24px;
    }
    .circular-gauge {
        position: relative;
        width: 180px;
        height: 180px;
        border-radius: 50%;
        background: conic-gradient(
            #00ff88 0%, 
            #ffc107 50%, 
            #ff6b6b 75%, 
            #d32f2f 100%
        );
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .gauge-inner {
        width: 150px;
        height: 150px;
        border-radius: 50%;
        background: #1a1a2e;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: inset 0 0 15px rgba(0, 0, 0, 0.5);
    }
    .stress-percentage {
        font-size: 42px;
        font-weight: 700;
        color: var(--glow-cyan);
        text-shadow: 0 0 10px rgba(0, 255, 245, 0.7);
    }
    .stress-label {
        font-size: 14px;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    
    </style>
    """, unsafe_allow_html=True
)


# --- Helpers and Model Loading (Your original logic is preserved) ---
@st.cache_resource
def load_emotion_model():
    return pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

emotion_model = load_emotion_model()

def compute_stress_score(model_scores):
    prob = {item['label'].lower(): item['score'] for item in model_scores}
    stress_raw = prob.get('anger', 0.0) + prob.get('fear', 0.0) + prob.get('sadness', 0.0) + prob.get('stress', 0.0)
    return int(round(min(1.0, stress_raw) * 100))

def extract_signals(text):
    txt = text.lower()
    feelings = ["anxious", "anxiety", "depressed", "depression", "sad", "hopeless", "overwhelmed", "stressed", "stress", "panic", "panic attack", "angry", "lonely", "isolated", "hurt", "frustrat", "burnout", "tired", "exhausted", "suicid", "worthless"]
    triggers = ["work", "job", "exam", "relationship", "money", "family", "health", "loss", "breakup", "school", "boss", "study", "deadline"]
    actions = [w for w in feelings if w in txt]
    triggers_found = [t for t in triggers if t in txt]
    serious = []
    if re.search(r"\bkill myself\b|\bi want to die\b|\bi can\'t go on\b|\bi\'m going to end\b", txt): serious.append("suicidal_ideation")
    if re.search(r"\bsleep(ing|s)?\b|\binsomnia\b", txt): serious.append("sleep_issue")
    if re.search(r"\beat(ing|s)?\b|\bappetite\b", txt): serious.append("appetite_change")
    return {"feelings": sorted(set(actions)), "triggers": triggers_found, "serious": serious}

def make_personalized_response(text, score, signals):
    excerpt = textwrap.shorten(text.replace("\n", " "), width=140, placeholder="...")
    if score < 35: level = "LOW — mild or transient stress"
    elif score < 65: level = "MODERATE — notable emotional strain"
    else: level = "HIGH — elevated stress or distress"
    
    sections = [f"**Stress Assessment:** {level} based on your language patterns.", f"**What I hear from you:**\n- \"{excerpt}\""]
    
    if signals["feelings"]:
        sections.append("**Emotional elements detected:**\n``````")
    if signals["triggers"]:
        sections.append(f"**Possible situational triggers:** {', '.join(signals['triggers'])}")
    
    suggestions = []
    if any(w in text.lower() for w in ["anxious", "anxiety", "panic"]): suggestions.append("- Try *box breathing* (inhale 4s, hold 4s, exhale 4s, hold 4s) to find calm.")
    if "sleep_issue" in signals["serious"] or "tired" in signals["feelings"]: suggestions.append("- For sleep, try a 30-min screen-free wind-down before bed.")
    suggestions.append("- Use the *5-4-3-2-1 grounding technique* to connect with your surroundings.")
    suggestions.append("- If you feel safe to do so, share one sentence about your feelings with a trusted person.")
    if score >= 65 or "suicidal_ideation" in signals["serious"]: suggestions.append("- **Please consider contacting a crisis service. If you feel unsafe, call the helpline below immediately.**")
    
    sections.append("**Personalized Coping Suggestions:**\n" + "\n".join(suggestions))
    sections.append("**What to watch for in the next 48 hours:**\n- Mood staying low or worsening\n- Changes in sleep or appetite\n- Any thoughts of self-harm")
    return "\n\n".join(sections)

def transcribe_with_whisper(file_bytes):
    model = whisper.load_model("small")
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(file_bytes)
        tmp = f.name
    try:
        res = model.transcribe(tmp, fp16=False) # fp16=False can improve CPU performance
        return res.get("text", "").strip()
    finally:
        try: os.remove(tmp)
        except Exception: pass

# --- App layout ---
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="title">MINDFUL AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">A confidential AI partner to help you understand and navigate stress.</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["✍️ TEXT ANALYSIS", "🎙️ AUDIO ANALYSIS"])
final_text_input = ""

with tab1:
    user_input_text = st.text_area("Share what you're feeling (write as much or as little as you like):", height=200, placeholder="e.g., I feel overwhelmed at work and can't focus...", label_visibility="collapsed")
    final_text_input = user_input_text

with tab2:
    st.info("Upload a short recording (wav/mp3/m4a). Transcription uses OpenAI's Whisper.")
    uploaded_file = st.file_uploader("Upload audio file", type=["wav", "mp3", "m4a", "ogg"], label_visibility="collapsed")
    if uploaded_file is not None:
        st.audio(uploaded_file)
        if WHISPER_AVAILABLE:
            if st.button("Transcribe Audio for Analysis"):
                with st.spinner("Transcribing audio... This may take a moment."):
                    try:
                        file_bytes = uploaded_file.read()
                        transcribed_text = transcribe_with_whisper(file_bytes)
                        st.session_state.transcribed_text = transcribed_text
                        st.success("Transcription complete!")
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")
            if "transcribed_text" in st.session_state:
                 final_text_input = st.text_area("Transcribed text (edit if needed, then click Analyze):", value=st.session_state.transcribed_text, height=150)
        else:
            st.warning("Whisper is not installed on this server. Please transcribe locally and paste it in the Text tab.")

col1, col2 = st.columns([3, 2])
with col1:
    analyze = st.button("🔍 Analyze & Get Support", use_container_width=True)
with col2:
    st.markdown("<div class='emergency'>In Crisis? Call 1800-599-0019</div>", unsafe_allow_html=True)

if analyze:
    final_text = final_text_input.strip()
    if not final_text:
        st.warning("Please enter some text or transcribe an audio file first.")
    else:
        with st.spinner("Analyzing language patterns for stress markers..."):
            try:
                raw_scores = emotion_model(final_text)[0]
                score = compute_stress_score(raw_scores)
                signals = extract_signals(final_text)
                response_md = make_personalized_response(final_text, score, signals)

                # --- Display new circular gauge ---
                st.markdown(f"""
                <div class="stress-meter-container">
                    <div class="circular-gauge" style="background: conic-gradient(from 0deg, #00ff88 0%, #ffc107 {score-10}%, #ff6b6b {score}%, #1a1a2e {score+10}%, #1a1a2e 100%);">
                        <div class="gauge-inner">
                            <div class="stress-percentage">{score}%</div>
                            <div class="stress-label">Stress</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # --- Display response ---
                st.markdown('<div class="response">', unsafe_allow_html=True)
                st.markdown(response_md)
                st.markdown('</div>', unsafe_allow_html=True)

                if "history" not in st.session_state: st.session_state.history = []
                st.session_state.history.insert(0, {"text": final_text[:80], "score": score})
                
                report = f"Mindful AI — Stress Report\n\nInput excerpt: {final_text[:300]}...\nStress score: {score}%\n\n{response_md}\n\nHelpline: 1800-599-0019"
                st.download_button("Download Report (.txt)", report, file_name="mindful_ai_report.txt")

            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")

if "history" in st.session_state and st.session_state.history:
    st.markdown("<hr style='border-color: rgba(187, 134, 252, 0.2);' />", unsafe_allow_html=True)
    st.markdown("#### Recent Analyses")
    for h in st.session_state.history[:3]:
        st.markdown(f"<div style='font-size:14px; color:var(--text-muted);'>- **{h['score']}%** — *{h['text']}...*</div>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="disclaimer">
    ⚠️ This AI provides supportive guidance and is NOT a substitute for professional medical care. 
    It is an informational tool only. If you are in crisis, please call the 24/7 helpline: <strong>1800-599-0019</strong>.
    </div>
    """, unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)
