import urllib.request
import re
import os

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

queries = [
    'border-patrol',
    'military-patrol',
    'security-camera-fence',
    'surveillance-camera-night',
    'perimeter-fence'
]

os.makedirs('sample_footage/tactical_downloads', exist_ok=True)
count = 0
for q in queries:
    url = f'https://www.pexels.com/search/videos/{q}/'
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8')
            vids = list(set(re.findall(r'https://video-previews\.pexels\.com/[^\"]+?\.mp4', html)))
            print(f"Query: {q} -> Found {len(vids)} MP4s")
            for vurl in vids[:2]:
                fname = f"sample_footage/tactical_downloads/{q}_{count}.mp4"
                print(f"Downloading {fname}...")
                vreq = urllib.request.Request(vurl, headers=headers)
                with urllib.request.urlopen(vreq) as vresp, open(fname, 'wb') as f:
                    f.write(vresp.read())
                count += 1
    except Exception as e:
        print(f"Error querying {q}: {e}")
print(f"Total downloaded: {count}")
