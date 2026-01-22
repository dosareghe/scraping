import os
import uuid
import yt_dlp
import shutil
import zipfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Authentication from Render Environment Variables
MY_COOKIES = os.getenv("INSTA_COOKIES", "")
USER_AGENT = 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36'

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = "/tmp/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def get_ydl_opts(is_download=False, out_path=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'Cookie': MY_COOKIES,
            'User-Agent': USER_AGENT,
        },
        'nocheckcertificate': True,
        'allowed_extractors': ['instagram', 'facebook', 'generic'],
    }
    if is_download:
        opts['outtmpl'] = out_path
        # 'best' is flexible for both video and image extraction
        opts['format'] = 'best/bestvideo+bestaudio'
    return opts

@app.get("/")
def health_check():
    return {"status": "Online", "message": "Ready for Reels and Posts!"}

@app.get("/preview")
def get_preview(url: str):
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts()) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get('title', 'Social Media Post'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration_string', 'Image/Post'),
                "source": info.get('extractor_key'),
                "is_carousel": 'entries' in info
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download")
async def download_content(url: str):
    job_id = str(uuid.uuid4())
    # Create a unique sub-folder for this specific download job
    job_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    out_tmpl = f"{job_dir}/%(title).50s_%(id)s.%(ext)s"
    
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(is_download=True, out_path=out_tmpl)) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Check if it's a carousel (contains multiple files)
            if 'entries' in info:
                zip_path = f"{DOWNLOAD_DIR}/{job_id}_gallery.zip"
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for root, dirs, files in os.walk(job_dir):
                        for file in files:
                            zipf.write(os.path.join(root, file), file)
                
                # Cleanup the individual files after zipping
                shutil.rmtree(job_dir)
                return FileResponse(path=zip_path, filename="gallery.zip")
            
            else:
                # It's a single video or single image
                filename = ydl.prepare_filename(info)
                return FileResponse(path=filename, filename=os.path.basename(filename))

    except Exception as e:
        # Cleanup on error
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
        raise HTTPException(status_code=500, detail=str(e))
