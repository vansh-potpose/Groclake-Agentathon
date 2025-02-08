from flask import Flask, request, jsonify, render_template_string
import os
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from groclake.utillake import GrocAgent

# --- Google Photos API Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/photoslibrary.appendonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata"
]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def authenticate():
    """Authenticate and return Google Photos API credentials."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=8080)
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    return creds

def list_photos():
    """Fetches and returns recent photos from Google Photos."""
    creds = authenticate()
    url = "https://photoslibrary.googleapis.com/v1/mediaItems"
    headers = {"Authorization": f"Bearer {creds.token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("mediaItems", [])
    return None

def search_photos_by_tag_parameter(tag):
    """Search for photos using a tag provided as parameter and return matching photos."""
    creds = authenticate()
    url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
    headers = {"Authorization": f"Bearer {creds.token}"}
    data = {
        "filters": {
            "contentFilter": {
                "includedContentCategories": [tag]
            }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("mediaItems", [])
    return None

def create_album(album_name):
    """Creates a new album in Google Photos and returns the album ID."""
    creds = authenticate()
    url = "https://photoslibrary.googleapis.com/v1/albums"
    headers = {"Authorization": f"Bearer {creds.token}"}
    data = {"album": {"title": album_name}}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("id")
    return None

def add_photos_to_album(tag_photos, album_id):
    """Adds photos to an album based on tag."""
    if not tag_photos:
        return False
    creds = authenticate()
    url = f"https://photoslibrary.googleapis.com/v1/albums/{album_id}:batchAddMediaItems"
    headers = {"Authorization": f"Bearer {creds.token}"}
    media_ids = [photo["id"] for photo in tag_photos]
    data = {"mediaItemIds": media_ids}
    response = requests.post(url, headers=headers, json=data)
    return response.status_code == 200

def list_albums():
    """Lists all user-created albums."""
    creds = authenticate()
    url = "https://photoslibrary.googleapis.com/v1/albums"
    headers = {"Authorization": f"Bearer {creds.token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("albums", [])
    return None

# --- GrocLake Agent Integration ---
class PhotoAgent(GrocAgent):
    def __init__(self, app):
        # Pass an empty dictionary for adaptor_config to avoid NoneType errors.
        super().__init__(app, "PhotoAgent", "photo_query", "Handles Google Photos queries", self.default_handler, adaptor_config={})
    
    def default_handler(self, payload):
        """
        Processes incoming requests.
        Expected payload contains:
          - query_text: e.g., "list photos", "search photos", "create album", or "list albums"
          - metadata: optional dict for additional parameters (e.g., "tag" or "album_name")
        """
        try:
            query_text = payload.get("query_text", "").lower()
            
            if "list photos" in query_text:
                photos = list_photos()
                if photos is None:
                    return {"response_text": "Failed to fetch photos."}
                photo_list = [
                    {"filename": photo.get("filename", "Unnamed"), "url": photo.get("baseUrl", "")}
                    for photo in photos[:10]
                ]
                return {"response_text": "Recent photos:", "photos": photo_list}
            
            elif "search photos" in query_text:
                tag = payload.get("metadata", {}).get("tag", "")
                if not tag:
                    return {"response_text": "Please provide a tag for searching."}
                photos = search_photos_by_tag_parameter(tag)
                if not photos:
                    return {"response_text": f"No photos found with tag '{tag}'."}
                photo_list = [
                    {"filename": photo.get("filename", "Unnamed"), "url": photo.get("baseUrl", "")}
                    for photo in photos
                ]
                return {"response_text": f"Photos with tag '{tag}':", "photos": photo_list}
            
            elif "create album" in query_text:
                album_name = payload.get("metadata", {}).get("album_name", "New Album")
                album_id = create_album(album_name)
                if album_id:
                    return {"response_text": f"Album '{album_name}' created successfully!", "album_id": album_id}
                return {"response_text": "Failed to create album."}
            
            elif "list albums" in query_text:
                albums = list_albums()
                if not albums:
                    return {"response_text": "No albums found."}
                album_list = [
                    {"title": album.get("title", "Unnamed"), "id": album.get("id", "")}
                    for album in albums
                ]
                return {"response_text": "Your albums:", "albums": album_list}
            
            else:
                return {"response_text": "Command not recognized. Use 'list photos', 'search photos', 'create album', or 'list albums'."}
        
        except Exception as e:
            return {"response_text": f"Error: {str(e)}"}

# --- Flask Application Setup ---
app = Flask(__name__)
photo_agent = PhotoAgent(app)

# User-friendly web interface at the root route
@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    if request.method == "POST":
        command = request.form.get("command")
        payload = {"query_text": command}
        metadata = {}
        if command == "search photos":
            tag = request.form.get("tag")
            if tag:
                metadata["tag"] = tag
        elif command == "create album":
            album_name = request.form.get("album_name")
            if album_name:
                metadata["album_name"] = album_name
        if metadata:
            payload["metadata"] = metadata
        # Call the agent's handler with the built payload.
        response = photo_agent.default_handler(payload)
    
    # A simple HTML template for a user-friendly form.
    html = '''
    <!DOCTYPE html>
    <html>
    <head>
      <title>Google Photos GrocLake Agent</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        label { display: block; margin-top: 10px; }
        .field { margin-bottom: 10px; }
      </style>
    </head>
    <body>
      <h1>Google Photos GrocLake Agent</h1>
      <form method="POST">
        <div class="field">
          <label for="command">Choose a command:</label>
          <select id="command" name="command" onchange="toggleFields()">
            <option value="list photos">List Photos</option>
            <option value="search photos">Search Photos</option>
            <option value="create album">Create Album</option>
            <option value="list albums">List Albums</option>
          </select>
        </div>
        <div class="field" id="tagField" style="display: none;">
          <label for="tag">Tag (for search photos):</label>
          <input type="text" id="tag" name="tag" placeholder="e.g., outdoor">
        </div>
        <div class="field" id="albumField" style="display: none;">
          <label for="album_name">Album Name (for create album):</label>
          <input type="text" id="album_name" name="album_name" placeholder="e.g., Vacation Album">
        </div>
        <button type="submit">Send Command</button>
      </form>
      <script>
        function toggleFields() {
          var command = document.getElementById("command").value;
          document.getElementById("tagField").style.display = (command === "search photos") ? "block" : "none";
          document.getElementById("albumField").style.display = (command === "create album") ? "block" : "none";
        }
        window.onload = toggleFields;
      </script>
      {% if response %}
        <h2>Response:</h2>
        <pre>{{ response|tojson(indent=2) }}</pre>
      {% endif %}
    </body>
    </html>
    '''
    return render_template_string(html, response=response)

# Also keep the original /agent endpoint for API calls.
@app.route("/agent", methods=["POST"])
def agent_endpoint():
    payload = request.get_json(force=True)
    response = photo_agent.default_handler(payload)
    return jsonify(response)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
