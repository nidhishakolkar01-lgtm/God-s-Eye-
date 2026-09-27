import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("border_patrol_1", "https://cdn.pixabay.com/video/2022/11/20/139788-773444420_tiny.mp4"),
    ("border_patrol_2", "https://cdn.pixabay.com/video/2021/12/19/101975-658840454_tiny.mp4"),
    ("night_vision_1", "https://cdn.pixabay.com/video/2020/06/30/43496-434353332_tiny.mp4"),
    ("checkpoint_1", "https://cdn.pixabay.com/video/2024/02/19/201109-914557927_tiny.mp4"),
    ("checkpoint_2", "https://cdn.pixabay.com/video/2021/10/23/93008-638414220_tiny.mp4")
]

os.makedirs("sample_footage/previews2", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews2/{name}.mp4"
        r = requests.get(url, headers=headers, timeout=15)
        with open(mp4_path, "wb") as f:
            f.write(r.content)
        
        cap = cv2.VideoCapture(mp4_path)
        # grab frame at 1 sec mark
        cap.set(cv2.CAP_PROP_POS_MSEC, 1500)
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
        if ret:
            img_path = f"sample_footage/previews2/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
