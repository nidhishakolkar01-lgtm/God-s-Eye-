import urllib.request
import cv2
import os

url = "https://upload.wikimedia.org/wikipedia/commons/1/19/Lithuania_Boosts_NATO%E2%80%99s_Baltics_Border_Defenses_With_Eye_on_Russia.webmhd.webm"
dst = "sample_footage/baltic_border.webm"

print("Downloading border defense clip...")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        # read first 8MB
        data = resp.read(8 * 1024 * 1024)
        with open(dst, "wb") as f:
            f.write(data)
    print("Downloaded:", os.path.getsize(dst))
    
    cap = cv2.VideoCapture(dst)
    # Grab frames across the clip
    for sec in [2, 5, 10, 15, 20]:
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite(f"sample_footage/baltic_frame_{sec}s.jpg", frame)
            print(f"Saved baltic_frame_{sec}s.jpg: {frame.shape}")
    cap.release()
except Exception as e:
    print("Error:", e)
