import os, requests

k = os.getenv("GOOGLE_TRANSLATE_API_KEY")
u = f"https://translation.googleapis.com/language/translate/v2?key={k}"
r = requests.post(u, json={"q": "hello world", "target": "ko"}, timeout=20)
print("status", r.status_code)
print(r.text[:200])
