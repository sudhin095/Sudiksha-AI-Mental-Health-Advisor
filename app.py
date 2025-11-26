# app.py
import streamlit as st
from streamlit_mic_recorder import mic_recorder
import re
import json
import time
import requests
import streamlit.components.v1 as components

# =========================
# OPENROUTER API KEY (Secrets)
# =========================
try:
    OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
except Exception:
    OPENROUTER_API_KEY = None

if not OPENROUTER_API_KEY:
    st.error("⚠️ No OPENROUTER_API_KEY found. Add it to .streamlit/secrets.toml (OPENROUTER_API_KEY).")
    st.stop()

# =========================
#  PAGE CONFIG + CSS (UNCHANGED)
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

# ====== MODEL NAMES (UI LABELS) ======
MODEL_NAMES = {
    "Qwen 2.5-72B (Primary)": "qwen/qwen2.5-72b-instruct",
    "Mistral 7B Instruct (Fallback)": "mistralai/mistral-7b-instruct"
}
SIDEBAR_MODEL_KEYS = list(MODEL_NAMES.keys())

# -------------------------
# OpenRouter call helper
# -------------------------
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def call_openrouter(model, prompt, max_tokens=700, timeout_secs=25):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.2
    }
    try:
        r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=timeout_secs)
        if r.status_code == 200:
            j = r.json()
            return j["choices"][0]["message"]["content"]
        else:
            st.warning(f"OpenRouter returned {r.status_code}: {r.text[:200]}")
            return None
    except Exception as e:
        st.info(f"Model call failed: {str(e)}")
        return None

# -------------------------
# Safe generate wrapper
# -------------------------
def safe_generate(prompt, preferred_model=None):
    models_try = []
    if preferred_model:
        models_try.append(preferred_model)
    if "qwen" not in (preferred_model or ""):
        models_try.append(MODEL_NAMES["Qwen 2.5-72B (Primary)"])
    models_try.append(MODEL_NAMES["Mistral 7B Instruct (Fallback)"])

    for m in models_try:
        out = call_openrouter(m, prompt)
        if out:
            if m != MODEL_NAMES["Qwen 2.5-72B (Primary)"]:
                st.warning("⚠️ Using fallback model (Mistral 7B). Primary model unavailable or timed out.")
            return out
        time.sleep(0.2)
    return None

# -------------------------
# Lexicon scoring
# -------------------------
LEXICON_WEIGHTS = {
    "suicid": 5, "kill myself": 5, "end my life": 5, "i want to die": 5, "worthless": 4,
    "panic": 4, "panic attack": 4, "hopeless": 4, "overwhelmed": 4, "can't cope": 4,
    "anxious": 3, "anxiety": 3, "depressed": 3, "depression": 3, "stress": 3, "stressed": 3,
    "tired": 1.5, "exhausted": 2, "can't sleep": 2, "insomnia": 2, "angry": 1.5, "sad": 2
}

def lexicon_score(text):
    t = text.lower()
    score = sum(w for kw, w in LEXICON_WEIGHTS.items() if kw in t)
    if any(k in t for k in ["suicid", "kill myself", "i want to die", "end my life"]):
        score = max(score, 8.0)
    return int(round(min(1.0, score / 10.0) * 100))

# -------------------------
# Model intensity and structured JSON
# -------------------------
def ask_model_for_intensity(user_text, model_name=None):
    prompt = (
        "You are an evaluator that gives a concise numeric emotional intensity score.\n"
        "Reply with ONLY valid JSON: {\"intensity\": <0-100>, \"confidence\": <0.0-1.0>}.\n\n"
        f"Text: {user_text}\n"
    )
    out = safe_generate(prompt, preferred_model=model_name)
    if not out:
        return None
    match = re.search(r"\{[\s\S]*?\}", out)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        return {
            "intensity": int(max(0, min(100, int(data.get("intensity", 50))))),
            "confidence": float(max(0.0, min(1.0, float(data.get("confidence", 0.5)))))
        }
    except Exception:
        return None

def ask_model_for_structured_stress(user_text, model_name=None):
    prompt = (
        "Return ONLY a single JSON object with keys:\n"
        "score: integer 0-100\n"
        "evidence: array of brief verbatim phrases from the user's text\n"
        "confidence: float 0.0-1.0\n\n"
        f"User text:\n{user_text}\n\n"
        "Example: {\"score\":72, \"evidence\": [\"I can't sleep\"], \"confidence\":0.83}"
    )
    out = safe_generate(prompt, preferred_model=model_name)
    if not out:
        return None
    txt = out.strip().replace("'", '"')
    match = re.search(r'\{[\s\S]*\}', txt)
    if not match:
        return None
    try:
        data = json.loads(match.group())
    except Exception:
        repaired = re.sub(r'(\w+):', r'"\1":', match.group())
        try:
            data = json.loads(repaired)
        except Exception:
            return None
    return {
        "model_score": int(max(0, min(100, int(data.get("score", 50))))),
        "evidence": data.get("evidence", []),
        "confidence": float(max(0.0, min(1.0, float(data.get("confidence", 0.5)))))
    }

# -------------------------
# Combined scoring
# -------------------------
def get_stress_level(user_text, model_name=None):
    lex = lexicon_score(user_text)
    structured = ask_model_for_structured_stress(user_text, model_name=model_name)
    reasoning = ask_model_for_intensity(user_text, model_name=model_name)

    model_score = structured["model_score"] if structured else None
    model_conf = structured.get("confidence", 0.5) if structured else 0.0
    reasoning_score = reasoning["intensity"] if reasoning else None
    reasoning_conf = reasoning.get("confidence", 0.5) if reasoning else 0.0

    w_model = 0.45 * (0.5 + 0.5 * model_conf)
    w_reason = 0.25 * (0.5 + 0.5 * reasoning_conf)
    w_lex = 1.0 - (w_model + w_reason)
    if w_lex < 0.1:
        w_lex = 0.1
        total = w_model + w_reason + w_lex
        w_model /= total
        w_reason /= total
        w_lex /= total

    if model_score is None:
        w_model, w_lex, w_reason = 0.0, 0.75, 0.25
    if reasoning_score is None:
        if model_score is None:
            w_reason = 0.0
        else:
            w_model += w_reason * 0.6
            w_lex += w_reason * 0.4
            w_reason = 0.0

    ms = model_score if model_score is not None else 50
    rs = reasoning_score if reasoning_score is not None else ms
    final = int(round(ms * w_model + lex * w_lex + rs * w_reason))
    final = max(0, min(100, final))

    meta = {
        "model_score": ms if model_score is not None else None,
        "model_conf": model_conf if model_score is not None else None,
        "lex_score": lex,
        "reasoning_score": rs if reasoning_score is not None else None,
        "weights": {"model": round(w_model, 3), "lex": round(w_lex, 3), "reason": round(w_reason, 3)}
    }
    return final, meta

def get_stress_desc(level):
    if level < 25: return "😌 Minimal Stress — You seem calm."
    if level < 50: return "🙂 Mild Stress — Manageable tension."
    if level < 75: return "😟 Moderate Stress — Consider coping tools."
    return "😰 High Stress — Strong distress detected."

# -------------------------
# Support prompt builder
# -------------------------
def build_support_prompt(mode, text):
    return f"""
You are a deeply empathetic professional mental-health assistant.
Use the user's exact phrases where relevant. Be specific and avoid generic stock responses.

User text:
{text}

Mode: {mode}

Produce a structured response in Markdown with these sections:
- Brief personalized validation (quote exact phrases)
- 4 tailored coping actions (why each helps for this user)
- Immediate 12–24 hour plan (3 items)
- How to phrase asking for help to a loved one (one-sentence script)
- Warning signs to monitor and when to seek professional help

End with the exact disclaimer block (do not vary):
----------------------------------------
⚠ **Important Disclaimer**
This AI may be inaccurate. Please seek medical advice from a professional.  
Talk to your loved ones for support.  
**Indian Mental Health Helpline:** 1800-599-0019
----------------------------------------
"""

# -------------------------
# UI HEADER
# -------------------------
st.markdown("""
<div class="main-header">
    <h1>🧠 Mental Health AI</h1>
    <p>Premium stress detector & crisis support tool</p>
</div>
""", unsafe_allow_html=True)

# QUOTES
st.markdown("""
<div style="
    background:rgba(49,24,94,0.55);
    padding:1rem 1.4rem;
    border-radius:14px;
    color:#e8d6ff;
    margin-top:-1rem;
    margin-bottom:1.5rem;
    box-shadow:0 4px 14px #31185e50;
    font-size:0.95rem;
    font-style:italic;">
“If you're going through hell, keep going.”<br>
“If there is something that means a lot to you, do not postpone it.”
</div>
""", unsafe_allow_html=True)

# -------------------------
# SIDEBAR
# -------------------------
with st.sidebar:
    st.write("## Settings")
    chosen_model_name = st.selectbox("Choose AI Model", SIDEBAR_MODEL_KEYS, index=0)
    model_id = MODEL_NAMES[chosen_model_name]
    mode = st.radio("Analysis Mode", ["Crisis Detection", "Emotional Support", "Risk Assessment"])
    st.write("### Emergency Resources")
    st.info("**KIRAN:** 1800-599-0019\n**Vandrevala:** 1860-2662-345\n**iCall:** 9152987821")

# -------------------------
# Web Speech API HTML
# -------------------------
def web_speech_transcriber():
    html = """
    <div style="color: #e8d6ff; font-family: Inter, sans-serif;">
      <p style="margin-bottom:6px;">Click <b>Start</b> and speak. Click <b>Stop</b> to finish. (Browser-based, free)</p>
      <button id="startBtn" style="padding:8px 14px;border-radius:8px;margin-right:8px;">Start</button>
      <button id="stopBtn" style="padding:8px 14px;border-radius:8px;">Stop</button>
      <div id="status" style="margin-top:8px;font-size:0.95rem;color:#c9aaff;"></div>
      <div id="transcript" style="margin-top:10px;padding:10px;background:#111827;border-radius:8px;color:#e6eef8;min-height:60px;"></div>
    </div>
    <script>
      const startBtn = document.getElementById("startBtn");
      const stopBtn = document.getElementById("stopBtn");
      const status = document.getElementById("status");
      const transcriptDiv = document.getElementById("transcript");
      let recognition;
      let finalTranscript = "";
      if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
        status.textContent = "❌ Browser does not support Web Speech API. Use Text tab.";
      } else {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        recognition.lang = "en-US";
        recognition.interimResults = true;
        recognition.continuous = true;
        recognition.onstart = () => { status.textContent = "🎙️ Listening..."; }
        recognition.onend = () => { status.textContent = "⏹️ Stopped."; }
        recognition.onerror = (e) => { status.textContent = "Error: " + e.error; }
        recognition.onresult = (event) => {
          let interim = "";
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            if (event.results[i].isFinal) {
              finalTranscript += event.results[i][0].transcript;
              finalTranscript += " ";
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          transcriptDiv.innerHTML = "<b>Transcript (live):</b><br>" + finalTranscript + "<i style='opacity:0.7'>" + interim + "</i>";
        };
      }

      startBtn.onclick = () => {
        finalTranscript = "";
        transcriptDiv.innerHTML = "";
        try { recognition.start(); } catch(e) {}
        status.textContent = "🎙️ Listening...";
      };
      stopBtn.onclick = () => {
        try { recognition.stop(); } catch(e) {}
        status.textContent = "⏹️ Stopped.";
        const payload = finalTranscript.trim();
        if (typeof window.parent !== "undefined" && window.parent.Streamlit) {
          window.parent.Streamlit.setComponentValue(payload);
        } else if (typeof Streamlit !== "undefined") {
          Streamlit.setComponentValue(payload);
        } else {
          window.parent.postMessage({ type: "STREAMLIT_WEB_SPEECH", transcript: payload }, "*");
        }
      };
    </script>
    """
    return components.html(html, height=220)

# -------------------------
# MAIN UI
# -------------------------
col1, col2 = st.columns([2, 1])

with col1:
    tab1, tab2 = st.tabs(["✍️ Text", "🎤 Voice"])
    input_text = ""

    with tab1:
        st.markdown('<div class="info-card"><h3>Write your feelings</h3>', unsafe_allow_html=True)
        input_text = st.text_area("Describe your feelings, challenges, or thoughts.", height=160, key="txt_input")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="info-card"><h3>Speak your mind</h3>', unsafe_allow_html=True)
        st.info("Click Start → speak → Stop. The transcript will populate the Text box. (Browser-based, free)")
        transcript_value = web_speech_transcriber()
        audio_data = mic_recorder(
            start_prompt="🎤 Start Recording",
            stop_prompt="⏹️ Stop",
            just_once=False,
            use_container_width=True,
            key="mic"
        )
        if audio_data is not None:
            st.audio(audio_data["bytes"], format="audio/wav")
            st.success("✅ Recording saved!")

        if transcript_value and isinstance(transcript_value, str) and transcript_value.strip():
            st.session_state["txt_input"] = transcript_value.strip()
            st.success("Transcription captured into the text box.")

    if st.button("🔍 Analyze & Get Support", use_container_width=True) and st.session_state.get("txt_input", "").strip():
        with st.spinner("Analyzing..."):
            input_text = st.session_state.get("txt_input", "")
            final_level, meta = get_stress_level(input_text, model_name=model_id)

            st.markdown(f"""
            <div class="stress-meter-container">
                <div class="circular-gauge">
                    <div class="gauge-inner">
                        <div class="stress-percentage">{final_level}%</div>
                        <div class="stress-label">Stress</div>
                    </div>
                </div>
                <div style="color:#bb86fc;margin-top:10px;">{get_stress_desc(final_level)}</div>
            </div>
            """, unsafe_allow_html=True)

            support_prompt = build_support_prompt(mode, input_text)
            response_text = safe_generate(support_prompt, preferred_model=model_id)

            st.markdown('<div class="response-area">', unsafe_allow_html=True)
            if response_text:
                st.markdown("### AI Support\n" + response_text)
            else:
                fallback_text = f"""
### AI Support (Fallback)
- **Validation:** I hear that you're saying: "{input_text[:120]}..." — that sounds distressing and important.
- **Immediate steps (tailored):**
  1. Take 3 minutes of diaphragmatic breathing.
  2. Write one small step you can take now.
  3. Reach out to one trusted person: "I need to talk — I haven't been okay lately."
- **12–24 hour plan:** sleep hygiene, short walk outside, limit caffeine, connect with someone.
- **When to seek help:** if you have thoughts of harming yourself, call a helpline immediately.
----------------------------------------
⚠ **Important Disclaimer**
This AI may be inaccurate. Please seek medical advice from a professional.  
Talk to your loved ones for support.  
**Indian Mental Health Helpline:** 1800-599-0019
----------------------------------------
"""
                st.markdown(fallback_text)
            st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="info-card"><h3>Why Mindful?</h3>- Modern, safe, and confidential\n- Qwen 2.5 / Mistral 7B models\n- 24/7 crisis guidance</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-card"><h3>Modes</h3>- Crisis Detection\n- Emotional Support\n- Risk Assessment</div>', unsafe_allow_html=True)
    st.markdown('<div class="emergency-banner">🚨 IN CRISIS? CALL KIRAN 1800-599-0019 🚨</div>', unsafe_allow_html=True)

st.markdown('---')
st.markdown("""
<div class="footer-dark">
    <p><strong>Disclaimer:</strong> This tool does not replace professional help. If you are in crisis, contact emergency services or the KIRAN helpline (1800-599-0019).</p>
    <p>Premium Mental Health Support — Powered by Qwen 2.5 & Mistral 7B (via OpenRouter)</p>
</div>
""", unsafe_allow_html=True)
