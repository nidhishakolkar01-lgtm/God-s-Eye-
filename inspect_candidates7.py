import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("sec_1", "https://cdn.pixabay.com/video/2021/02/06/64295-509565171_tiny.mp4"),
    ("sec_2", "https://cdn.pixabay.com/video/2016/10/24/6095-188704564_tiny.mp4"),
    ("sec_3", "https://cdn.pixabay.com/video/2021/10/18/92491-637274790_tiny.mp4"),
    ("patrol_1", "https://cdn.pixabay.com/video/2025/03/20/266383_tiny.mp4"),
    ("patrol_2", "https://cdn.pixabay.com/video/2026/07/02/361816_tiny.mp4")
]

os.makedirs("sample_footage/previews7", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews7/{name}.mp4"
        r = requests.get(url, headers=headers, timeout=15)
        with open(mp4_path, "wb") as f:
            f.write(r.content)
        
        cap = cv2.VideoCapture(mp4_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, 1500)
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
        if ret:
            img_path = f"sample_footage/previews7/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
