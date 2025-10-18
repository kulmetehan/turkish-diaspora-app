"""
infra_audit.py – Quick quota & usage check for Turkish Diaspora App
Reads environment, queries OpenAI & Google API usage endpoints (if enabled).
"""
import os, requests

def check_openai():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {"openai": "missing key"}
    try:
        r = requests.get(
            "https://api.openai.com/v1/usage",
            headers={"Authorization": f"Bearer {key}"}, timeout=10)
        return {"openai_status": r.status_code, "ok": r.ok}
    except Exception as e:
        return {"openai_error": str(e)}

def check_google():
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        return {"google": "missing key"}
    # Google doesn't expose usage endpoint on free tier; just validate
    test_url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=Rotterdam&key={key}"
    r = requests.get(test_url, timeout=10)
    return {"google_status": r.status_code, "ok": r.ok}

if __name__ == "__main__":
    print(check_openai())
    print(check_google())
