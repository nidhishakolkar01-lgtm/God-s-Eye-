import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("wire_fence1", "https://cdn.pixabay.com/video/2022/06/19/120762-724673329_tiny.mp4"),
    ("patrol_sec3", "https://cdn.pixabay.com/video/2024/09/09/230545_tiny.mp4"),
    ("patrol_sec4", "https://cdn.pixabay.com/video/2026/06/17/359023_tiny.mp4"),
    ("surv_cam1", "https://cdn.pixabay.com/video/2022/01/03/103300-662114635_tiny.mp4"),
    ("surv_cam2", "https://cdn.pixabay.com/video/2024/03/24/205468-926967226_tiny.mp4")
]

os.makedirs("sample_footage/previews8", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews8/{name}.mp4"
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
            img_path = f"sample_footage/previews8/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
