import yt_dlp

ydl_opts = {
    "format": "bestvideo[height<=720][ext=mp4]+bestaudio/best[height<=720][ext=mp4]/best",
    "outtmpl": "sample_footage/tactical_%(id)s.%(ext)s",
    "noplaylist": True,
    "max_filesize": 25 * 1024 * 1024,
    "quiet": False
}

queries = [
    "ytsearch3:BSF border surveillance night camera CCTV",
    "ytsearch3:border perimeter security thermal camera fence intrusion",
    "ytsearch3:border patrol CCTV fence surveillance footage"
]

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for q in queries:
        try:
            print(f"Searching: {q}")
            res = ydl.extract_info(q, download=False)
            entries = res.get("entries", [])
            for e in entries:
                if e:
                    title = e.get("title")
                    dur = e.get("duration", 0)
                    url = e.get("webpage_url")
                    print(f"  FOUND: [{dur}s] {title} -> {url}")
        except Exception as err:
            print(f"Error {q}: {err}")
