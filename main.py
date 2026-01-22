from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
import os
import uuid

app = FastAPI()

# 1. PASTE YOUR LONG COOKIE STRING BETWEEN THE QUOTES BELOW
MY_COOKIES = "datr=i5NyaY4K9zb86iFc26xbudLI;ig_did=5A3C3682-16EF-41A9-9AC9-80E6A75A0C08;mid=aXKTiwAEAAFrM7r_O6eVhbop8u8w;ps_l=1;ps_n=1;ig_nrcb=1;sessionid=80100521443%3Aji0MEX2sARWRc5%3A14%3AAYjUlIXBbmHrcEtLvRB2OPh0Zv9nND4Y3RVw_GzGwg;wd=980x1588;dpr=2.608695652173913;csrftoken=YgWCdAIixxpARl2RjXLXTWJPNcUhS2yE;rur="LDC\05480100521443\0541800654430:01fe56f38f4a44bc2c4e5b2b02b317898adb8048655a8df88962bd4c2504a84402cc7b2c";ds_user_id=80100521443;"

# Common User-Agent to match a mobile browser
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
