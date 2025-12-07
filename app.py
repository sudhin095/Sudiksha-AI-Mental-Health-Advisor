import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import re
import json
import time

# =========================
# GEMINI API KEY (Secrets)
# =========================
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = None

if not GEMINI_API_KEY:
    st.error("⚠️ No GEMINI_API_KEY found. Add it to .streamlit/secrets.toml.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)

# =========================
#  PAGE CONFIG + CSS
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

# ====== MODEL NAMES (unchanged UI labels) ======
MODEL_NAMES = {
    "Gemini 2.5 Pro": "models/gemini-2.5-pro",
    "Gemini 2.5 Flash": "models/gemini-2.5-flash"
}
SIDEBAR_MODEL_KEYS = list(MODEL_NAMES.keys())

# ====== Initialize Session State ======
if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""

# -------------------------
# Safe generate wrapper - NO TIMEOUT PARAMETER
# -------------------------
def safe_generate(model_id, prompt, max_retries=3, backoff_base=2):
    """Generate content with proper retry logic (removed timeout param)."""
    attempt = 0
    while attempt <= max_retries:
        try:
            model = genai.GenerativeModel(model_id)
            response = model.generate_content(prompt)
            return response
        except Exception as e:
            msg = str(e).lower()
            attempt += 1
            
            # Rate limit: switch to flash
            if "429" in msg or "quota" in msg or "rate limit" in msg:
                if model_id == "models/gemini-2.5-flash":
                    if attempt < max_retries:
                        wait_time = (2 ** attempt) + (attempt * 0.5)
                        time.sleep(wait_time)
                        continue
                    return None
                
                st.warning("⚠️ Switching to Gemini 2.5 Flash due to rate limit.")
                model_id = "models/gemini-2.5-flash"
                time.sleep(1)
                continue
            
            # Transient errors: retry with backoff
            if "500" in msg or "503" in msg or "deadline" in msg.lower():
                if attempt < max_retries:
                    wait_time = (2 ** attempt)
                    time.sleep(wait_time)
                    continue
            
            # Other errors
            if attempt >= max_retries:
                st.error(f"API Error: {str(e)}")
                return None
            
            time.sleep(2 ** attempt)
    
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
    score = 0.0
    for kw, w in LEXICON_WEIGHTS.items():
        if kw in t:
            score += w
    if any(k in t for k in ["suicid", "kill myself", "i want to die", "end my life"]):
        score = max(score, 8.0)
    return int(round(min(1.0, score / 10.0) * 100))

# -------------------------
# Model intensity check
# -------------------------
def ask_model_for_intensity(user_text, model_id):
    """Get intensity score from model."""
    prompt = (
        "You are an evaluator that gives a concise numeric emotional intensity score.\n"
        "Reply with ONLY valid JSON: {\"intensity\": <0-100>, \"confidence\": <0.0-1.0>}.\n\n"
        f"Text: {user_text}\n"
    )
    time.sleep(0.5)
    resp = safe_generate(model_id, prompt, max_retries=2)
    if not resp:
        return None
    txt = resp.text.strip()
    match = re.search(r"\{[\s\S]*?\}", txt)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        intensity = int(max(0, min(100, int(data.get("intensity", 50)))))
        confidence = float(max(0.0, min(1.0, float(data.get("confidence", 0.5)))))
        return {"intensity": intensity, "confidence": confidence}
    except Exception:
        return None

# -------------------------
# Structured stress extraction
# -------------------------
def ask_model_for_structured_stress(user_text, model_id):
    """Get structured stress score from model."""
    prompt = (
        "Return ONLY a single JSON object with keys:\n"
        "score: integer 0-100\n"
        "evidence: array of brief verbatim phrases from the user's text\n"
        "confidence: float 0.0-1.0\n\n"
        f"User text:\n{user_text}\n\n"
        "Example: {\"score\":72, \"evidence\": [\"I can't sleep\"], \"confidence\":0.83}"
    )
    time.sleep(0.5)
    resp = safe_generate(model_id, prompt, max_retries=2)
    if not resp:
        return None
    txt = resp.text.strip()
    match = re.search(r'\{[\s\S]*\}', txt)
    if not match:
        cleaned = txt.replace("'", '"')
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if not match:
            return None
    json_text = match.group()
    try:
        data = json.loads(json_text)
    except Exception:
        repaired = re.sub(r'(\w+):', r'"\1":', json_text)
        try:
            data = json.loads(repaired)
        except Exception:
            return None
    score = int(max(0, min(100, int(data.get("score", 50)))))
    evidence = data.get("evidence", [])
    confidence = float(max(0.0, min(1.0, float(data.get("confidence", 0.5)))))
    return {"model_score": score, "evidence": evidence, "confidence": confidence}

# -------------------------
# Combined stress scoring
# -------------------------
def get_stress_level(user_text, model_id):
    """Calculate combined stress level."""
    lex = lexicon_score(user_text)
    structured = ask_model_for_structured_stress(user_text, model_id)
    reasoning = ask_model_for_intensity(user_text, model_id)

    model_score = None
    model_conf = 0.0
    reasoning_score = None
    reasoning_conf = 0.0

    if structured:
        model_score = structured["model_score"]
        model_conf = structured.get("confidence", 0.5)
    if reasoning:
        reasoning_score = reasoning["intensity"]
        reasoning_conf = reasoning.get("confidence", 0.5)

    w_model_base = 0.45
    w_lex_base = 0.30
    w_reason_base = 0.25

    model_conf_factor = model_conf if model_conf is not None else 0.0
    reason_conf_factor = reasoning_conf if reasoning_conf is not None else 0.0

    w_model = w_model_base * (0.5 + 0.5 * model_conf_factor)
    w_reason = w_reason_base * (0.5 + 0.5 * reason_conf_factor)
    w_lex = 1.0 - (w_model + w_reason)
    if w_lex < 0.1:
        w_lex = 0.1
        total = w_model + w_reason + w_lex
        w_model /= total
        w_reason /= total
        w_lex /= total

    if model_score is None:
        w_model = 0.0
        w_lex = 0.75
        w_reason = 0.25
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
# Context-aware support prompt
# -------------------------
def build_support_prompt(mode, text, stress_level):
    """Build unique, context-specific support prompt."""
    
    mode_guide = {
        "Crisis Detection": "Focus on immediate safety. Identify risk factors. Provide urgent resources.",
        "Emotional Support": "Validate their feelings. Provide practical, compassionate guidance.",
        "Risk Assessment": "Assess severity. Provide structured intervention plan.",
    }
    
    return f"""You are a compassionate mental health professional. 

ANALYSIS MODE: {mode}
STRESS LEVEL: {stress_level}%
{mode_guide.get(mode, "")}

USER'S SPECIFIC MESSAGE:
"{text}"

Based on THIS SPECIFIC person and THEIR EXACT WORDS, provide:

1. **Personalized Validation** - Reference exactly what they said
2. **3 Concrete Coping Actions** - Specific to their situation  
3. **24-Hour Action Plan** - Realistic next steps
4. **Script to Ask for Help** - One sentence they can use
5. **Warning Signs** - What to watch for specific to them

Use Markdown formatting. End with:
----------------------------------------
⚠ **Important Disclaimer**
This AI may be inaccurate. Seek professional help.
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
"If you're going through hell, keep going."<br>
"If there is something that means a lot to you, do not postpone it."
</div>
""", unsafe_allow_html=True)

# -------------------------
# SIDEBAR
# -------------------------
with st.sidebar:
    st.write("## Settings")
    chosen_model_name = st.selectbox("Choose AI Model", SIDEBAR_MODEL_KEYS, index=1)
    model_id = MODEL_NAMES[chosen_model_name]
    mode = st.radio("Analysis Mode", ["Crisis Detection", "Emotional Support", "Risk Assessment"])
    st.write("### Emergency Resources")
    st.info("**KIRAN:** 1800-599-0019\n**Vandrevala:** 1860-2662-345\n**iCall:** 9152987821")

# -------------------------
# MAIN UI
# -------------------------
col1, col2 = st.columns([2, 1])

with col1:
    tab1, tab2 = st.tabs(["✍️ Text", "🎤 Voice"])
    input_text = ""

    with tab1:
        st.markdown('<div class="info-card"><h3>Write your feelings</h3>', unsafe_allow_html=True)
        input_text = st.text_area("Describe your feelings.", height=160, key="text_input")
        st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="info-card"><h3>Speak your mind</h3>', unsafe_allow_html=True)
        audio_data = mic_recorder(start_prompt="🎤 Start Recording", stop_prompt="⏹ Stop")
        if audio_data:
            st.audio(audio_data["bytes"], format="audio/wav")
            st.success("Voice recorded!")
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🔍 Analyze & Get Support", use_container_width=True):
        # Get text from appropriate source
        final_text = input_text.strip() if input_text.strip() else st.session_state.voice_text.strip()
        
        if not final_text:
            st.error("❌ Please describe your feelings using text or microphone.")
        else:
            with st.spinner("Analyzing your emotional state..."):
                # Calculate stress level
                final_level, meta = get_stress_level(final_text, model_id)

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

                # Generate personalized support
                st.markdown("### Generating personalized support...")
                support_prompt = build_support_prompt(mode, final_text, final_level)
                time.sleep(1)
                response = safe_generate(model_id, support_prompt, max_retries=3)

                st.markdown('<div class="response-area">', unsafe_allow_html=True)
                if response and response.text:
                    st.markdown("### 💬 AI Support\n" + response.text)
                else:
                    # Extract key concern for fallback
                    concerns = []
                    if "sleep" in final_text.lower():
                        concerns.append("sleep issues")
                    if "overwhelm" in final_text.lower():
                        concerns.append("feeling overwhelmed")
                    if "alone" in final_text.lower():
                        concerns.append("isolation")
                    concern_str = concerns[0] if concerns else "your mental health"
                    
                    fallback_text = f"""
### 💬 AI Support (Offline Fallback)

**Your Situation:** You mentioned: "{final_text[:100]}..."

**What I hear:** This sounds important and distressing. Your feelings about {concern_str} are valid.

**Immediate steps:**
1. **Ground yourself** - 5-4-3-2-1 technique: Name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste
2. **Reach out** - Text/call someone you trust: "I'm not okay right now, can we talk?"
3. **Move your body** - 10-minute walk or stretch to shift your nervous system

**Next 24 hours:**
- Prioritize sleep (even 20-min power nap)
- Eat something nourishing
- Avoid major decisions

**Script to ask for help:**
"I've been struggling with {concern_str}. I could use your support. Can we talk?"

**When to escalate:**
- Thoughts of harming yourself
- Inability to function
- Overwhelming isolation

----------------------------------------
⚠ **Important Disclaimer**
This is not a substitute for professional help.
**Indian Mental Health Helpline:** 1800-599-0019
----------------------------------------
"""
                    st.markdown(fallback_text)
                st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="info-card"><h3>Why Mindful?</h3>- Modern<br>- Gemini 2.5 models<br>- 24/7 support</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-card"><h3>Modes</h3>- Crisis Detection<br>- Emotional Support<br>- Risk Assessment</div>', unsafe_allow_html=True)
    st.markdown('<div class="emergency-banner">🚨 IN CRISIS? CALL KIRAN 1800-599-0019 🚨</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("""
<div style="color: #fafafa; padding: 1rem 0; border-radius: 8px;">
<p><strong>Disclaimer:</strong> This tool does not replace professional help. If you are in crisis, contact emergency services or KIRAN (1800-599-0019).</p>
</div>
""", unsafe_allow_html=True)
