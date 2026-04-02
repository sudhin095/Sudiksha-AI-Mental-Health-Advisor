import streamlit as st
import google.generativeai as genai
import re
import time
import tempfile
import os

# ── Page Config ────────────────────────────────────────────────
st.set_page_config(
    page_title="Stress Detector",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── API Key ────────────────────────────────────────────────────
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# ── Model Configuration (Primary → Fallback) ───────────────────
PRIMARY_MODEL  = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-1.5-flash"

# ── Session State Init ─────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "last_request_time" not in st.session_state:
    st.session_state["last_request_time"] = 0
if "mood_tag" not in st.session_state:
    st.session_state["mood_tag"] = ""
if "selected_language" not in st.session_state:
    st.session_state["selected_language"] = "English"
if "voice_transcript" not in st.session_state:
    st.session_state["voice_transcript"] = ""
if "last_audio_id" not in st.session_state:
    st.session_state["last_audio_id"] = None
if "active_model" not in st.session_state:
    st.session_state["active_model"] = PRIMARY_MODEL

# ── Language Options ───────────────────────────────────────────
LANGUAGES = {
    "English": "English",
    "हिंदी (Hindi)": "Hindi",
    "ਪੰਜਾਬੀ (Punjabi)": "Punjabi",
    "தமிழ் (Tamil)": "Tamil",
    "తెలుగు (Telugu)": "Telugu",
    "বাংলা (Bengali)": "Bengali",
    "मराठी (Marathi)": "Marathi",
}

# ── Stress Lexicon ─────────────────────────────────────────────
STRESS_LEXICON = {
    "stressed": 3, "stress": 3, "anxious": 3, "anxiety": 3,
    "overwhelmed": 4, "panic": 4, "depressed": 3, "depression": 3,
    "hopeless": 4, "tired": 2, "exhausted": 3, "worried": 2,
    "fear": 3, "scared": 3, "nervous": 2, "frustrated": 2,
    "angry": 2, "sad": 2, "unhappy": 2, "miserable": 4,
    "worthless": 4, "helpless": 4, "lonely": 3, "isolated": 3,
    "burnout": 4, "pressure": 2, "tense": 2, "upset": 2,
    "crying": 3, "insomnia": 3, "sleepless": 3, "nightmare": 3,
    "suicid": 10, "self-harm": 9, "want to die": 9, "end my life": 9,
}

NEGATION_WORDS = {
    "not", "no", "never", "don't", "doesn't", "didn't",
    "won't", "can't", "couldn't", "shouldn't", "isn't",
    "aren't", "wasn't", "weren't", "hardly", "barely", "neither"
}

DISTANCING_PHRASES = [
    "my friend", "my colleague", "someone i know", "i read about",
    "i heard about", "i learned about", "they said", "he feels",
    "she feels", "people say", "i read that", "a person i know",
    "my classmate", "my neighbor"
]

# ── Negation-Aware Lexicon Scorer ──────────────────────────────
def lexicon_score(text):
    t = text.lower()
    tokens = re.findall(r"\b\w+\b", t)
    score = 0.0
    distancing = any(phrase in t for phrase in DISTANCING_PHRASES)
    multiplier = 0.25 if distancing else 1.0

    for phrase, weight in STRESS_LEXICON.items():
        if " " in phrase and phrase in t:
            phrase_idx = t.find(phrase)
            preceding = t[max(0, phrase_idx - 40):phrase_idx]
            preceding_tokens = re.findall(r"\b\w+\b", preceding)
            negated = any(w in NEGATION_WORDS for w in preceding_tokens[-4:])
            if not negated:
                score += weight * multiplier

    for i, token in enumerate(tokens):
        for kw, weight in STRESS_LEXICON.items():
            if " " in kw:
                continue
            if token == kw or token.startswith(kw):
                window = tokens[max(0, i - 4):i]
                negated = any(w in NEGATION_WORDS for w in window)
                if not negated:
                    score += weight * multiplier

    return round(score, 2)


# ── Gemini Helper with Primary → Fallback ─────────────────────
def safe_generate(prompt, fallback="Unable to generate response."):
    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            st.session_state["active_model"] = model_name
            return response.text.strip()
        except Exception as e:
            if model_name == FALLBACK_MODEL:
                st.session_state["active_model"] = f"{FALLBACK_MODEL} (error)"
                return f"{fallback} (Error: {str(e)[:80]})"
            continue
    return fallback


# ── Structured Stress Analysis ─────────────────────────────────
def ask_model_for_structured_stress(text):
    prompt = f"""Analyze the stress level in this text and respond in JSON only.
Text: "{text}"
Respond exactly like this:
{{
  "stress_score": <0-10 float>,
  "primary_emotion": "<emotion>",
  "confidence": "<low|medium|high>"
}}"""
    result = safe_generate(prompt, fallback='{"stress_score": 5, "primary_emotion": "unknown", "confidence": "low"}')
    try:
        json_match = re.search(r'\{.*?\}', result, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group())
    except Exception:
        pass
    return {"stress_score": 5.0, "primary_emotion": "unknown", "confidence": "low"}


def ask_model_for_intensity(text):
    prompt = f"""Rate the emotional intensity of this text as one word only: mild, moderate, severe, or critical.
Text: "{text}"
Respond with one word only."""
    result = safe_generate(prompt, fallback="moderate")
    result = result.strip().lower()
    if result in ["mild", "moderate", "severe", "critical"]:
        return result
    return "moderate"


def build_support_prompt(text, stress_label, intensity_label, lang="English"):
    return f"""You are a compassionate mental health support assistant.
A person shared: "{text}"
Stress Level: {stress_label} | Intensity: {intensity_label}

Respond with empathy and practical coping suggestions.
IMPORTANT: Respond entirely in {lang}. If {lang} is not English, write your full response in {lang}.
Keep it warm, supportive, and under 200 words."""


def get_stress_level(text, lang="English"):
    lex = lexicon_score(text)
    structured = ask_model_for_structured_stress(text)
    ai_score = float(structured.get("stress_score", 5.0))
    intensity_label = ask_model_for_intensity(text)

    final_level = (lex * 0.45 + ai_score * 10 * 0.30 + {
        "mild": 2, "moderate": 5, "severe": 8, "critical": 10
    }.get(intensity_label, 5) * 10 * 0.25)
    final_level = min(100, max(0, final_level))

    if final_level < 25:
        stress_label = "🟢 Low Stress"
    elif final_level < 50:
        stress_label = "🟡 Mild Stress"
    elif final_level < 75:
        stress_label = "🟠 Moderate Stress"
    else:
        stress_label = "🔴 High Stress"

    support_prompt = build_support_prompt(text, stress_label, intensity_label, lang=lang)
    support_response = safe_generate(support_prompt)

    return {
        "final_level": round(final_level, 1),
        "stress_label": stress_label,
        "intensity": intensity_label,
        "primary_emotion": structured.get("primary_emotion", "unknown"),
        "confidence": structured.get("confidence", "low"),
        "lexicon_score": lex,
        "ai_score": round(ai_score, 2),
        "support": support_response,
    }


# ── Voice Transcription with Primary → Fallback ────────────────
def transcribe_and_analyze_audio(audio_bytes):
    tmp_path = None
    uploaded_file = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        uploaded_file = genai.upload_file(tmp_path, mime_type="audio/wav")

        import time as _time
        for _ in range(20):
            file_info = genai.get_file(uploaded_file.name)
            if file_info.state.name == "ACTIVE":
                break
            _time.sleep(1)

        transcription_prompt = [
            "Please transcribe this audio recording exactly as spoken. Return only the transcribed text, nothing else.",
            uploaded_file
        ]

        for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(transcription_prompt)
                st.session_state["active_model"] = model_name
                return response.text.strip()
            except Exception:
                if model_name == FALLBACK_MODEL:
                    raise
                continue

    except Exception as e:
        return f"[Transcription error: {str(e)[:100]}]"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
        if uploaded_file:
            try:
                genai.delete_file(uploaded_file.name)
            except Exception:
                pass


# ── Breathing Widget ───────────────────────────────────────────
def show_breathing_widget():
    st.markdown("---")
    st.markdown("### 🧘 Breathing Exercise")
    st.markdown("High stress detected. Try this 4-7-8 breathing exercise:")
    breathing_html = """
    <style>
    @keyframes breathe {
        0%   { transform: scale(1);   background: #4CAF50; opacity: 0.7; }
        36%  { transform: scale(1.6); background: #2196F3; opacity: 1;   }
        78%  { transform: scale(1.6); background: #9C27B0; opacity: 0.9; }
        100% { transform: scale(1);   background: #4CAF50; opacity: 0.7; }
    }
    .breath-circle {
        width: 120px; height: 120px; border-radius: 50%;
        background: #4CAF50;
        animation: breathe 19s ease-in-out infinite;
        margin: 20px auto; display: flex; align-items: center;
        justify-content: center; color: white; font-weight: bold;
        font-size: 13px; text-align: center;
        box-shadow: 0 0 30px rgba(76,175,80,0.4);
    }
    .breath-label { font-size: 13px; text-align: center; color: #888; margin-top: -10px; }
    </style>
    <div style="text-align:center">
        <div class="breath-circle" id="bc">Inhale<br>4s</div>
        <p class="breath-label" id="bl">Breathe in slowly through your nose</p>
    </div>
    <script>
    (function(){
        const circle = document.getElementById('bc');
        const label  = document.getElementById('bl');
        const steps  = [
            {t:4000,  text:"Inhale\\n4s",  hint:"Breathe in slowly through your nose"},
            {t:7000,  text:"Hold\\n7s",    hint:"Hold your breath gently"},
            {t:8000,  text:"Exhale\\n8s",  hint:"Exhale slowly through your mouth"},
        ];
        let i = 0;
        function next(){
            const s = steps[i % steps.length];
            circle.innerHTML = s.text.replace('\\n','<br>');
            label.textContent = s.hint;
            i++;
            setTimeout(next, s.t);
        }
        next();
    })();
    </script>
    """
    st.components.v1.html(breathing_html, height=200)


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.title("🧠 Stress Detector")

    # ── Model Status Badge ─────────────────────────────────────
    active = st.session_state.get("active_model", PRIMARY_MODEL)
    if "error" in str(active):
        st.warning(f"⚠️ Model error: `{FALLBACK_MODEL}`")
    elif active == FALLBACK_MODEL:
        st.info(f"🔄 Fallback active: `{FALLBACK_MODEL}`")
    else:
        st.success(f"✅ Model: `{PRIMARY_MODEL}`")

    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "This app analyzes your text or voice input to detect stress levels "
        "using AI and a keyword lexicon."
    )
    st.markdown("---")
    st.markdown("### 🚨 Crisis Support")
    st.markdown("**KIRAN Mental Health:** `1800-599-0019` (Free, 24/7)")
    st.markdown("**iCall:** `9152987821`")
    st.markdown("---")
    st.markdown("### Tips")
    st.markdown("- Be honest in your input\n- Use complete sentences\n- Try voice for natural expression")


# ══════════════════════════════════════════════════════════════
# MAIN LAYOUT
# ══════════════════════════════════════════════════════════════
st.title("🧠 Mental Health Stress Detector")
st.markdown("Analyze your stress levels through text or voice. Your data stays private.")

tab_text, tab_voice = st.tabs(["📝 Text Input", "🎙️ Voice Input"])


# ──────────────────────────────────────────────────────────────
# TEXT TAB
# ──────────────────────────────────────────────────────────────
with tab_text:
    st.markdown("#### Tell us how you're feeling")

    selected_lang_label = st.selectbox(
        "🌐 Response Language",
        options=list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(
            next(k for k, v in LANGUAGES.items() if v == st.session_state["selected_language"])
        ),
    )
    st.session_state["selected_language"] = LANGUAGES[selected_lang_label]

    st.markdown("**Quick mood tags** — tap to pre-fill:")
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        if st.button("😔 Sad"):
            st.session_state["mood_tag"] = "I am feeling very sad and low today. "
    with mc2:
        if st.button("😤 Angry"):
            st.session_state["mood_tag"] = "I am feeling very angry and frustrated today. "
    with mc3:
        if st.button("😰 Anxious"):
            st.session_state["mood_tag"] = "I am feeling very anxious and worried today. "
    with mc4:
        if st.button("😶 Clear"):
            st.session_state["mood_tag"] = ""

    typed_text = st.text_area(
        "How are you feeling?",
        value=st.session_state["mood_tag"],
        placeholder="Describe your feelings in your own words...",
        height=130,
        max_chars=2000,
    )

    if st.button("🔍 Analyze Stress", use_container_width=True, key="analyze_text"):
        input_text = typed_text.strip()
        if not input_text:
            st.warning("Please enter some text or use a mood tag before analyzing.")
        else:
            now = time.time()
            elapsed = now - st.session_state["last_request_time"]
            if elapsed < 5:
                remaining = int(5 - elapsed)
                st.warning(f"⏳ Please wait {remaining} second(s) before analyzing again.")
            else:
                st.session_state["last_request_time"] = time.time()
                lang = st.session_state["selected_language"]
                with st.spinner("Analyzing your stress levels..."):
                    result = get_stress_level(input_text, lang=lang)

                final_level = result["final_level"]

                if final_level >= 75:
                    st.error("🚨 High stress detected. Please consider calling KIRAN: **1800-599-0019** (Free, 24/7)")

                col1, col2 = st.columns([1, 2])
                with col1:
                    st.metric("Stress Level", f"{final_level}%")
                    st.metric("Category", result["stress_label"])
                    st.metric("Intensity", result["intensity"].capitalize())
                    st.metric("Primary Emotion", result["primary_emotion"].capitalize())

                with col2:
                    st.markdown("#### 💬 Support Response")
                    st.info(result["support"])

                with st.expander("📊 Score Breakdown"):
                    st.write(f"**Lexicon Score:** {result['lexicon_score']}")
                    st.write(f"**AI Score (0–10):** {result['ai_score']}")
                    st.write(f"**Model Confidence:** {result['confidence']}")
                    st.write(f"**Model Used:** `{st.session_state.get('active_model', PRIMARY_MODEL)}`")

                if final_level > 70:
                    show_breathing_widget()


# ──────────────────────────────────────────────────────────────
# VOICE TAB
# ──────────────────────────────────────────────────────────────
with tab_voice:
    st.markdown("#### Record your voice")

    v_lang_label = st.selectbox(
        "🌐 Response Language",
        options=list(LANGUAGES.keys()),
        index=list(LANGUAGES.keys()).index(
            next(k for k, v in LANGUAGES.items() if v == st.session_state["selected_language"])
        ),
        key="voice_lang"
    )
    st.session_state["selected_language"] = LANGUAGES[v_lang_label]

    try:
        from audio_recorder_streamlit import audio_recorder
        audio_data = audio_recorder(
            text="Click to record",
            recording_color="#e74c3c",
            neutral_color="#3498db",
            icon_size="2x",
        )
    except ImportError:
        st.error("Install `audio-recorder-streamlit`: `pip install audio-recorder-streamlit`")
        audio_data = None

    if audio_data is not None:
        audio_id = hash(audio_data)

        if audio_id != st.session_state.get("last_audio_id"):
            st.session_state["last_audio_id"] = audio_id
            with st.spinner("🎙️ Transcribing your voice..."):
                transcript = transcribe_and_analyze_audio(audio_data)
            st.session_state["voice_transcript"] = transcript

        if st.session_state["voice_transcript"]:
            st.markdown("**Transcript:**")
            st.success(st.session_state["voice_transcript"])

            vc1, vc2 = st.columns(2)
            with vc1:
                analyze_voice = st.button("🔍 Analyze Voice", use_container_width=True)
            with vc2:
                if st.button("🗑️ Clear Transcript", use_container_width=True):
                    st.session_state["voice_transcript"] = ""
                    st.session_state["last_audio_id"] = None
                    st.rerun()

            if analyze_voice:
                now = time.time()
                elapsed = now - st.session_state["last_request_time"]
                if elapsed < 5:
                    remaining = int(5 - elapsed)
                    st.warning(f"⏳ Please wait {remaining} second(s) before analyzing again.")
                else:
                    st.session_state["last_request_time"] = time.time()
                    lang = st.session_state["selected_language"]
                    with st.spinner("Analyzing stress from voice transcript..."):
                        result = get_stress_level(st.session_state["voice_transcript"], lang=lang)

                    final_level = result["final_level"]

                    if final_level >= 75:
                        st.error("🚨 High stress detected. Please consider calling KIRAN: **1800-599-0019**")

                    vc_col1, vc_col2 = st.columns([1, 2])
                    with vc_col1:
                        st.metric("Stress Level", f"{final_level}%")
                        st.metric("Category", result["stress_label"])
                        st.metric("Intensity", result["intensity"].capitalize())
                        st.metric("Primary Emotion", result["primary_emotion"].capitalize())

                    with vc_col2:
                        st.markdown("#### 💬 Support Response")
                        st.info(result["support"])

                    with st.expander("📊 Score Breakdown"):
                        st.write(f"**Lexicon Score:** {result['lexicon_score']}")
                        st.write(f"**AI Score (0–10):** {result['ai_score']}")
                        st.write(f"**Model Confidence:** {result['confidence']}")
                        st.write(f"**Model Used:** `{st.session_state.get('active_model', PRIMARY_MODEL)}`")

                    if final_level > 70:
                        show_breathing_widget()
    else:
        st.info("🎙️ Press the button above to start recording.")

# ── Footer ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<center><small>This app is not a substitute for professional mental health care.</small></center>",
    unsafe_allow_html=True,
)
