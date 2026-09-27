import urllib.request
import os

sources = [
    ("parth_test.mp4", "https://raw.githubusercontent.com/parthameshingawale-eng/ibvap/main/test.mp4"),
    ("riddhi_border.mp4", "https://raw.githubusercontent.com/Riddhi23133/IBVAP_Border_surveillance/main/src/imports/vid-20260902-wa0051-htvexnlm-odbrqxhc-whrpl9ti_9yB5BghV.mp4"),
    ("raghav_test.mp4", "https://raw.githubusercontent.com/raghavpli515/Sensitive-area-Intrusion-detection-system/main/backend/samples/test_video.mp4")
]

os.makedirs("sample_footage/sih_candidate_vids", exist_ok=True)

headers = {"User-Agent": "Mozilla/5.0"}
for fname, url in sources:
    dest = f"sample_footage/sih_candidate_vids/{fname}"
    print(f"Downloading {fname}...")
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        size_mb = os.path.getsize(dest) / (1024*1024)
        print(f"Downloaded {dest}: {size_mb:.2f} MB")
    except Exception as e:
        print(f"Failed {fname}: {e}")
