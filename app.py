# app.py
# Streamlit App for Mental Health Stress Detection (Text + Voice)

import streamlit as st
from transformers import pipeline
from io import BytesIO
import textwrap

# Try loading whisper for audio transcription
try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

st.set_page_config(page_title="Mental Health Stress Detector", page_icon="🧠", layout="centered")
st.title("🧠 Mental Health Stress Detector – Text & Voice")
st.caption("Detect stress levels (0–100%) using AI + Provide Supportive Tips")

# Load emotion model
@st.cache_resource
def load_model():
    return pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

emotion_model = load_model()


def get_stress_score(results):
    prob = {r['label']: r['score'] for r in results}
    score = prob.get("anger", 0) + prob.get("fear", 0) + prob.get("sadness", 0)
    return int(score * 100)


def get_tips(score):
    if score < 40:
        return (
            "• Practice deep breathing (4s inhale, 4s exhale).\n"
            "• Take a short walk or stretch.\n"
            "• Write your thoughts in a journal."
        )
    elif score < 70:
        return (
            "• Try grounding: 5 things you see, 4 you can touch, 3 you hear.\n"
            "• Talk to a trusted friend/family.\n"
            "• Listen to relaxing music or do guided breathing."
        )
    else:
        return (
            "• Take slow deep breaths and sit somewhere calm.\n"
            "• Stay connected with someone you trust.\n"
            "• Consider reaching out for professional help."
        )


def explain(text, score):
    if score < 40:
        base = "You seem to be experiencing mild stress or worry."
    elif score < 70:
        base = "You seem to be dealing with moderate stress or emotional difficulty."
    else:
        base = "You seem to be showing high signs of emotional stress or distress."

    short = textwrap.shorten(text, width=120, placeholder="...")
    return f"{base} Example from your message: '{short}'"


def transcribe_audio(data):
    if not WHISPER_AVAILABLE:
        return None, "Whisper not installed. Cannot transcribe audio."

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

# Tabs
text_tab, audio_tab = st.tabs(["Text Input", "Voice Input"])

# TEXT INPUT
with text_tab:
    user_text = st.text_area("Describe how you're feeling:")
    if st.button("Analyze Text"):
        if user_text.strip():
            results = emotion_model(user_text)[0]
            score = get_stress_score(results)
            explanation = explain(user_text, score)
            tips = get_tips(score)

            st.subheader("Stress Level")
            st.metric("Stress Score", f"{score}%")
            st.progress(score)

            st.subheader("Explanation")
            st.write(explanation)

            st.subheader("Tips to Relieve Stress")
            st.write(tips)

            st.subheader("Important")
            st.write("I am not a medical professional. Please seek medical advice if needed.")
            st.write("Talk to your loved ones — sharing how you feel can help.")
            st.write("If you're overwhelmed, call the helpline: **1800-599-0019**")
        else:
            st.warning("Please enter some text.")

# AUDIO INPUT
with audio_tab:
    file = st.file_uploader("Upload audio (wav/mp3/m4a)", type=["wav", "mp3", "m4a", "ogg"])
    if file:
        st.audio(file)

        if st.button("Transcribe & Analyze Audio"):
            data = file.read()
            text, err = transcribe_audio(data)

            if err:
                st.error("Transcription failed: " + err)
            else:
                st.success("Audio Transcribed:")
                st.write(text)

                results = emotion_model(text)[0]
                score = get_stress_score(results)
                explanation = explain(text, score)
                tips = get_tips(score)

                st.subheader("Stress Level")
                st.metric("Stress Score", f"{score}%")
                st.progress(score)

                st.subheader("Explanation")
                st.write(explanation)

                st.subheader("Tips to Relieve Stress")
                st.write(tips)

                st.subheader("Important")
                st.write("I am not a medical professional. Please seek medical advice if needed.")
                st.write("Talk to your loved ones — sharing how you feel can help.")
                st.write("If you're overwhelmed, call the helpline: **1800-599-0019**")
