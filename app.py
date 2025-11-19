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
except Exception:
    WHISPER_AVAILABLE = False

# Page config
st.set_page_config(page_title="Mindful — Mental Health Support", page_icon="🧠", layout="centered")

# --- Premium CSS (compact & modern card style) ---
st.markdown(
    """
    <style>
    :root {
        --accent1: #667eea;
        --accent2: #764ba2;
        --muted: #6b7280;
    }
    body { background: linear-gradient(180deg,#eef2ff 0%, #ffffff 60%); }
    .card {
        background: white;
        padding: 28px;
        border-radius: 14px;
        box-shadow: 0 8px 24px rgba(30,41,59,0.06);
        max-width:900px;
        margin: 18px auto;
        border: 1px solid rgba(99,102,241,0.06);
    }
    .title {
        font-size:30px;
        font-weight:800;
        background: linear-gradient(90deg,var(--accent1),var(--accent2));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    .subtitle { color:var(--muted); margin-bottom: 18px; }
    .response { background: #fff; padding:18px; border-radius:10px; border-left:6px solid var(--accent1); margin-top:16px; }
    .disclaimer {
        background:#fff8e6; border-left:6px solid #ffb84d; padding:12px; border-radius:8px; margin-top:18px;
        font-weight:600; color:#7a2b00;
    }
    .emergency {
        background: linear-gradient(90deg,#f093fb,#f5576c); color:white; padding:12px; border-radius:10px; text-align:center; margin-top:10px;
        font-weight:700;
    }
    .small { font-size:13px; color:var(--muted); }
    </style>
    """, unsafe_allow_html=True
)

# --- Helpers and Model Loading ---
@st.cache_resource
def load_emotion_model():
    # This uses a small emotion model that is free on HF hubs.
    # The first run will download weights.
    return pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

emotion_model = load_emotion_model()

def compute_stress_score(model_scores):
    """
    model_scores: list of dicts [{'label':..., 'score':...}, ...]
    We treat anger, fear, sadness as stress indicators.
    Return integer 0-100.
    """
    prob = {item['label'].lower(): item['score'] for item in model_scores}
    # sum relevant emotions; clamp and scale
    stress_raw = prob.get('anger', 0.0) + prob.get('fear', 0.0) + prob.get('sadness', 0.0)
    # Some models include 'stress' or 'neg' labels — include if present
    stress_raw += prob.get('stress', 0.0)
    # convert to percentage (cap at 1.0)
    pct = min(1.0, stress_raw)
    return int(round(pct * 100))

def extract_signals(text):
    """
    Return keywords, possible stressors, sleep/eating/self-harm hints.
    """
    txt = text.lower()
    # simple keyword lists (expand as desired)
    feelings = ["anxious","anxiety","depressed","depression","sad","hopeless","overwhelmed","stressed","stress","panic","panic attack","angry","lonely","isolated","hurt","frustrat","burnout","tired","exhausted","suicid","worthless"]
    triggers = ["work","job","exam","relationship","money","family","health","loss","breakup","school","boss","study","deadline"]
    actions = []
    for w in feelings:
        if w in txt:
            actions.append(w)
    triggers_found = [t for t in triggers if t in txt]
    # detect first-person intent words that can be serious
    serious = []
    if re.search(r"\bkill myself\b|\bi want to die\b|\bi can\'t go on\b|\bi\'m going to end\b", txt):
        serious.append("suicidal_ideation")
    # sleep/eating
    if re.search(r"\bsleep(ing|s)?\b|\binsomnia\b", txt): serious.append("sleep_issue")
    if re.search(r"\beat(ing|s)?\b|\bappetite\b", txt): serious.append("appetite_change")
    return {
        "feelings": sorted(set(actions)),
        "triggers": triggers_found,
        "serious": serious
    }

def make_personalized_response(text, score, signals):
    """
    Create an organized, bullet-point response tied to user text.
    """
    # short excerpt
    excerpt = textwrap.shorten(text.replace("\n"," "), width=140, placeholder="...")
    # determine level
    if score < 35:
        level = "LOW — mild or transient stress"
    elif score < 65:
        level = "MODERATE — notable emotional strain"
    else:
        level = "HIGH — elevated stress or distress"
    # build sections (Markdown)
    sections = []
    sections.append(f"**Stress assessment:** {level} — estimated **{score}%** stress based on language patterns.")
    sections.append("**What I hear from you:**")
    sections.append(f"- \"{excerpt}\"")
    # key emotional elements
    if signals["feelings"]:
        sections.append("**Emotional elements detected:**")
        sections.append("```\n- " + "\n- ".join(signals["feelings"]) + "\n```")
    else:
        sections.append("- No strong single-feeling word detected; emotional nuance observed.")
    if signals["triggers"]:
        sections.append("**Possible situational triggers mentioned:**")
        sections.append("- " + ", ".join(signals["triggers"]))
    # immediate tailored coping suggestions
    suggestions = []
    # breathing if anxiety words found
    if any(w in text.lower() for w in ["anxious","anxiety","panic","panic attack"]):
        suggestions.append("- Try *box breathing* (4 sec inhale — hold 4 — 4 sec exhale — hold 4) for 3–5 cycles to reduce acute panic.")
    # sleep/exhaustion
    if "sleep_issue" in signals["serious"] or "tired" in signals["feelings"] or "exhausted" in text.lower():
        suggestions.append("- If sleep is disturbed, try a short wind-down: dim lights, no screens 30 min before bed, and a 10-minute relaxation exercise.")
    # general grounding
    suggestions.append("- Use grounding: name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste.")
    suggestions.append("- Break the immediate problem into smaller steps and pick one tiny action you can do right now (even 5 minutes counts).")
    # social support
    suggestions.append("- If comfortable, tell one person you trust one clear sentence about how you're feeling (e.g., \"I’ve been feeling overwhelmed lately and could use to talk\").")
    # professional help if high
    if score >= 65 or "suicidal_ideation" in signals["serious"]:
        suggestions.append("- Consider contacting a trained professional or crisis service. If you feel unsafe, call emergency services or the helpline below immediately.")
    # pack sections
    sections.append("**Personalized coping suggestions (choose 2–3 to try now):**")
    sections.append("\n".join(suggestions))
    sections.append("**What to watch over the next 48–72 hours:**")
    watch = ["Mood stays the same or worsens", "Sleep becomes much worse", "Thoughts about harming yourself or not wanting to be here"]
    sections.append("- " + "\n- ".join(watch))
    # follow-up
    sections.append("**If you decide to seek help:**")
    sections.append("- When possible, bring examples of recent thoughts, sleep patterns, and any triggers you noticed — this helps clinicians quickly understand your situation.")
    # join with spacing and return markdown
    return "\n\n".join(sections)

def transcribe_with_whisper(file_bytes):
    """Transcribes audio bytes using local whisper (if installed). Returns text or raises."""
    model = whisper.load_model("small")
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        f.write(file_bytes)
        tmp = f.name
    try:
        res = model.transcribe(tmp)
        return res.get("text", "").strip()
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass

# --- App layout ---
st.markdown('<div class="card">', unsafe_allow_html=True)
st.markdown('<div class="title">Mindful — Mental Health Support</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle small">Confidential, compassionate AI to help you understand stress and find next steps.</div>', unsafe_allow_html=True)

# Input region
tab1, tab2 = st.tabs(["✍️ Text", "🎙️ Audio (Upload)"])

user_input_text = ""
with tab1:
    user_input_text = st.text_area("Share what you're feeling (write as much or as little as you like):", height=200, placeholder="I feel overwhelmed at work...")

with tab2:
    st.info("Upload a short recording (wav / mp3 / m4a). Whisper transcription is optional and must be installed on the server.")
    uploaded_file = st.file_uploader("Upload audio file", type=["wav","mp3","m4a","ogg"])
    if uploaded_file is not None:
        st.audio(uploaded_file)
        if WHISPER_AVAILABLE:
            if st.button("Transcribe audio"):
                with st.spinner("Transcribing audio..."):
                    try:
                        file_bytes = uploaded_file.read()
                        text_out = transcribe_with_whisper(file_bytes)
                        st.success("Transcription complete — pasted into text box for review.")
                        # fill text area in tab1 by setting variable and instructing user
                        user_input_text = st.text_area("Transcribed text (edit if needed):", value=text_out, height=180)
                    except Exception as e:
                        st.error(f"Transcription failed: {e}")
        else:
            st.warning("Whisper is not installed on this server. Please transcribe locally and paste into the Text tab.")

# Analyze button
col1, col2 = st.columns([3,1])
with col1:
    analyze = st.button("🔍 Analyze & Get Support", use_container_width=True)
with col2:
    st.markdown("<div class='emergency'>If in crisis: call KIRAN helpline 1800-599-0019</div>", unsafe_allow_html=True)

if analyze:
    # ensure there is text
    final_text = user_input_text.strip() if user_input_text else ""
    if not final_text:
        st.warning("Please enter some text or transcribe audio first so the AI can analyze your message.")
    else:
        with st.spinner("Analyzing for stress markers and tailored guidance..."):
            # model inference
            try:
                raw = emotion_model(final_text)[0]  # list of label/score dicts
            except Exception as e:
                st.error("Error running the emotion model: " + str(e))
                raw = []
            # compute score
            score = compute_stress_score(raw) if raw else 0
            signals = extract_signals(final_text)
            response_md = make_personalized_response(final_text, score, signals)

            # show results
            st.markdown('<div class="response">', unsafe_allow_html=True)
            st.markdown(f"### 🧾 Stress Level — **{score}%**")
            st.progress(score)
            st.markdown(response_md)
            st.markdown('</div>', unsafe_allow_html=True)

            # Save history entry
            if "history" not in st.session_state:
                st.session_state.history = []
            st.session_state.history.insert(0, {"text": final_text[:300], "score": score})

            # Downloadable brief report
            report = f"Mindful — Stress Report\n\nInput excerpt: {final_text[:300]}\nStress score: {score}%\n\nRecommendations:\n{response_md}\n\nHelpline: 1800-599-0019\n(Automated support — not a medical diagnosis.)"
            st.download_button("Download brief report (txt)", report, file_name="mindful_report.txt")

# History (limited)
if "history" in st.session_state and st.session_state.history:
    st.markdown("<hr />", unsafe_allow_html=True)
    st.markdown("#### Recent analyses")
    for i, h in enumerate(st.session_state.history[:5]):
        st.markdown(f"- **{h['score']}%** — {h['text']}")

# Always show highlighted disclaimer & helpline at bottom of card
st.markdown(
    """
    <div class="disclaimer">
    ⚠️ This tool provides supportive guidance and is NOT a replacement for professional medical care. 
    Please consider seeking medical advice for diagnosis and treatment. 
    Talk to your loved ones — sharing how you feel can help. 
    If you are in immediate crisis or feel unsafe, call the 24/7 helpline: <strong>1800-599-0019</strong>.
    </div>
    """, unsafe_allow_html=True
)

st.markdown('</div>', unsafe_allow_html=True)
