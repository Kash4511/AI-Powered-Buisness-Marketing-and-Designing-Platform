import os
import sys
import json
import requests

BASE = "http://127.0.0.1:8000/api/auth"

def post(url, payload):
    r = requests.post(url, json=payload, timeout=5)
    return r.status_code, r.text

def main():
    email = "edge@example.com"
    good_pw = "StrongP@ssw0rd!"
    bad_pw = "wrongpass"

    status, text = post(f"{BASE}/register/", {
        "email": email.upper(),
        "name": "",
        "phone_number": "",
        "password": good_pw,
        "password_confirm": good_pw,
    })
    print("register-mixedcase", status, text)

    status, text = post(f"{BASE}/login/", {"email": email, "password": good_pw})
    print("login-before-create", status, text)

    status, text = post(f"{BASE}/login/", {"email": email.upper(), "password": good_pw})
    print("login-mixedcase", status, text)

    status, text = post(f"{BASE}/login/", {"email": email, "password": bad_pw})
    print("login-wrongpw", status, text)

    status, text = post(f"{BASE}/register/", {
        "email": email,
        "name": "Dup",
        "phone_number": "",
        "password": good_pw,
        "password_confirm": good_pw,
    })
    print("register-create", status, text)

    status, text = post(f"{BASE}/login/", {"email": email, "password": good_pw})
    print("login-good", status, text)

if __name__ == "__main__":
    main()
