# check_models.py

import os
import google.generativeai as genai

# 1. Read your API key (or replace with a string temporarily)
API_KEY = os.environ.get("GOOGLE_API_KEY")  # or: API_KEY = "YOUR_KEY_HERE"

if not API_KEY:
    raise RuntimeError("Set GOOGLE_API_KEY environment variable or hardcode API_KEY in this file.")

# 2. Configure the client
genai.configure(api_key=API_KEY)

def list_models():
    print("\nModels that support generateContent:\n")
    for m in genai.list_models():
        # Some models only support embeddings etc., so filter for generateContent
        if "generateContent" in getattr(m, "supported_generation_methods", []):
            print("-", m.name)

if __name__ == "__main__":
    list_models()
