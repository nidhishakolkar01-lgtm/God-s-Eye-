import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}

search_terms = [
    'climbing-fence',
    'trespassing',
    'intruder',
    'security-camera-night',
    'patrol-border',
    'night-vision-scope'
]

results = {}
for term in search_terms:
    url = f"https://pixabay.com/videos/search/{term}/"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        matches = re.findall(r'https://cdn\.pixabay\.com/video/[^"\'\s]+_(?:tiny|small|medium)\.mp4', r.text)
        if matches:
            results[term] = list(set(matches))[:3]
            print(f"[{term}] Found {len(matches)} links:")
            for m in results[term]:
                print(f"  {m}")
    except Exception as e:
        print(f"[{term}] Error: {e}")
