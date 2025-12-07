import streamlit as st
from streamlit_mic_recorder import mic_recorder
import google.generativeai as genai
import re
import json
import time
import os

# =========================
# GEMINI API KEY - Robust Loading
# =========================
def get_api_key():
    """Get API key from secrets or environment."""
    try:
        key = st.secrets.get("GEMINI_API_KEY", "").strip()
        if key and key != "":
            return key
    except:
        pass
    
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key and key != "":
        return key
    
    return None

GEMINI_API_KEY = get_api_key()

if not GEMINI_API_KEY:
    st.error("""
    ⚠️ API Key not found!
    
    **For Local Development:**
    Create `.streamlit/secrets.toml` with:
    ```
    GEMINI_API_KEY = "your-api-key-here"
    ```
    
    **For Streamlit Cloud:**
    Settings → Secrets → Add GEMINI_API_KEY
    """)
    st.stop()

try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"⚠️ Failed to configure API: {str(e)}")
    st.stop()

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

# ====== MODEL NAMES ======
MODEL_NAMES = {
    "Gemini 2.5 Pro": "models/gemini-2.5-pro",
    "Gemini 2.5 Flash": "models/gemini-2.5-flash"
}
SIDEBAR_MODEL_KEYS = list(MODEL_NAMES.keys())

# ====== Initialize Session State ======
if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""

# -------------------------
# Safe generate wrapper with DETAILED LOGGING
# -------------------------
def safe_generate(model_id, prompt, max_retries=3, backoff_base=2):
    """Generate content with proper retry logic and detailed error reporting."""
    attempt = 0
    last_error = None
    
    while attempt <= max_retries:
        try:
            st.write(f"🔄 API Call Attempt {attempt + 1} with {model_id}...")
            model = genai.GenerativeModel(model_id)
            response = model.generate_content(prompt)
            
            if response and response.text:
                st.success(f"✅ API Success on attempt {attempt + 1}")
                return response
            else:
                st.warning(f"⚠️ Empty response from API")
                return None
                
        except Exception as e:
            last_error = e
            msg = str(e).lower()
            
            # API key invalid
            if "invalid" in msg or "expired" in msg or "unauthorized" in msg or "api_key_invalid" in msg:
                st.error(f"❌ API Key Error: {str(e)}")
                st.error("Check your GEMINI_API_KEY in .streamlit/secrets.toml")
                return None
            
            # Rate limit: switch to flash
            if "429" in msg or "quota" in msg or "rate limit" in msg:
                if model_id == "models/gemini-2.5-flash":
                    if attempt < max_retries:
                        wait = 2 ** (attempt + 1)
                        st.warning(f"⚠️ Flash rate limited. Waiting {wait}s before retry...")
                        time.sleep(wait)
                        attempt += 1
                        continue
                    return None
                
                st.warning("⚠️ Pro quota reached. Switching to Flash...")
                model_id = "models/gemini-2.5-flash"
                time.sleep(1)
                continue
            
            # Transient errors: retry
            if "500" in msg or "503" in msg or "deadline" in msg or "timeout" in msg:
                if attempt < max_retries:
                    wait = 2 ** attempt
                    st.warning(f"⚠️ Temporary error. Retrying in {wait}s...")
                    time.sleep(wait)
                    attempt += 1
                    continue
            
            # Other errors
            attempt += 1
            if attempt <= max_retries:
                time.sleep(2 ** attempt)
                continue
            else:
                st.error(f"❌ API failed after {max_retries} retries: {str(e)}")
                return None
    
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
    time.sleep(0.3)
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
    except Exception as ex:
        st.warning(f"JSON parse error in intensity: {str(ex)}")
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
    time.sleep(0.3)
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
        except Exception as ex:
            st.warning(f"JSON parse error in structured: {str(ex)}")
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
    
    st.write("📊 Calculating stress level...")
    structured = ask_model_for_structured_stress(user_text, model_id)
    reasoning = ask_model_for_intensity(user_text, model_id)

    model_score = None
    model_conf = 0.0
    reasoning_score = None
    reasoning_conf = 0.0

    if structured:
        model_score = structured["model_score"]
        model_conf = structured.get("confidence", 0.5)
        st.write(f"✓ Model score: {model_score}")
    if reasoning:
        reasoning_score = reasoning["intensity"]
        reasoning_conf = reasoning.get("confidence", 0.5)
        st.write(f"✓ Reasoning score: {reasoning_score}")

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

    st.write(f"✓ Lexicon score: {lex}, Final: {final}")

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
# Context-aware support prompt with stress level
# -------------------------
def build_support_prompt(mode, text, stress_level):
    """Build unique, context-specific support prompt with stress level."""
    
    mode_guide = {
        "Crisis Detection": "Focus on immediate safety. Identify risk factors. Provide urgent resources.",
        "Emotional Support": "Validate their feelings. Provide practical, compassionate guidance.",
        "Risk Assessment": "Assess severity. Provide structured intervention plan.",
    }
    
    return f"""You are a compassionate mental health professional responding to someone with a {stress_level}% stress level.

ANALYSIS MODE: {mode}
STRESS LEVEL DETECTED: {stress_level}%
CONTEXT: {mode_guide.get(mode, "")}

IMPORTANT: Every response MUST be unique and tailored to these EXACT words from the person:
"{text}"

Generate a personalized response that:
1. References their SPECIFIC situation (not generic advice)
2. Validates their EXACT words and emotions
3. Provides 3 concrete coping actions tailored to THEIR problem
4. Includes a 24-hour action plan specific to them
5. Gives a one-sentence script they can use to ask for help
6. Lists warning signs specific to what they mentioned

Use Markdown. IMPORTANT: DO NOT provide a generic response. Everything must reference their specific situation and words.

End with:
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

                # Generate personalized support with stress level
                st.markdown("### Generating personalized support...")
                support_prompt = build_support_prompt(mode, final_text, final_level)
                time.sleep(1)
                response = safe_generate(model_id, support_prompt, max_retries=3)

                st.markdown('<div class="response-area">', unsafe_allow_html=True)
                if response and response.text and len(response.text) > 100:
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
                    if "panic" in final_text.lower():
                        concerns.append("panic attacks")
                    if "anxious" in final_text.lower():
                        concerns.append("anxiety")
                    
                    concern_str = concerns[0] if concerns else "your emotional wellbeing"
                    
                    fallback_text = f"""
### 💬 AI Support (Offline Mode)

**Your Situation:** You shared: "{final_text[:100]}..."

**Stress Level:** {final_level}% - {get_stress_desc(final_level)}

**I hear you:** Your struggle with {concern_str} is real and valid. Here's personalized support:

**Immediate Coping Actions (for your situation):**
1. **For {concern_str}** - Start with 5-4-3-2-1 grounding: Name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste
2. **Reach out immediately** - Call/text someone safe: "I'm struggling with {concern_str}. Can we talk?"
3. **Physical shift** - 10-min walk, cold water on face, or stretching to change your nervous system

**Your 24-Hour Plan:**
- **Now:** One grounding technique above
- **Next 2 hours:** Reach out to 1 person
- **Tonight:** Sleep focus, avoid decisions, limit caffeine

**Script to Ask for Help:**
"I've been dealing with {concern_str} and I'm not handling it well. I need your support."

**Warning Signs (Watch for these):**
- Thoughts of harming yourself → Call KIRAN immediately
- Inability to function → Reach out to professional
- Complete isolation → Force connection with someone

----------------------------------------
⚠ **Important Disclaimer**
This is not professional help. Seek real mental health support.
**Indian Mental Health Helpline:** 1800-599-0019
**Crisis Chat:** https://www.aasra.info/
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
<p><strong>Disclaimer:</strong> This tool does not replace professional help. If you are in crisis, contact KIRAN (1800-599-0019).</p>
</div>
""", unsafe_allow_html=True)
