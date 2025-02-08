import os
import time
import pyautogui
import webbrowser
from dotenv import load_dotenv
from groclake.vectorlake import VectorLake
from groclake.modellake import ModelLake

load_dotenv()
API_KEY = os.getenv("TWITTER_API_KEY")
API_SECRET = os.getenv("TWITTER_API_SECRET")
ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")
os.environ['GROCLAKE_API_KEY'] = "140f6969d5213fd0ece03148e62e461e"
os.environ['GROCLAKE_ACCOUNT_ID'] = "72aea028970a23b6530c7faa987905e0"

vectorlake = VectorLake()
modellake = ModelLake()

SYSTEM_PROMPT = """Generate a professional tweet with the following requirements:
    - Keep it concise and engaging
    - Maintain a professional yet approachable tone
"""

def open_twitter():
    print("🔄 Opening Twitter...")
    webbrowser.open("https://twitter.com/compose/tweet", new=1)
    time.sleep(3)

def post_tweet():
    tweet_text = input("Enter your tweet: ")
    chat_completion_request = {
        "groc_account_id": "c4ca4238a0b923820dcc509a6f75849b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Post this tweet: {tweet_text}"}
        ]
    }
    
    response = modellake.chat_complete(chat_completion_request)
    tweet_content = response['answer'].strip()
    print("✅ Tweet generated:", tweet_content)
    
    open_twitter()
    
    # Simulate typing the tweet in the browser
    time.sleep(2)
    pyautogui.write(tweet_content, interval=0.05)
    time.sleep(1)
    pyautogui.hotkey('ctrl', 'enter')
    print("✅ Tweet posted successfully!")

def main():
    while True:
        print("\nTwitter Actions:")
        print("1. Post a tweet")
        print("2. Exit")
        
        choice = input("Choose (1-2): ")
        
        if choice == "1":
            post_tweet()
        elif choice == "2":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice.")

if __name__ == "__main__":
    main()
