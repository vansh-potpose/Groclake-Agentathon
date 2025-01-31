import os
import requests
import json
import webbrowser
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.cloud import vision
from google.cloud.vision_v1 import types
import io

# Scopes required for Google Photos API
SCOPES = ["https://www.googleapis.com/auth/photoslibrary.appendonly",
          "https://www.googleapis.com/auth/photoslibrary.readonly"]

# Authenticate user and get credentials
def authenticate():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

# Upload an image to Google Photos
def upload_photo(image_path):
    creds = authenticate()
    upload_url = "https://photoslibrary.googleapis.com/v1/uploads"
    
    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/octet-stream",
        "X-Goog-Upload-File-Name": os.path.basename(image_path),
        "X-Goog-Upload-Protocol": "raw"
    }

    with open(image_path, "rb") as image_file:
        response = requests.post(upload_url, data=image_file, headers=headers)

    if response.status_code == 200:
        upload_token = response.text
        create_item_url = "https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate"

        data = {
            "newMediaItems": [{
                "description": "Uploaded via Python",
                "simpleMediaItem": {"uploadToken": upload_token}
            }]
        }

        response = requests.post(create_item_url, json=data, headers={"Authorization": f"Bearer {creds.token}"})
        print("Uploaded Successfully:", response.json())
    else:
        print("Error Uploading:", response.text)

# Retrieve recent photos
def get_recent_photos():
    creds = authenticate()
    service = build("photoslibrary", "v1", credentials=creds)

    results = service.mediaItems().list(pageSize=5).execute()
    items = results.get("mediaItems", [])

    if not items:
        print("No photos found.")
    else:
        print("Recent Photos:")
        for item in items:
            print(item["baseUrl"])
            webbrowser.open(item["baseUrl"])  # Opens the photo in a browser

# Use Google Vision AI to analyze an image
def analyze_photo(image_path):
    client = vision.ImageAnnotatorClient()

    with io.open(image_path, "rb") as image_file:
        content = image_file.read()

    image = types.Image(content=content)
    response = client.label_detection(image=image)
    labels = response.label_annotations

    print("AI Analysis:")
    for label in labels:
        print(f" - {label.description} ({label.score:.2f})")

# Main Function
if __name__ == "__main__":
    while True:
        print("\nGoogle Photos AI Agent")
        print("1. Upload a Photo")
        print("2. Get Recent Photos")
        print("3. Analyze a Photo with AI")
        print("4. Exit")
        
        choice = input("Choose an option: ")
        
        if choice == "1":
            image_path = input("Enter image path: ")
            upload_photo(image_path)
        elif choice == "2":
            get_recent_photos()
        elif choice == "3":
            image_path = input("Enter image path: ")
            analyze_photo(image_path)
        elif choice == "4":
            break
        else:
            print("Invalid choice. Try again.")
