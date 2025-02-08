import os
import json
import requests
from flask import Flask, request, jsonify, render_template_string
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from groclake.modellake import ModelLake

# --- Setup Environment Variables ---
# These can be set externally or via a .env file.
# For example:
# os.environ['GROCLAKE_API_KEY'] = "140f6969d5213fd0ece03148e62e461e"
# os.environ['GROCLAKE_ACCOUNT_ID'] = "72aea028970a23b6530c7faa987905e0"
# os.environ['GROQ_API_KEY'] is not needed now.

# --- Initialize ModelLake for LLM Integration ---
modellake = ModelLake()

def call_llm_chat(prompt):
    """
    Uses ModelLake's chat_complete method to process the prompt.
    Returns the answer as a string.
    """
    chat_completion_request = {
        "groc_account_id": os.environ.get("GROCLAKE_ACCOUNT_ID"),
        "messages": [
            {"role": "system", "content": "You are a photo command parser. Output valid JSON."},
            {"role": "user", "content": prompt}
        ]
    }
    response = modellake.chat_complete(chat_completion_request)
    answer = response.get("answer", "").strip()
    return answer

# --- Google Photos API Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/photoslibrary.appendonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata"
]
CREDENTIALS_FILE = "credentials.json"  # Your OAuth credentials file
TOKEN_FILE = "token.json"              # File to store the OAuth token

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
    """Fetch and return recent photos from Google Photos."""
    creds = authenticate()
    url = "https://photoslibrary.googleapis.com/v1/mediaItems"
    headers = {"Authorization": f"Bearer {creds.token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("mediaItems", [])
    return None

def search_photos_by_tag_parameter(tag):
    """Search for photos using a given tag and return matching photos."""
    creds = authenticate()
    url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
    headers = {"Authorization": f"Bearer {creds.token}"}
    data = {"filters": {"contentFilter": {"includedContentCategories": [tag]}}}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("mediaItems", [])
    return None

def create_album(album_name):
    """Create a new album in Google Photos and return its album ID."""
    creds = authenticate()
    url = "https://photoslibrary.googleapis.com/v1/albums"
    headers = {"Authorization": f"Bearer {creds.token}"}
    data = {"album": {"title": album_name}}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("id")
    return None

def list_albums():
    """List all user-created albums."""
    creds = authenticate()
    url = "https://photoslibrary.googleapis.com/v1/albums"
    headers = {"Authorization": f"Bearer {creds.token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("albums", [])
    return None

# --- Photo Agent Class ---
# In this lean version we define our own PhotoAgent class without using a GrocAgent base.
class PhotoAgent:
    def default_handler(self, payload):
        """
        Processes incoming requests.
        Expected payload contains:
          - query_text: A natural language command (e.g., "give me images of night")
        Uses enhanced keyword matching and the LLM (via ModelLake) to convert the query into a structured command.
        """
        try:
            query_text = payload.get("query_text", "").strip()
            lower_query = query_text.lower()
            # Enhanced keyword matching:
            if "list photos" in lower_query or "list images" in lower_query:
                operation = "list photos"
                metadata = payload.get("metadata", {})
            elif ("search photos" in lower_query or "search images" in lower_query or
                  "seach photos" in lower_query or "seach images" in lower_query or
                  (("search" in lower_query or "seach" in lower_query) and ("photo" in lower_query or "image" in lower_query))):
                operation = "search photos"
                metadata = payload.get("metadata", {})
                tag = metadata.get("tag", "")
                if not tag:
                    phrase = "search images of "
                    if phrase in lower_query:
                        tag = lower_query.split(phrase)[-1].strip()
                        metadata["tag"] = tag
            elif "create album" in lower_query:
                operation = "create album"
                metadata = payload.get("metadata", {})
            elif "list albums" in lower_query:
                operation = "list albums"
                metadata = payload.get("metadata", {})
            else:
                # Use LLM to parse the natural language query.
                prompt = (
                    "Convert the following natural language query into a JSON command for a photo agent that supports "
                    "'list photos', 'search photos' (with tag), 'create album' (with album_name), and 'list albums'.\n"
                    f"Query: \"{query_text}\"\n"
                    "Return JSON with key 'operation' and include additional keys if needed. Output only valid JSON."
                )
                print(f"DEBUG: Prompt sent to ModelLake:\n{prompt}\n")
                llm_response = call_llm_chat(prompt)
                print(f"DEBUG: ModelLake response: {llm_response}\n")
                instructions = json.loads(llm_response)
                print(f"DEBUG: Parsed instructions: {instructions}\n")
                operation = instructions.get("operation", "").strip().lower()
                metadata = {k: instructions[k] for k in ["tag", "album_name"] if k in instructions}
            
            # Process the structured command.
            if operation == "list photos":
                photos = list_photos()
                if photos is None:
                    return {"response_text": "Failed to fetch photos."}
                photo_list = [{"filename": p.get("filename", "Unnamed"), "url": p.get("baseUrl", "")} for p in photos[:10]]
                return {"response_text": "Recent photos:", "photos": photo_list}
            elif operation == "search photos":
                tag = metadata.get("tag", "")
                if not tag:
                    return {"response_text": "Please provide a tag for searching."}
                photos = search_photos_by_tag_parameter(tag)
                if not photos:
                    return {"response_text": f"No photos found with tag '{tag}'."}
                photo_list = [{"filename": p.get("filename", "Unnamed"), "url": p.get("baseUrl", "")} for p in photos]
                return {"response_text": f"Photos with tag '{tag}':", "photos": photo_list}
            elif operation == "create album":
                album_name = metadata.get("album_name", "New Album")
                album_id = create_album(album_name)
                if album_id:
                    return {"response_text": f"Album '{album_name}' created successfully!", "album_id": album_id}
                return {"response_text": "Failed to create album."}
            elif operation == "list albums":
                albums = list_albums()
                if not albums:
                    return {"response_text": "No albums found."}
                album_list = [{"title": a.get("title", "Unnamed"), "id": a.get("id", "")} for a in albums]
                return {"response_text": "Your albums:", "albums": album_list}
            else:
                return {"response_text": "Operation not recognized.", "query_text": query_text}
        except Exception as e:
            return {"response_text": f"Error: {str(e)}", "query_text": query_text}

# --- Flask Application Setup ---
app = Flask(__name__)
photo_agent = PhotoAgent()

@app.route("/", methods=["GET", "POST"])
def index():
    response = None
    if request.method == "POST":
        command = request.form.get("command")
        payload = {"query_text": command}
        response = photo_agent.default_handler(payload)
    html = '''
    <!DOCTYPE html>
    <html>
      <head>
        <title>Google Photos Agent</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          label { display: block; margin-top: 10px; }
          .field { margin-bottom: 10px; }
        </style>
      </head>
      <body>
        <h1>Google Photos Agent</h1>
        <form method="POST">
          <div class="field">
            <label for="command">Enter your command (e.g., "give me images of night"):</label>
            <input type="text" id="command" name="command" placeholder="Enter your command here">
          </div>
          <button type="submit">Send Command</button>
        </form>
        {% if response %}
          <h2>Response:</h2>
          {% if response.photos %}
            <h3>Photos:</h3>
            <div>
              {% for photo in response.photos %}
                <div style="display:inline-block; margin:10px; text-align:center;">
                  <img src="{{ photo.url }}" alt="{{ photo.filename }}" style="max-width:200px; max-height:200px;"><br>
                  <span>{{ photo.filename }}</span>
                </div>
              {% endfor %}
            </div>
          {% else %}
            <pre>{{ response|tojson(indent=2) }}</pre>
          {% endif %}
        {% endif %}
      </body>
    </html>
    '''
    return render_template_string(html, response=response)

@app.route("/agent", methods=["POST"])
def agent_endpoint():
    payload = request.get_json(force=True)
    result = photo_agent.default_handler(payload)
    return jsonify(result)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
