import os
from groq import Groq

def check_groq():
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not found")
        return
    
    client = Groq(api_key=api_key)
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "ping",
                }
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=10
        )
        print("Success!")
        print(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"Error type: {type(e)}")
        print(f"Error str: '{str(e)}'")
        if hasattr(e, 'status_code'):
            print(f"Status code: {e.status_code}")

if __name__ == "__main__":
    check_groq()
