import requests
import re
import json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
for term in ['security-fence', 'border-fence', 'surveillance-camera', 'barbed-wire']:
    url = f"https://pixabay.com/videos/search/{term}/"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Term: {term}, Status: {r.status_code}")
        # Look for video URLs in page source
        matches = re.findall(r'(https://cdn\.pixabay\.com/video/[^"\'\s]+\.mp4\?[^"\'\s]+)', r.text)
        if not matches:
            matches = re.findall(r'(https://cdn\.pixabay\.com/video/[^"\'\s]+\.mp4)', r.text)
        print(f"  Matches: {len(matches)}")
        for m in list(set(matches))[:3]:
            print(f"  -> {m}")
    except Exception as e:
        print(f"Error {term}: {e}")
