import yt_dlp

ydl_opts = {
    "format": "best[ext=mp4]/bestvideo[ext=mp4]/best",
    "outtmpl": "sample_footage/%(id)s.%(ext)s",
    "quiet": False
}

targets = [
    ("rvss_border_surveillance", "https://www.youtube.com/watch?v=G68Lr2LAjYs"),
    ("flir_thermal_perimeter", "https://www.youtube.com/watch?v=hQN5alpt3Jw"),
    ("border_fence_crossing", "https://www.youtube.com/watch?v=enV2BRAIpDg")
]

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    for name, url in targets:
        print(f"Downloading {name} from {url}...")
        try:
            ydl.download([url])
        except Exception as e:
            print(f"Failed {name}: {e}")
