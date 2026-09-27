import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

queries = ['thermal', 'infrared', 'flir', 'night-vision', 'drone-tracking']
for q in queries:
    url = f"https://pixabay.com/videos/search/{q}/"
    r = requests.get(url, headers=headers, timeout=10)
    matches = re.findall(r'https://cdn\.pixabay\.com/video/[^"\'\s]+_(?:tiny|small|medium)\.mp4', r.text)
    print(f"[{q}] Found {len(matches)} matches")
    for m in list(set(matches))[:5]:
        print(f"  {m}")
