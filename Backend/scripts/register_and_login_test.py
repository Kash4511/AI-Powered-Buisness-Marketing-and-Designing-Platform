import requests
import sys

BASE = "http://127.0.0.1:8000/api/auth"

def main():
    email = "test@example.com"
    payload = {
        "email": email,
        "name": "Test User",
        "phone_number": "1234567890",
        "password": "TestPass123!",
        "password_confirm": "TestPass123!",
    }
    try:
        r = requests.post(f"{BASE}/register/", json=payload, timeout=5)
        print("register", r.status_code, r.text)
    except Exception as e:
        print("register ERROR", str(e))
    try:
        r = requests.post(f"{BASE}/login/", json={"email": email.upper(), "password": "TestPass123!"}, timeout=5)
        print("login", r.status_code, r.text)
    except Exception as e:
        print("login ERROR", str(e))

if __name__ == "__main__":
    main()
