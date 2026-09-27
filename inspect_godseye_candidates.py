import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("flir1", "https://cdn.pixabay.com/video/2024/07/25/223161_tiny.mp4"),
    ("flir2", "https://cdn.pixabay.com/video/2020/01/03/30862-382770830_tiny.mp4"),
    ("flir3", "https://cdn.pixabay.com/video/2024/06/29/218665_tiny.mp4"),
    ("night1", "https://cdn.pixabay.com/video/2022/08/17/128118-740854486_tiny.mp4"),
    ("night2", "https://cdn.pixabay.com/video/2021/10/13/91998-631504261_tiny.mp4"),
    ("drone_track1", "https://cdn.pixabay.com/video/2022/08/19/128362-741176851_tiny.mp4")
]

os.makedirs("sample_footage/previews_godseye", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews_godseye/{name}.mp4"
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
            img_path = f"sample_footage/previews_godseye/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
