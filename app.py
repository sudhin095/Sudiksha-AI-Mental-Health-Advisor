import streamlit as st
import json
import requests

st.set_page_config(page_title="AI Mental Health Advisor", layout="wide")

# ======================
# FREE BROWSER SPEECH-TO-TEXT (Web Speech API)
# ======================
st.markdown("""
<style>
.stt-btn {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 12px 20px;
    border-radius: 8px;
    font-size: 18px;
    cursor: pointer;
}
</style>

<script>
let recognition;

function startRecording() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert("Your browser does not support speech recognition. Please use Chrome.");
        return;
    }

    recognition = new(window.SpeechRecognition || window.webkitSpeechRecognition)();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = function(event) {
        const text = event.results[0][0].transcript;
        window.parent.postMessage({ type: 'stt_text', text: text }, "*");
    };

    recognition.onerror = function(event) {
        window.parent.postMessage({ type: 'stt_text', text: "" }, "*");
    };

    recognition.start();
}
</script>

<button class="stt-btn" onclick="startRecording()">🎙️ Speak Your Mind</button>
""", unsafe_allow_html=True)

# Capture messages from browser → Streamlit
st.markdown("""
<script>
window.addEventListener("message", (event) => {
    if (event.data.type === "stt_text") {
        const text = event.data.text;
        const query = new URLSearchParams(window.location.search);
        query.set("voice_input", text);
        window.location.search = query.toString();
    }
});
</script>
""", unsafe_allow_html=True)

# Get transcription result from URL
voice_input = st.experimental_get_query_params().get("voice_input", [""])[0]

st.title("🧠 AI Mental Health Advisor")

# User text area
user_text = st.text_area(
    "Type your message or use the Microphone above:",
    value=voice_input,
    height=150
)

# ======================
# AI MODEL SELECTION
# ======================
st.subheader("Choose AI Model (OpenRouter – Free Options Available)")

model_choice = st.selectbox(
    "Select a Model:",
    [
        "Qwen2.5-72B (High Accuracy – Free)",
        "Mistral-7B-Instruct (Fast – Backup Model)"
    ]
)

# Load OpenRouter API Key
OPENROUTER_KEY = st.secrets.get("OPENROUTER_API_KEY", None)

if not OPENROUTER_KEY:
    st.error("⚠️ OpenRouter API key missing! Add it in Streamlit → Settings → Secrets.")
else:
    st.success("✅ OpenRouter API Ready")

# ======================
# AI CALL FUNCTION
# ======================
def analyze_stress(text):
    if model_choice == "Qwen2.5-72B (High Accuracy – Free)":
        model = "qwen/qwen2.5-72b-instruct"
    else:
        model = "mistralai/mistral-7b-instruct"

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENROUTER_KEY}"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an AI mental health advisor. Analyze stress level between 0–100%. Provide short, empathetic feedback."
            },
            {
                "role": "user",
                "content": text
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    try:
        result = response.json()
        ai_text = result["choices"][0]["message"]["content"]
    except:
        ai_text = "⚠️ Error: Could not get a proper response from the AI."

    return ai_text


# ======================
# Submit Button
# ======================
if st.button("Analyze My Stress"):
    if user_text.strip() == "":
        st.warning("Please type something or speak using the microphone.")
    else:
        with st.spinner("Analyzing your mental state..."):
            result = analyze_stress(user_text)

        st.subheader("🧠 Stress Analysis Result")
        st.write(result)
