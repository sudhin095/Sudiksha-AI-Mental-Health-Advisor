"""
Streamlit Stress Detector App
Single-file Streamlit app that accepts text input or audio upload and returns:
- Stress score (0-100)
- Explanation
- Tips based on score
- Always includes medical disclaimer, loved-ones advice, and helpline 1800-599-0019

Notes:
- This app uses a Hugging Face emotion model by default (e.g. j-hartmann/emotion-english-distilroberta-base).
  The first run will download the model and may take time.
- For audio->text, the app attempts to use OpenAI's whisper (if installed) or falls back to showing instructions.
- Requirements: see bottom of file for requirements.txt content.

How to run:
1. Save this file as streamlit_stress_detector_app.py
2. pip install -r requirements.txt
3. streamlit run streamlit_stress_detector_app.py

"""

import streamlit as st
from transformers import pipeline
import math
import textwrap
from io import BytesIO

# Optional: whisper for local transcription (heavy). If not available, audio upload will show instructions.
try:
    import whisper
    WHISPER_AVAILABLE = True
except Exception:
    WHISPER_AVAILABLE = False

# ---------------------- Helper functions ----------------------
@st.cache_resource
def load_emotion_model(model_name="j-hartmann/emotion-english-distilroberta-base"):
    """Load a Hugging Face text-classification model (returns a pipeline).
    This may download weights on the first run."""
    classifier = pipeline("text-classification", model=model_name, return_all_scores=True)
    return classifier


def calculate_stress_score_from_probs(prob_list):
    """Given a list of {label, score}, compute stress percentage.
    We treat anger, fear, sadness as the primary stress indicators.
    The result is scaled to 0-100."""
    prob_dict = {e["label"]: e["score"] for e in prob_list}

    # Some models use different labels; normalize common ones
    score = 0.0
    for label in ["anger", "fear", "sadness", "stress", "neutral"]:
        if label in prob_dict:
            if label in ["anger", "fear", "sadness", "stress"]:
                score += prob_dict[label]

    # Fallback heuristic: if model doesn't include stress-related labels, use negative valence
    # We clamp and convert to percentage
    stress_pct = max(0.0, min(1.0, score)) * 100
    return round(stress_pct)


def get_stress_tips(score):
    """Return tips string based on stress score (0-100)."""
    if score < 40:
        tips = (
            "• Try slow deep breathing (4 seconds in, 4 seconds out).\n"
            "• Take a short walk or step outside for fresh air.\n"
            "• Write down what you're feeling — journaling helps organize thoughts.\n"
        )
    elif score < 70:
        tips = (
            "• Grounding techniques: name 5 things you can see, 4 you can touch, 3 you can hear.\n"
            "• Reach out and talk to a trusted friend or family member.\n"
            "• Try a 10–15 minute guided relaxation or breathing exercise.\n"
        )
    else:
        tips = (
            "• Pause and focus on breathing — try 6 slow breaths.\n"
            "• Avoid isolating yourself; stay connected to someone you trust.\n"
            "• Consider contacting a mental health professional for support.\n"
        )
    return tips


def generate_explanation(text, score):
    """Generate a brief explanation based on text and numeric score."""
    if score < 40:
        tone = "Your message shows low-to-moderate signs of stress. You may be experiencing transient worry or fatigue."
    elif score < 70:
        tone = "Your message shows moderate signs of stress or emotional burden. Consider reaching out and trying coping techniques."
    else:
        tone = "Your message shows strong signs of stress, anxiety, or emotional distress. Please consider immediate support and professional help."

    # Include a short excerpt (safe) of the user's message to personalize (trim length)
    excerpt = textwrap.shorten(text.replace('\n', ' '), width=150, placeholder='...')
    return f"{tone} Example from your message: \"{excerpt}\""


# ---------------------- Transcription helpers ----------------------

def transcribe_audio_with_whisper(file_bytes: bytes, whisper_model_name: str = "small") -> str:
    """Transcribe audio bytes using whisper (if installed).
    Returns the transcript string.
    Note: whisper requires ffmpeg and may be slow on CPU.
    """
    if not WHISPER_AVAILABLE:
        raise RuntimeError("Whisper is not available. Install openai-whisper or use server-side transcription.")

    model = whisper.load_model(whisper_model_name)
    # Write bytes to a temp buffer and let whisper transcribe
    audio_file = BytesIO(file_bytes)
    # whisper expects a path, but it can accept file-like via tempfile; to keep simple, save to a temp file
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(file_bytes)
        tmp_path = f.name
    try:
        result = model.transcribe(tmp_path)
        text = result.get("text", "").strip()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
    return text


# ---------------------- Streamlit UI ----------------------

st.set_page_config(page_title="Stress Detector — Streamlit", page_icon="🧠", layout="centered")
st.title("🧠 Stress Detector — Text & Voice")
st.caption("Detects stress percentage (0–100%) from text or audio and suggests supportive tips.")

# Sidebar settings
st.sidebar.header("Settings & Info")
model_name = st.sidebar.selectbox(
    "Emotion model (Hugging Face)",
    ("j-hartmann/emotion-english-distilroberta-base", "bhadresh-savani/distilbert-base-uncased-emotion"),
)
whisper_option = st.sidebar.selectbox("Audio transcription method", ("Whisper (local, if installed)", "I will paste text / upload pre-transcribed text"))
show_raw = st.sidebar.checkbox("Show raw model output (probabilities)", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("**Disclaimer & Helpline**\n\nI am not a medical professional. For proper support, please consult a qualified mental health professional. If you feel overwhelmed or unsafe, call the 24/7 helpline: **1800-599-0019**.")

# Main input area: tabs for Text and Voice
tab1, tab2 = st.tabs(["Text input", "Audio upload"])

user_text = ""
transcript = None

with tab1:
    st.subheader("Enter what you're feeling or experiencing")
    user_text = st.text_area("Describe your situation (be as honest as you feel comfortable)", height=200)
    if st.button("Analyze text"):
        if not user_text.strip():
            st.warning("Please write something so I can analyze it.")
        else:
            st.session_state['last_input'] = user_text
            st.session_state['input_type'] = 'text'

with tab2:
    st.subheader("Upload an audio file (wav, mp3) describing how you feel")
    audio_file = st.file_uploader("Upload audio", type=["wav", "mp3", "m4a", "ogg"] )
    if audio_file is not None:
        st.audio(audio_file)
        st.info("Transcription will use Whisper if available on this server. Otherwise please transcribe elsewhere and paste the text in the Text input tab.")
        if st.button("Transcribe & Analyze"):
            file_bytes = audio_file.read()
            try:
                if WHISPER_AVAILABLE and whisper_option.startswith("Whisper"):
                    with st.spinner("Transcribing audio with Whisper (may take a while)..."):
                        transcript = transcribe_audio_with_whisper(file_bytes)
                        st.success("Transcription done. See transcript below.")
                        st.text_area("Transcript", value=transcript, height=150)
                        st.session_state['last_input'] = transcript
                        st.session_state['input_type'] = 'audio'
                else:
                    st.error("Whisper is not installed or not selected. Please transcribe the audio locally and paste into the Text input tab.")
            except Exception as e:
                st.exception(e)

# Analyze when session_state has last_input
if 'last_input' in st.session_state and st.session_state['last_input'].strip():
    text_to_analyze = st.session_state['last_input']

    # Load model (cached)
    with st.spinner("Loading emotion model (if not already loaded)..."):
        try:
            classifier = load_emotion_model(model_name)
        except Exception as e:
            st.error("Failed to load the emotion model. Check your internet connection and model name.\n" + str(e))
            classifier = None

    if classifier is not None:
        with st.spinner("Analyzing text for emotional cues..."):
            try:
                results = classifier(text_to_analyze)[0]  # list of {label, score}
                score = calculate_stress_score_from_probs(results)
                explanation = generate_explanation(text_to_analyze, score)
                tips = get_stress_tips(score)

                # Display the results
                st.markdown("---")
                st.subheader("🧾 Stress Analysis Result")
                st.metric(label="Estimated stress level", value=f"{score}%")

                # Visual progress-like bar
                st.progress(score)

                # Color-coded message
                if score < 40:
                    st.success(f"Low-to-moderate signs of stress ({score}%).")
                elif score < 70:
                    st.warning(f"Moderate signs of stress ({score}%).")
                else:
                    st.error(f"High signs of stress ({score}%). Consider reaching out for help.")

                st.markdown("**What this means**")
                st.write(explanation)

                st.markdown("**Tips to help you right now**")
                st.write(tips)

                st.markdown("**🤝 You're Not Alone**")
                st.write("Talking to someone you trust — a family member, friend, or loved one — can make a big difference.")

                st.markdown("**⚠️ Important**")
                st.write("I am not a medical professional. For proper support, please consider seeking help from a qualified mental health expert.")
                st.write("If you feel overwhelmed or unsafe, please reach out to the 24/7 helpline: **1800-599-0019**.")

                if show_raw:
                    st.markdown("---")
                    st.subheader("Raw model output")
                    st.write(results)

                # Allow user to download a short report
                report = (
                    f"Stress Analysis Report\n\nInput type: {st.session_state.get('input_type','unknown')}\nStress score: {score}%\n\nExplanation:\n{explanation}\n\nTips:\n{tips}\n\nHelpline: 1800-599-0019\n\n(Automated analysis — not a medical diagnosis.)\n"
                )
                st.download_button("Download report (txt)", report, file_name="stress_report.txt")

            except Exception as e:
                st.exception(e)

# Footer: examples and how to improve results
st.markdown("---")
with st.expander("Example prompts and tips for better analysis"):
    st.write(
        "Examples:\n"
        "• \"I haven't been sleeping for days, I feel hopeless and tired.\"\n"
        "• \"Work has been overwhelming, I'm snapping at everyone and can't focus.\"\n"
        "• \"I'm okay but a bit anxious about upcoming exams.\"\n\n"
        "Tips:\n"
        "• Be honest in your description — the model works better with detail.\n"
        "• If using audio, speak clearly and avoid noisy backgrounds.\n"
    )

st.markdown("---")
st.caption("Built for educational/demo purposes. Always include a real clinician for medical workflows.")


# ---------------------- requirements.txt ----------------------
# Save the following lines to requirements.txt when deploying:
# streamlit
# transformers
# torch
# sentencepiece
# librosa
# openai-whisper (optional; heavy) 
# ffmpeg (system dependency for whisper)


# ---------------------- End of file ----------------------
