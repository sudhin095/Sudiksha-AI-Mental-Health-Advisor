# app.py (Premium UI + Personalized Responses + Highlighted Disclaimer)
import streamlit as st
from transformers import pipeline
from io import BytesIO
import textwrap
import re

# Try loading whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

# ------------------- PAGE CONFIG -------------------
st.set_page_config(page_title="Premium Mental Health Stress Detector", page_icon="💙", layout="centered")

# Custom CSS for premium aesthetic UI
st.markdown(
    """
    <style>
        body {
            background-color: #f0f4f8;
        }
        .main-container {
            background: white;
            padding: 40px;
            border-radius: 25px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.12);
            max-width: 900px;
            margin: auto;
            border: 1px solid #e6e6e6;
        }
        .title-text {
            font-size: 48px;
            font-weight: 900;
            text-align: center;
            background: linear-gradient(90deg, #2b5876, #4e4376);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
        }
        .subtitle-text {
            font-size: 18px;
            text-align: center;
            color: #555;
            margin-bottom: 30px;
        }
        .response-box {
            background: #ffffff;
            border-left: 6px solid #4e4376;
            padding: 20px;
            border-radius: 12px;
            font-size: 17px;
            line-height: 1.7;
        }
        .disclaimer {
            margin-top: 25px;
            font-size: 15px;
            color: #a80000 !important;
            font-weight: 600;
            border-top: 1px solid #ffb3b3;
            padding-top: 15px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="title-text">💙 Premium Mental Health Stress Detector</div>', unsafe_allow_html=True)

# 🔧 FIXED: Changed subtitle → subtitle-text
st.markdown(
    '<div class="subtitle-text">AI-powered stress detection with supportive, personalized guidance</div>',
    unsafe_allow_html=True
)

# ------------------- LOAD MODEL -------------------
@st.cache_resource
def load_model():
    return pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

emotion_model = load_model()

# ------------------- FUNCTIONS -------------------
def get_stress_score(results):
    prob = {r['label']: r['score'] for r in results}
    score = prob.get("anger", 0) + prob.get("fear", 0) + prob.get("sadness", 0)
    return int(score * 100)


def generate_personalized_response(text, score):
    # Extract keywords to personalize advice
    words = re.findall(r"[a-zA-Z]+", text.lower())
    negative_words = [w for w in words if w in [
        "tired", "depressed", "anxious", "alone", "overwhelmed", "cry", "panic",
        "hopeless", "stress", "angry", "fear", "sad", "problem", "pressure"
    ]]

    extracted = ", ".join(set(negative_words)) if negative_words else "your described experience"

    # Response varies with stress level
    if score < 40:
        level_msg = "You seem to be dealing with mild emotional stress or worry."
    elif score < 70:
        level_msg = "Your message reflects moderate stress, indicating emotional pressure or discomfort." 
    else:
        level_msg = "You appear to be facing high emotional stress or distress, and immediate supportive steps may help you feel safer and grounded."

    # Personalized long-form bullet-point response
    response = f"""
### 🧠 What Your Message Indicates
{level_msg}

### 🧩 Key Emotional Elements Detected
- Your message shows emotional signals related to **{extracted}**.
- These patterns may reflect what you are internally processing.
- It's important to acknowledge these feelings — they are valid.

### 💡 Personalized Guidance For You
- Try grounding yourself by taking **slow, deep breaths** and focusing on your surroundings.
    - Consider gently expressing your emotions to someone you trust.
- Engage in a simple calming activity such as listening to soft music, stepping outside, or writing your thoughts.
- Remind yourself that what you're feeling is **not permanent** — small steps can create relief.

### 🌱 Practical Steps You Can Try Right Now
- Break your current stressor into smaller, manageable parts.
- Give yourself permission to rest — your mind may need a reset.
- If possible, shift your environment briefly (different room, walk, sunlight).
- Practice the 5-4-3-2-1 method to reduce overwhelming thoughts.
"""
    return response


def transcribe_audio(data):
    if not WHISPER_AVAILABLE:
        return None, "Whisper not installed."
    try:
        model = whisper.load_model("small")
        import tempfile, os
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(data)
            temp_path = f.name
        result = model.transcribe(temp_path)
        os.remove(temp_path)
        return result.get("text", "").strip(), None
    except Exception as e:
        return None, str(e)

# ------------------- UI TABS -------------------
text_tab, audio_tab = st.tabs(["📝 Text Input", "🎤 Voice Input"])

# ------------------- TEXT INPUT -------------------
with text_tab:
    user_text = st.text_area("Describe how you're feeling in detail:", height=200)

    if st.button("Analyze Text", use_container_width=True):
        if user_text.strip():
            results = emotion_model(user_text)[0]
            score = get_stress_score(results)
            personalized = generate_personalized_response(user_text, score)

            st.markdown(f"### Stress Level: **{score}%**")
            st.progress(score)

            st.markdown(personalized)

            st.markdown(
                """
                <div class="disclaimer-box">
                <b>⚠️ Disclaimer</b><br>
                I am not a medical professional. Please seek medical advice if you feel the need.<br>
                Talk to your loved ones — sharing your feelings can truly help.<br>
                If you're overwhelmed, call the helpline: <b>1800-599-0019</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.warning("Please describe your feelings so I can analyze them.")

# ------------------- AUDIO INPUT -------------------
with audio_tab:
    file = st.file_uploader("Upload audio describing your feelings (wav/mp3/m4a)", type=["wav", "mp3", "m4a", "ogg"])

    if file and st.button("Transcribe & Analyze Audio", use_container_width=True):
        data = file.read()
        text, err = transcribe_audio(data)

        if err:
            st.error("Transcription Error: " + err)
        else:
            st.success("Transcription Successful:")
            st.write(text)

            results = emotion_model(text)[0]
            score = get_stress_score(results)
            personalized = generate_personalized_response(text, score)

            st.markdown(f"### Stress Level: **{score}%**")
            st.progress(score)

            st.markdown(personalized)

            st.markdown(
                """
                <div class="disclaimer-box">
                <b>⚠️ Disclaimer</b><br>
                I am not a medical professional. Please seek medical advice if needed.<br>
                Talk to your loved ones — sharing how you feel can make a big difference.<br>
                If you're overwhelmed, call: <b>1800-599-0019</b>
                </div>
                """,
                unsafe_allow_html=True,
            )
