import os
import uuid
import yt_dlp
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 1. AUTHENTICATION: This looks for your cookie string in Render's Environment Variables
# Key should be: INSTA_COOKIES
MY_COOKIES = os.getenv("INSTA_COOKIES", "")

# Identity to match your phone's browser
USER_AGENT = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36'

# Enable CORS so your GitHub Pages frontend can talk to this Render backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Render uses /tmp for ephemeral file storage (limit is usually 2GB)
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_ydl_opts(is_download=False, out_path=None):
    """
    Centralized configuration for yt-dlp. 
    Using http_headers instead of a cookie file for easier mobile deployment.
    """
    opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'Cookie': MY_COOKIES,
            'User-Agent': USER_AGENT,
        },
        'nocheckcertificate': True,
    }
    
    if is_download:
        opts['outtmpl'] = out_path
        opts['format'] = 'best'
        
    return opts

@app.get("/")
def health_check():
    return {"status": "Online", "message": "Backend is ready!"}

@app.get("/preview")
def get_preview(url: str):
    """Fetches video title and thumbnail to show the user before they download."""
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")
        
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get('title', 'Video'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration_string'),
                "source": info.get('extractor_key')
            }
    except Exception as e:
        # We pass the error message so you can see if it's a 'Login Required' issue
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download")
async def download_content(url: str):
    """Downloads the file to the server and then streams it to the user's phone."""
    unique_id = str(uuid.uuid4())
    # Sanitize the title later if needed, but yt-dlp handles most characters
    out_tmpl = f"{DOWNLOAD_DIR}/{unique_id}_%(title)s.%(ext)s"
    
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(is_download=True, out_path=out_tmpl)) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        # Send the file to the browser and delete it from server after sending
        return FileResponse(
            path=filename, 
            filename=os.path.basename(filename),
            media_type='application/octet-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
