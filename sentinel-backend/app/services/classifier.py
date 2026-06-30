import os
import requests
import json

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

CLASSIFIER_PROMPT = """You are a distress signal classifier for Nepali migrant workers abroad. You read messages in Nepali, Romanized Nepali, or English from workers, their families, or community groups.

Classify the message into exactly one of three categories:
- SAFE: Normal conversation, no signs of distress
- DISTRESS: Concerning signs like unpaid wages, difficult conditions, homesickness, minor complaints
- CRISIS: Severe signs like passport confiscation, physical abuse, forced confinement, trafficking, threats, medical emergency, death

Respond ONLY with valid JSON in this exact format, nothing else:
{
    "classification": "SAFE" or "DISTRESS" or "CRISIS",
    "confidence": <number between 0 and 1>,
    "signals_detected": ["signal1", "signal2"],
    "recommended_action": "<short action recommendation>"
}

Examples:

Message: "Dai hamlai thik jagah maa liyena, passport liye ko chha, kaam dherai garauchha"
Response: {"classification": "CRISIS", "confidence": 0.94, "signals_detected": ["passport confiscation", "forced labor", "restricted movement"], "recommended_action": "Embassy alert - immediate welfare check"}

Message: "Yaha sabai thik cha, kaam ramro cha, paisa pani time maa aaucha"
Response: {"classification": "SAFE", "confidence": 0.91, "signals_detected": [], "recommended_action": "No action needed"}

Message: "Yo mahina tlab dina baki cha, manager le bhanya next week dinchu vanera"
Response: {"classification": "DISTRESS", "confidence": 0.78, "signals_detected": ["delayed wages"], "recommended_action": "Monitor - flag if unresolved in 2 weeks"}

Now classify this message:
"""

def classify_text(text: str) -> dict:
    if not NVIDIA_API_KEY:
        return {
            "classification": "ERROR",
            "confidence": 0,
            "signals_detected": [],
            "recommended_action": "NVIDIA_API_KEY not configured"
        }

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "messages": [
            {"role": "user", "content": CLASSIFIER_PROMPT + text}
        ],
        "temperature": 0.2,
        "max_tokens": 300
    }

    try:
        response = requests.post(NIM_URL, headers=headers, json=payload, timeout=30)
        result = response.json()
        
        raw_output = result["choices"][0]["message"]["content"].strip()
        
        # strip markdown code fences if model wraps response in ```json
        if raw_output.startswith("```"):
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:]
        
        parsed = json.loads(raw_output)
        return parsed

    except Exception as e:
        return {
            "classification": "ERROR",
            "confidence": 0,
            "signals_detected": [],
            "recommended_action": f"Classification failed: {str(e)}"
        }