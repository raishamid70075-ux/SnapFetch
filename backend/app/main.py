from fastapi import FastAPI, Query, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.downloader import extract_video_details
import yt_dlp, os, re, uuid, glob, urllib.request

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
MEDIA_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
               "webp": "image/webp", "mp4": "video/mp4", "m4v": "video/mp4",
               "webm": "video/webm", "mov": "video/quicktime"}
REFERERS = {"instagram": "https://www.instagram.com/", "tiktok": "https://www.tiktok.com/"}


def _cookie_file(url: str) -> str | None:
    names = ("cookiestiktok.txt", "cookies.txt") if "tiktok.com" in url.lower() else ("cookies.txt",)
    for name in names:
        if os.path.isfile(name):
            return name
    return None


@app.get("/api/extract")
def extract(url: str, method: str = "ffmpeg"): return extract_video_details(url, method)

@app.get("/api/download")
def download(url: str = Query(...), format_id: str = Query(...), title: str = Query("video"), ext: str = Query("mp4"), method: str = Query("ffmpeg")):
    clean_title = re.sub(r'[\\/*?:\"<>|]', "", title)[:50]
    os.makedirs("temp", exist_ok=True)
    file_id = str(uuid.uuid4())

    if ext in IMAGE_EXTS or format_id == "direct":
        # URL media langsung (slide foto/video IG & TikTok), tidak lewat yt-dlp
        final_file = f"temp/{file_id}.{ext}"
        referer = next((v for k, v in REFERERS.items() if k in url.lower()), "")
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer})
        with urllib.request.urlopen(req, timeout=60) as r, open(final_file, "wb") as f:
            f.write(r.read())
        media_type = MEDIA_TYPES.get(ext, f"image/{ext}")
    else:
        if ext == "mp3":
            ydl_opts = {
                'format': format_id or 'bestaudio/best',
                'outtmpl': f"temp/{file_id}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
                'js_runtimes': {"node": {}},
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }
            media_type = 'audio/mpeg'
        else:
            ydl_opts = {
                # format IG (1/2/3) bisa hilang di pass download, fallback ke best
                'format': f"{format_id}/best",
                'outtmpl': f"temp/{file_id}.%(ext)s",
                'quiet': True,
                'no_warnings': True,
                'js_runtimes': {"node": {}}
            }
            if method == "ffmpeg":
                ydl_opts['merge_output_format'] = 'mp4'
            media_type = 'video/mp4'

        ck = _cookie_file(url)
        if ck:
            ydl_opts["cookiefile"] = ck

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

    downloaded_files = glob.glob(f"temp/{file_id}.*")
    if not downloaded_files:
        raise HTTPException(status_code=500, detail="Failed to download file")
        
    final_file = downloaded_files[0]
    actual_ext = final_file.split(".")[-1]
    
    def remove_file(path: str):
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception:
            pass
            
    bg_tasks = BackgroundTasks()
    bg_tasks.add_task(remove_file, final_file)
        
    return FileResponse(final_file, media_type=media_type, filename=f"{clean_title}.{actual_ext}", background=bg_tasks)