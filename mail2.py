import os
import base64
import time
import pyautogui
import keyboard
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
from groclake.vectorlake import VectorLake
from groclake.modellake import ModelLake

load_dotenv()
os.environ['GROCLAKE_API_KEY'] = "140f6969d5213fd0ece03148e62e461e"
os.environ['GROCLAKE_ACCOUNT_ID'] = "72aea028970a23b6530c7faa987905e0"

vectorlake = VectorLake()
modellake = ModelLake()

SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

SYSTEM_PROMPT = """Write a professional email with the following requirements:
    - Topic: 
    - Start with 'Dear'
    - End with 'Best regards,\n'
    - Make it professional and concise"""

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

def generate_email_content(user_input, recipient_name, sender_name):
    chat_completion_request = {
        "groc_account_id": "c4ca4238a0b923820dcc509a6f75849b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Write an email to {recipient_name} about {user_input}."}
        ]
    }
    
    response = modellake.chat_complete(chat_completion_request)
    return response['answer'].strip()

def create_message(sender, sender_name, to, subject, message_text):
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = f"{sender_name} <{sender}>"
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message, 'to': to, 'subject': subject, 'message': message_text}

def send_email(service, message):
    try:
        import webbrowser
        from urllib.parse import quote
        
        to_email = message['to']
        subject = message['subject']
        body = message['message']
        
        mailto_url = f"mailto:{to_email}"
        webbrowser.open(mailto_url, new=1)
        
        time.sleep(2)
        pyautogui.write(subject)
        pyautogui.press('tab')
        time.sleep(0.2)
        pyautogui.press('tab')
        time.sleep(0.2)
        pyautogui.write(body, interval=0.001)
        time.sleep(0.5)
        
        if os.name == 'nt':
            pyautogui.hotkey('ctrl', 'enter')
        else:
            pyautogui.hotkey('command', 'return')
            
        print("Email sent successfully")
        
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    user_input = input("Enter the purpose of the email: ")
    recipient = input("Enter the recipient's email address: ")
    recipient_name = input("Enter the recipient's name: ")
    sender_name = input("Enter your name: ")
    
    subject = f"Re: {user_input.capitalize()}"
    email_content = generate_email_content(user_input, recipient_name, sender_name)
    print("\nOpening email client and auto-typing content...")
    
    service = authenticate_gmail()
    sender = "me"
    message = create_message(sender, sender_name, recipient, subject, email_content)
    send_email(service, message)

if __name__ == "__main__":
    main()