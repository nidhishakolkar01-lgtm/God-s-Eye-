import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("drone1", "https://cdn.pixabay.com/video/2023/11/19/189819-887078801_tiny.mp4"),
    ("drone2", "https://cdn.pixabay.com/video/2025/12/21/323513_tiny.mp4"),
    ("thermal1", "https://cdn.pixabay.com/video/2022/01/03/103309-662525601_tiny.mp4"),
    ("thermal2", "https://cdn.pixabay.com/video/2018/11/06/19164-299997213_tiny.mp4"),
    ("patrol_night", "https://cdn.pixabay.com/video/2017/09/20/12127-235051444_tiny.mp4"),
    ("aerial1", "https://cdn.pixabay.com/video/2020/04/09/35573-407595474_tiny.mp4"),
    ("border_sec", "https://cdn.pixabay.com/video/2022/06/22/121776-724719714_tiny.mp4")
]

os.makedirs("sample_footage/previews3", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews3/{name}.mp4"
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
            img_path = f"sample_footage/previews3/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
