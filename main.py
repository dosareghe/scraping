from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import yt_dlp
import os
import uuid

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all domains to talk to your backend
    allow_methods=["*"],
    allow_headers=["*"],
)

# Render uses a temporary /tmp folder for storage
DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.get("/download")
async def download_content(url: str):
    unique_id = str(uuid.uuid4())
    # This template ensures we don't have filename conflicts
    out_tmpl = f"{DOWNLOAD_DIR}/{unique_id}_%(title)s.%(ext)s"
    
    ydl_opts = {
        'outtmpl': out_tmpl,
        'format': 'best',
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        # Return the file to the user's browser
        return FileResponse(
            path=filename, 
            filename=os.path.basename(filename),
            media_type='application/octet-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def home():
    return {"status": "Backend is running! Use /download?url=YOUR_URL"}
