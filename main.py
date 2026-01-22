import os
from fastapi import FastAPI, HTTPException
# ... (keep other imports)

app = FastAPI()

# This looks for the secret value on Render. 
# If it's not found, it defaults to an empty string.
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
    """Helper to maintain consistent headers and cookies"""
    opts = {
        'quiet': True,
        'http_headers': {
            'Cookie': MY_COOKIES,
            'User-Agent': USER_AGENT,
        },
        'nocheckcertificate': True, # Helps avoid some SSL errors on cloud servers
    }
    if is_download:
        opts['outtmpl'] = out_path
        opts['format'] = 'best'
    return opts

@app.get("/preview")
def get_preview(url: str):
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
        # Returning the error message helps you debug if cookies expired
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/download")
async def download_content(url: str):
    unique_id = str(uuid.uuid4())
    out_tmpl = f"{DOWNLOAD_DIR}/{unique_id}_%(title)s.%(ext)s"
    
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(True, out_tmpl)) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        return FileResponse(path=filename, filename=os.path.basename(filename))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
