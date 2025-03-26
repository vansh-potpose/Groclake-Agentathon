import os
import json
import requests
import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from groclake.modellake import Modellake

# --- Page Configuration ---
st.set_page_config(
    page_title="Photo Assistant",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
    <style>
    .stButton > button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #FF4B4B;
        color: white;
        border: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #FF6B6B;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main > div {
        padding: 2em;
        border-radius: 10px;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .css-1d391kg {
        padding: 2em;
    }
    .stTextInput > div > div > input {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 1em;
        font-size: 1.1em;
    }
    .stTab {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 1em;
        margin-bottom: 1em;
    }
    .photo-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1.5rem;
        padding: 1rem;
    }
    .photo-card {
        background: white;
        border-radius: 10px;
        overflow: hidden;
        transition: transform 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .photo-card:hover {
        transform: translateY(-5px);
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    </style>
""", unsafe_allow_html=True)

# --- Initialize Modellake for LLM Integration ---
@st.cache_resource
def init_modellake():
    return Modellake()

modellake = init_modellake()

def call_llm_chat(prompt):
    """Uses Modellake's chat_complete method to process the prompt."""
    try:
        chat_completion_request = {
            "groc_account_id": os.environ.get("GROCLAKE_ACCOUNT_ID"),
            "messages": [
                {"role": "system", "content": "You are a photo command parser. Output valid JSON."},
                {"role": "user", "content": prompt}
            ]
        }
        response = modellake.chat_complete(chat_completion_request)
        return response.get("answer", "").strip()
    except Exception as e:
        st.error(f"Error processing chat request: {str(e)}")
        return None

# --- Google Photos API Setup ---
SCOPES = [
    "https://www.googleapis.com/auth/photoslibrary.appendonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata"
]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

@st.cache_resource
def authenticate():
    """Authenticate and return Google Photos API credentials."""
    try:
        creds = None
        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        if not creds or not creds.valid:
            if not os.path.exists(CREDENTIALS_FILE):
                st.error("credentials.json file not found. Please ensure it exists in the project directory.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8080)
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
        return creds
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def list_photos():
    """Fetch and return recent photos from Google Photos."""
    creds = authenticate()
    if not creds:
        return None
    
    try:
        url = "https://photoslibrary.googleapis.com/v1/mediaItems"
        headers = {"Authorization": f"Bearer {creds.token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("mediaItems", [])
        st.error(f"API Error: {response.status_code}")
        return None
    except Exception as e:
        st.error(f"Error fetching photos: {str(e)}")
        return None

@st.cache_data(ttl=300)
def search_photos(tag):
    """Search for photos using a given tag."""
    creds = authenticate()
    if not creds:
        return None
    
    try:
        url = "https://photoslibrary.googleapis.com/v1/mediaItems:search"
        headers = {"Authorization": f"Bearer {creds.token}"}
        data = {"filters": {"contentFilter": {"includedContentCategories": [tag]}}}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json().get("mediaItems", [])
        st.error(f"API Error: {response.status_code}")
        return None
    except Exception as e:
        st.error(f"Error searching photos: {str(e)}")
        return None

def create_album(album_name):
    """Create a new album in Google Photos."""
    creds = authenticate()
    if not creds:
        return None
    
    try:
        url = "https://photoslibrary.googleapis.com/v1/albums"
        headers = {"Authorization": f"Bearer {creds.token}"}
        data = {"album": {"title": album_name}}
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json().get("id")
        st.error(f"API Error: {response.status_code}")
        return None
    except Exception as e:
        st.error(f"Error creating album: {str(e)}")
        return None

@st.cache_data(ttl=300)
def list_albums():
    """List all user-created albums."""
    creds = authenticate()
    if not creds:
        return None
    
    try:
        url = "https://photoslibrary.googleapis.com/v1/albums"
        headers = {"Authorization": f"Bearer {creds.token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json().get("albums", [])
        st.error(f"API Error: {response.status_code}")
        return None
    except Exception as e:
        st.error(f"Error listing albums: {str(e)}")
        return None

def display_photos(photos, columns=3):
    """Display photos in a responsive grid."""
    if not photos:
        return
    
    cols = st.columns(columns)
    for idx, photo in enumerate(photos[:12]):  # Show up to 12 photos
        with cols[idx % columns]:
            st.image(
                photo.get("baseUrl", ""),
                caption=photo.get("filename", ""),
                use_container_width=True
            )
            with st.expander("Photo Details"):
                st.write(f"📅 Created: {photo.get('mediaMetadata', {}).get('creationTime', 'Unknown')}")
                st.write(f"📏 Dimensions: {photo.get('mediaMetadata', {}).get('width', '?')}x{photo.get('mediaMetadata', {}).get('height', '?')}")

def main():
    # Sidebar
    with st.sidebar:
        st.image("https://images.unsplash.com/photo-1552168324-d612d77725e3?auto=format&fit=crop&w=300&q=80", 
                 use_container_width=True)
        st.markdown("---")
        st.markdown("""
        ### 🎯 Quick Commands
        
        ```python
        list photos
        search images of [tag]
        create album [name]
        list albums
        ```
        """)
        st.markdown("---")
        st.markdown("### 📊 Stats")
        if albums := list_albums():
            st.metric("Total Albums", len(albums))
    
    # Main content
    st.title("📸 Photo Assistant")
    st.markdown("""
    Welcome to your personal photo management assistant! 
    Use natural language commands to manage your Google Photos library efficiently.
    """)
    
    # Command input with tabs
    tab1, tab2 = st.tabs(["💬 Command Center", "ℹ️ Help & Documentation"])
    
    with tab1:
        command = st.text_input(
            "Enter your command:",
            placeholder="Try 'list photos' or 'search images of sunset'",
            key="command_input"
        )
        
        execute = st.button("Execute Command", key="execute_btn", use_container_width=True)
        
        if execute:
            with st.spinner("🔄 Processing your request..."):
                query_text = command.strip().lower()
                
                # Command processing
                if "list photos" in query_text:
                    if photos := list_photos():
                        st.success("📸 Here are your recent photos:")
                        display_photos(photos)
                    else:
                        st.error("No photos found or error occurred.")
                        
                elif "search images" in query_text or "search photos" in query_text:
                    tag = query_text.split("of")[-1].strip()
                    st.info(f"🔍 Searching for photos matching: '{tag}'")
                    if photos := search_photos(tag):
                        st.success(f"Found {len(photos)} matching photos:")
                        display_photos(photos)
                    else:
                        st.warning(f"No photos found matching '{tag}'")
                        
                elif "create album" in query_text:
                    album_name = query_text.split("create album")[-1].strip() or "New Album"
                    with st.spinner(f"Creating album '{album_name}'..."):
                        if album_id := create_album(album_name):
                            st.success(f"✨ Album '{album_name}' created successfully!")
                            st.balloons()
                        else:
                            st.error("Failed to create album.")
                        
                elif "list albums" in query_text:
                    if albums := list_albums():
                        st.success("📚 Your Albums:")
                        for album in albums:
                            with st.expander(f"📁 {album.get('title', 'Unnamed')}"):
                                st.write(f"📅 Created: {album.get('creationTime', 'Unknown')}")
                                st.write(f"📸 Total items: {album.get('mediaItemsCount', '0')}")
                                if album.get('coverPhotoBaseUrl'):
                                    st.image(album['coverPhotoBaseUrl'], use_container_width=True)
                    else:
                        st.info("No albums found.")
                else:
                    st.error("⚠️ Command not recognized. Please check the help tab for available commands.")
    
    with tab2:
        st.markdown("""
        ### 📚 Available Commands
        
        1. **List Recent Photos**
           - Command: `list photos`
           - Shows your most recent photos in a grid layout
           - Includes photo details and metadata
        
        2. **Search Photos**
           - Command: `search images of [what you're looking for]`
           - Example: `search images of sunset`
           - Searches through your entire photo library
        
        3. **Create Album**
           - Command: `create album [album name]`
           - Example: `create album Summer Vacation 2025`
           - Creates a new album in your Google Photos
        
        4. **List Albums**
           - Command: `list albums`
           - Shows all your albums with details
           - Includes cover photos and item counts
        
        ### 💡 Tips
        - Commands are case-insensitive
        - Use natural language in your commands
        - Check the sidebar for quick command reference
        """)

if __name__ == "__main__":
    main()
