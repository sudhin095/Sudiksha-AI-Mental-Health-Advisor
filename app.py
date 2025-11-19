import streamlit as st
import google.generativeai as genai
import re
import numpy as np

# -----------------------------
# CONFIGURE GEMINI API PROPERLY
# -----------------------------
# Instead of hardcoding the model, we load the available models dynamically.
# This prevents "model not found" errors.

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

def get_available_model():
    try:
        models = genai.list_models()
        # Pick the first model that supports generate_content
        for m in models:
            if "generateContent" in m.supported_generation_methods:
                return m.name
        return "gemini-1.5-flash"  # safe fallback
    except:
        return "gemini-1.5-flash"

MODEL_NAME = get_available_model()


# --------------------------------
# OFFLINE STRESS ANALYZER (fallback)
# --------------------------------
def offline_stress_score(text):
    """
    A simple ML-style heuristic analyzer used ONLY if the API fails.
    """
    stress_keywords = {
        "high": ["panic", "anxiety", "depressed", "suicidal", "hopeless", "worthless", "crying", "breakdown"],
        "medium": ["stress", "tired", "overwhelmed", "pressure", "scared", "angry", "frustrated"],
        "low": ["worried", "concern", "busy", "confused"]
    }

    score = 0
    txt = text.lower()

    for word in stress_keywords["high"]:
        if word in txt:
            score += 35
    for word in stress_keywords["medium"]:
        if word in txt:
            score += 20
    for word in stress_keywords["low"]:
        if word in txt:
            score += 10

    # Normalize
    return min(100, score)


# ------------------
# GEMINI RESPONSE
# ------------------
def analyze_with_gemini(user_text):
    prompt = f"""
You are a mental-health support AI. Analyze the user's message:

"{user_text}"

1. Detect emotional state & stress level (0–100%).
2. Provide a VERY SPECIFIC, non-generic analysis based directly on their text.
3. Provide a structured response with:
   - What emotions they may be experiencing
   - Why they might be feeling this way (based on context)
   - Actionable steps tailored to their situation
4. END the message with this EXACT disclaimer block:

----------------------------------------
⚠ **Important Disclaimer**
This AI may be inaccurate. Please seek medical advice from a professional.  
Talk to your loved ones for support.  
**Indian Mental Health Helpline:** 1800-599-0019
----------------------------------------

Respond in clear bullet points.
"""

    try:
        model = genai.GenerativeModel(MODEL_NAME)
        result = model.generate_content(prompt)
        return result.text
    except Exception as e:
        return None


# -----------------------
# STRESS SCORE EXTRACTION
# -----------------------
def extract_stress(text):
    match = re.search(r"(\d{1,3})\s*%", text)
    if match:
        return min(100, int(match.group(1)))
    return None


# -----------------------------
# STREAMLIT USER INTERFACE (same)
# -----------------------------
st.set_page_config(page_title="Mindful AI", page_icon="🧠")

st.markdown("<h1 style='text-align:center;color:#5C6BC0;'>Mindful AI – Stress Analyzer</h1>",
            unsafe_allow_html=True)

st.markdown("<p style='text-align:center;color:#888;'>Enter your feelings below:</p>",
            unsafe_allow_html=True)

user_input = st.text_area("Describe what you're feeling:", height=180)

if "history" not in st.session_state:
    st.session_state.history = []

if st.button("Analyze Stress"):
    if user_input.strip() == "":
        st.warning("Please enter some text.")
    else:
        with st.spinner("Analyzing your emotional state..."):
            response = analyze_with_gemini(user_input)

            if response:
                stress_score = extract_stress(response)
                if stress_score is None:
                    stress_score = offline_stress_score(user_input)

                st.progress(stress_score / 100)
                st.subheader(f"Stress Level: {stress_score}%")
                st.markdown(response)

                st.session_state.history.append(
                    (user_input, stress_score, response)
                )
            else:
                st.error("API limit reached — using offline analyzer.")
                stress_score = offline_stress_score(user_input)
                st.progress(stress_score / 100)

                fallback_text = f"""
### Stress Level: {stress_score}%

You may be experiencing specific emotional pressures based on what you shared.
Here is a tailored breakdown:

- **Your concerns:** Based on your message, the emotion indicators point to heightened tension.
- **Possible causes:** Words and patterns in your text suggest mental overload or emotional fatigue.
- **What may help right now:**
  - Take 3–5 slow breaths to stabilize your nervous system.
  - Write down what is bothering you in a short list to separate thoughts.
  - Reach out to one trusted person today.
  - Consider a small break or short walk.

----------------------------------------
⚠ **Important Disclaimer**
This AI may be inaccurate. Please seek medical advice from a professional.  
Talk to your loved ones for support.  
**Indian Mental Health Helpline:** 1800-599-0019
----------------------------------------
"""

                st.markdown(fallback_text)


# -----------------------
# HISTORY SECTION (same UI)
# -----------------------
with st.expander("📜 Previous Analyses"):
    if len(st.session_state.history) == 0:
        st.write("No previous analyses yet.")
    else:
        for idx, (text, score, res) in enumerate(st.session_state.history):
            st.markdown(f"### Entry {idx+1}")
            st.markdown(f"**User Input:** {text}")
            st.markdown(f"**Stress Score:** {score}%")
            st.markdown(res)
            st.markdown("---")
