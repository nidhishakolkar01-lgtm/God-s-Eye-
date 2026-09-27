import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

urls = [
    "https://www.pexels.com/search/videos/security%20camera/",
    "https://www.pexels.com/search/videos/security%20guard/",
    "https://www.pexels.com/search/videos/border%20patrol/",
    "https://www.pexels.com/search/videos/fence%20walking/"
]

for u in urls:
    try:
        r = requests.get(u, headers=headers, timeout=10)
        # Find video download URLs from pexels (video-files.pexels.com)
        vids = re.findall(r'https://video-files\.pexels\.com/videos/\d+/[^"\']+\.mp4', r.text)
        if not vids:
            vids = re.findall(r'https://[^"\'\s]+\.mp4\?[^"\'\s]+', r.text)
        print(u, f"Found: {len(vids)}")
        for v in list(set(vids))[:3]:
            print("  ->", v)
    except Exception as e:
        print(u, e)
