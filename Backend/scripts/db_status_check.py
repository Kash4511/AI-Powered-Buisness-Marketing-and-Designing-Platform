import requests
import sys

def main():
    url = "http://127.0.0.1:8000/api/db-status"
    try:
        r = requests.get(url, timeout=5)
        print(r.status_code)
        print(r.text)
    except Exception as e:
        print("ERROR", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
