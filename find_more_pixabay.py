import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

for q in ['fence', 'security', 'guard', 'soldier', 'patrol', 'checkpoint']:
    url = f"https://pixabay.com/videos/search/{q}/"
    r = requests.get(url, headers=headers, timeout=10)
    matches = re.findall(r'https://cdn\.pixabay\.com/video/[^"\'\s]+_(?:tiny|small|medium)\.mp4', r.text)
    print(f"[{q}] Found {len(matches)} matches")
    for m in list(set(matches))[:4]:
        print(f"  {m}")
