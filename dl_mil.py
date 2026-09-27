import urllib.request

urls = [
    ("special_forces.webm", "https://upload.wikimedia.org/wikipedia/commons/5/5c/Special_Forces_Conduct_Training_DOD_100067169.webm"),
    ("military_intel.webm", "https://upload.wikimedia.org/wikipedia/commons/d/d9/719th_Military_Intelligence_Battalion_at_Yawolsan%2C_South_Korea_%281000117%29.webm")
]

headers = {"User-Agent": "Mozilla/5.0"}

for fname, u in urls:
    dest = f"sample_footage/{fname}"
    print(f"Downloading {fname}...")
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        print(f"Saved {dest}")
    except Exception as e:
        print(f"Error {fname}: {e}")
