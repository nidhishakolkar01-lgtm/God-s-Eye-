import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
queries = [
    'drone-surveillance',
    'military-drone',
    'night-surveillance',
    'thermal-camera',
    'security-patrol-night',
    'aerial-surveillance',
    'border-security'
]

for q in queries:
    url = f"https://pixabay.com/videos/search/{q}/"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        matches = re.findall(r'https://cdn\.pixabay\.com/video/[^"\'\s]+_tiny\.mp4', r.text)
        print(f"Query '{q}': {len(matches)} videos found")
        for m in list(set(matches))[:2]:
            print(f"  {m}")
    except Exception as e:
        print(f"Error {q}: {e}")
