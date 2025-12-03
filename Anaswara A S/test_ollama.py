import requests

url = "http://localhost:11434/api/generate"
data = {
    "model": "llama3.1:8b",
    "prompt": "What is the capital of France?",
    "stream": False
}

try:
    r = requests.post(url, json=data, timeout=120)
    print("STATUS:", r.status_code)
    print("BODY:", r.text)
except Exception as e:
    print("ERROR:", e)



