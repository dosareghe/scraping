
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
        # These two lines ensure it grabs ALL media types in a post
        'ignoreerrors': True,
        'extract_flat': False, 
    }
    if is_download:
        opts['outtmpl'] = out_path
        # We use 'best' to ensure we get images (which have no 'video' tag) and videos
        opts['format'] = 'best' 
        # Crucial for Instagram carousels to prevent skipping images
        opts['writethumbnail'] = True 
    return opts

@app.get("/")
def health_check():
    return {"status": "Online", "message": "Ready for Reels, Photos, and Carousels!"}

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
                "is_carousel": 'entries' in info or info.get('_type') == 'playlist'
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download")
async def download_content(url: str):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(DOWNLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # We use a broader template to catch all file types (.jpg, .mp4, .webp)
    out_tmpl = f"{job_dir}/%(title).30s_%(id)s.%(ext)s"
    
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(is_download=True, out_path=out_tmpl)) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Identify if it's a carousel/multi-item post
            is_multi = 'entries' in info or info.get('_type') == 'playlist'
            
            if is_multi:
                zip_path = f"{DOWNLOAD_DIR}/{job_id}_complete_post.zip"
                
                # Check the folder to see what was actually downloaded
                downloaded_files = os.listdir(job_dir)
                
                if not downloaded_files:
                    raise Exception("No media found to download.")

                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for file in downloaded_files:
                        zipf.write(os.path.join(job_dir, file), file)
                
                shutil.rmtree(job_dir)
                return FileResponse(path=zip_path, filename="instagram_post.zip")
            
            else:
                # Single file download logic
                filename = ydl.prepare_filename(info)
                # If the file doesn't exist (sometimes happens with specific image formats), 
                # check the folder for any file that was created
                if not os.path.exists(filename):
                    files = os.listdir(job_dir)
                    if files:
                        filename = os.path.join(job_dir, files[0])
                    else:
                        raise Exception("File not found after download.")

                return FileResponse(path=filename, filename=os.path.basename(filename))

    except Exception as e:
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
        raise HTTPException(status_code=500, detail=str(e))
