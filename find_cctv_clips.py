import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

for q in ['cctv', 'surveillance', 'night-security', 'security-patrol', 'border-crossing']:
    url = f"https://pixabay.com/videos/search/{q}/"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        matches = re.findall(r'https://cdn\.pixabay\.com/video/[^"\'\s]+_tiny\.mp4', r.text)
        print(f"[{q}] {len(matches)} links:")
        for m in list(set(matches))[:3]:
            print(f"  {m}")
    except Exception as e:
        print(f"Error {q}: {e}")
