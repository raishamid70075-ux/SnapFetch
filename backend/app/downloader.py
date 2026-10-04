import yt_dlp
import os
import re
from app.utils import format_duration
from yt_dlp.utils.traversal import traverse_obj


_TIKTOK_URL_RE = re.compile(r"tiktok\.com/(?:@(?P<user>[\w.\-]+)/)?(?:video|photo)/(?P<id>\d+)")


def _is_tiktok(url: str) -> bool:
    return "tiktok.com" in url.lower()


def _is_instagram(url: str) -> bool:
    return "instagram.com" in url.lower() or "instagr.am" in url.lower()


def _ig_media(item: dict) -> tuple[str, str]:
    # (url, ext) untuk 1 slide: video pakai format terakhir, foto pakai thumbnail tertinggi
    fmts = [f for f in (item.get("formats") or []) if f.get("url")]
    if fmts:
        return fmts[-1]["url"], fmts[-1].get("ext") or "mp4"
    for t in reversed(item.get("thumbnails") or []):
        if t.get("url"):
            return t["url"], "jpg"
    return item.get("thumbnail") or "", "jpg"


def _cookie_file(url: str) -> str | None:
    # Postingan TikTok butuh sesi login; pakai cookiestiktok.txt kalau ada
    names = ("cookiestiktok.txt", "cookies.txt") if _is_tiktok(url) else ("cookies.txt",)
    for name in names:
        if os.path.isfile(name):
            return name
    return None


def _is_slideshow(info: dict | None) -> bool:
    # yt-dlp hanya memberi format audio untuk post foto (tidak ada video stream)
    formats = (info or {}).get("formats") or []
    return all((f.get("vcodec") or "none") == "none" for f in formats)


def _carousel_from_item(item: dict):
    # Satu slide per foto: ambil urlList pertama saja (tiap foto punya beberapa CDN URL)
    images = []
    for img in traverse_obj(item, ("imagePost", "images", ..., {dict})) or []:
        urls = [u for u in traverse_obj(img, ("imageURL", "urlList", ..., {str})) if u]
        if urls:
            images.append({"id": len(images) + 1, "url": urls[0],
                           "thumbnail": urls[0], "title": f"Slide {len(images) + 1}"})
    if not images:
        return None

    return {
        "status": "success",
        "type": "carousel",
        "title": item.get("desc") or "TikTok Carousel",
        "images": images,
        "thumbnail": images[0]["url"],
        "duration": "00:00",
    }


def _extract_tiktok_carousel(ydl, info: dict | None, url: str):
    # yt-dlp membuang field imagePost, jadi kita pakai extractor-nya lagi untuk membacanya
    from yt_dlp.extractor.tiktok import TikTokIE
    ie = TikTokIE(ydl)
    video_id = (info or {}).get("id")
    uploader = (info or {}).get("uploader")
    if not video_id:
        m = _TIKTOK_URL_RE.search(url)
        if not m:
            return None
        video_id, uploader = m.group("id"), m.group("user")
    item, _ = ie._extract_web_data_and_status(
        ie._create_url(uploader, video_id), video_id, fatal=False)
    return _carousel_from_item(item) if item else None


def extract_video_details(video_url: str, method: str = "ffmpeg", cookie_path: str | None = None):
    # Cek file cookies otomatis (TikTok pakai cookiestiktok.txt)
    if not cookie_path:
        cookie_path = _cookie_file(video_url)

    # Jangan langsung memanipulasi string URL di awal agar shortlink tidak rusak
    ydl_opts = {
        "quiet": True,
        "no_warnings": True, # Menyembunyikan pesan kuning (WARNING) yang tidak berbahaya
        "js_runtimes": {"node": {}}, # Mengaktifkan Node.js yang sudah ada di PC untuk YouTube cipher
        # Gunakan User-Agent modern agar tidak diblokir sistem anti-bot TikTok
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        }
    }
    
    if cookie_path and os.path.isfile(cookie_path):
        ydl_opts["cookiefile"] = cookie_path

    if _is_instagram(video_url):
        # Post foto/carousel IG tidak punya format video sama sekali,
        # biar yt-dlp balikin info kosong (thumbnail) alih-alih melempar error
        ydl_opts["ignore_no_formats_error"] = True

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            extract_error = None
            # Foto TikTok: yt-dlp hanya dukung /video/, jadi baca imagePost dulu
            if _is_tiktok(video_url) and "/photo/" in video_url:
                carousel = _extract_tiktok_carousel(ydl, None, video_url)
                if carousel:
                    return carousel
            try:
                info = ydl.extract_info(video_url, download=False)
            except Exception as e:
                info, extract_error = None, e

            # 1. PENANGANAN UNTUK TIKTOK FOTO / CAROUSEL
            # Post foto hanya menghasilkan format audio dari yt-dlp, jadi imagePost
            # dibaca langsung dari data extractor-nya.
            if _is_tiktok(video_url) and (info is None or _is_slideshow(info)):
                carousel = _extract_tiktok_carousel(ydl, info, video_url)
                if carousel:
                    return carousel

            if extract_error:
                raise extract_error

        # 1a. INSTAGRAM: post foto / carousel tidak punya format video,
        # jadi kita ambil thumbnail res tertinggi (atau URL video per slide)
        if _is_instagram(video_url):
            entries = info["entries"] if info.get("_type") == "playlist" else [info]
            need_carousel = info.get("_type") == "playlist" or not info.get("formats")
            if need_carousel:
                images = []
                for e in entries:
                    if not e:
                        continue
                    u, x = _ig_media(e)
                    if u:
                        images.append({
                            "id": len(images) + 1, "url": u, "ext": x,
                            "thumbnail": u, "title": f"Slide {len(images) + 1}",
                        })
                if images:
                    return {
                        "status": "success",
                        "type": "carousel",
                        "title": info.get("description") or info.get("title") or "Instagram Post",
                        "images": images,
                        "thumbnail": images[0]["thumbnail"],
                        "duration": "00:00",
                    }

        # 1b. Fallback carousel bawaan yt-dlp (playlist)
        if info.get("_type") == "playlist" or "entries" in info:
            entries = info.get("entries", [])
            images = []
            
            for idx, entry in enumerate(entries):
                if not entry:
                    continue
                # Mengambil URL foto resolusi tertinggi yang tersedia
                img_url = entry.get("url") or entry.get("thumbnail")
                if img_url:
                    images.append({
                        "id": idx + 1,
                        "url": img_url,
                        "title": entry.get("title", f"Slide {idx+1}")
                    })
            
            return {
                "status": "success",
                "type": "carousel",
                "title": info.get("title") or "TikTok Carousel",
                "images": images,
                "thumbnail": info.get("thumbnail") or (images[0]["url"] if images else ""),
                "duration": "00:00"
            }

        # 2. PENANGANAN UNTUK VIDEO BIASA (YOUTUBE / TIKTOK VIDEO / INSTAGRAM VIDEO)
        available_formats = []
        formats = info.get("formats", [])
        
        for fmt in formats:
            # Filter format yang layak unduh sesuai kebutuhan aplikasimu
            if fmt.get("vcodec") != "none" or fmt.get("acodec") != "none":
                has_audio = "true" if fmt.get("acodec") != "none" else "false"
                label = f"{fmt.get('format_note', 'Video')} ({fmt.get('ext', 'mp4')})"
                if fmt.get('filesize'):
                    label += f" - {round(fmt.get('filesize') / (1024*1024), 1)} MB"
                
                available_formats.append({
                    "format_id": fmt.get("format_id"),
                    "url": fmt.get("url"),
                    "ext": fmt.get("ext", "mp4"),
                    "label": label,
                    "has_audio": has_audio
                })

        return {
            "status": "success",
            "type": "video",
            "title": info.get("title", "Video Tanpa Judul"),
            "thumbnail": info.get("thumbnail", ""),
            "duration": format_duration(info.get("duration")),
            "formats": available_formats,
        }

    except Exception as e:
        error_msg = str(e)
        # Menghapus kode ANSI (seperti \033[0;31m) dari pesan error yt-dlp
        clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', error_msg)
        return {
            "status": "error",
            "message": clean_msg
        }


if __name__ == "__main__":
    sample = {"desc": "hi", "imagePost": {"images": [
        {"imageURL": {"urlList": ["https://a/1.jpg", "https://a/1b.jpg"]}},
        {"imageURL": {"urlList": ["https://a/2.jpg"]}},
    ]}}
    out = _carousel_from_item(sample)
    # 2 foto dengan 2 CDN URL -> harusnya tepat 2 slide, bukan 3
    assert out["type"] == "carousel" and len(out["images"]) == 2, out
    assert out["images"][0]["thumbnail"] == "https://a/1.jpg"
    assert out["images"][1]["url"] == "https://a/2.jpg"
    assert _carousel_from_item({}) is None
    assert _TIKTOK_URL_RE.search(
        "https://www.tiktok.com/@gw.shihab2.0/photo/7674478327268216085?x=1"
    ).group("id") == "7674478327268216085"
    assert _is_slideshow({"formats": [{"vcodec": "none"}]}) is True
    assert _is_slideshow({"formats": [{"vcodec": "h264"}]}) is False
    assert _is_tiktok("https://vm.tiktok.com/abc") is True
    assert _is_instagram("https://www.instagram.com/p/AbC123/") is True
    assert _is_instagram("https://www.tiktok.com/@x/video/1") is False
    assert _ig_media({"formats": [{"url": "https://c/v.mp4", "ext": "mp4"}]}) == ("https://c/v.mp4", "mp4")
    assert _ig_media({"thumbnails": [{"url": "https://c/s.jpg"}]}) == ("https://c/s.jpg", "jpg")
    assert _ig_media({"thumbnail": "https://c/t.jpg"}) == ("https://c/t.jpg", "jpg")
    assert _ig_media({}) == ("", "jpg")
    print("ok")