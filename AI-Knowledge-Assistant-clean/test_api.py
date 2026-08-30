import requests

BASE_URL = "http://127.0.0.1:8000"

try:
    res = requests.post(
        f"{BASE_URL}/upload",
        files={"file": ("test.txt", b"Hello world. This is a test document containing useful information.")},
    )
    print("Upload Response:", res.status_code, res.text)
except Exception as e:
    print("Upload Error:", e)

try:
    res = requests.post(
        f"{BASE_URL}/ask",
        json={"query": "What is this document about?"},
    )
    print("Ask Response:", res.status_code, res.text)
except Exception as e:
    print("Ask Error:", e)
