import requests
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
for term in ['wire-fence', 'barbed-wire', 'security-patrol', 'surveillance-camera']:
    url = f"https://pixabay.com/videos/search/{term}/"
    r = requests.get(url, headers=headers, timeout=10)
    matches = re.findall(r'https://cdn\.pixabay\.com/video/[^"\'\s]+_tiny\.mp4', r.text)
    print(f"Term: {term} -> {len(matches)} matches")
    for m in list(set(matches))[:3]:
        print(f"  {m}")
