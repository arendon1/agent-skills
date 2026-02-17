import os
import sys
import json
import requests
from pathlib import Path

def get_api_key():
    # Structure: skills/.env <- skills/stitch-ui-generator/scripts/stitch_client.py
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return None
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("GOOGLE_STITCH_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None

def call_stitch(prompt, tech_stack="jquery"):
    api_key = get_api_key()
    if not api_key:
        print("ERROR: API Key missing.")
        sys.exit(1)

    # Note: As of early 2026, Google Stitch is often accessed via the Gemini API 
    # with a specific system instruction or via a dedicated preview endpoint.
    # This client uses the Generative Language API which powers Stitch behaviors.
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    # Enrich the prompt with Stitch-like UI generation directives
    system_instruction = (
        "You are the Google Stitch UI Agent. Your goal is to generate high-fidelity, production-ready "
        f"frontend code using {tech_stack}. Follow the user's layout plan exactly. "
        "Provide ONLY the code blocks. No explanations outside the code."
    )
    
    payload = {
        "contents": [{
            "parts": [{"text": f"{system_instruction}\n\nUser Request: {prompt}"}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.8,
            "maxOutputTokens": 8192,
        }
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Extract text from Gemini response
        code = data['candidates'][0]['content']['parts'][0]['text']
        print(code)
    except Exception as e:
        print(f"ERROR: API Call failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stitch_client.py '<prompt>' '<tech_stack>'")
        sys.exit(1)
    
    prompt_arg = sys.argv[1]
    stack_arg = sys.argv[2] if len(sys.argv) > 2 else "jquery"
    call_stitch(prompt_arg, stack_arg)
