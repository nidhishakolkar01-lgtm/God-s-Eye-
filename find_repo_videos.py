import urllib.request
import json
import re

headers = {'User-Agent': 'Mozilla/5.0'}

# Search GitHub repositories related to border surveillance and intrusion detection
repos = [
    "https://api.github.com/repos/hasan-sayeed/Perimeter-Intrusion-Detection-System/contents",
    "https://api.github.com/repos/computervisioneng/ai-virtual-fence/contents",
    "https://api.github.com/repos/ultralytics/ultralytics/contents",
    "https://api.github.com/repos/spmallick/learnopencv/contents"
]

for r in repos:
    try:
        req = urllib.request.Request(r, headers=headers)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(r, "SUCCESS, items:", len(data))
            for item in data:
                if any(item.get('name', '').endswith(ext) for ext in ['.mp4', '.avi', '.mov']):
                    print("  -> Video:", item.get('name'), item.get('download_url'))
    except Exception as e:
        print(r, "Failed:", e)
