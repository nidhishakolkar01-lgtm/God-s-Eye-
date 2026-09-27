import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("fence1", "https://cdn.pixabay.com/video/2021/11/09/95193-644716871_tiny.mp4"),
    ("fence2", "https://cdn.pixabay.com/video/2020/01/28/31654-387926643_tiny.mp4"),
    ("fence3", "https://cdn.pixabay.com/video/2020/12/10/58846-489663384_tiny.mp4"),
    ("barbed1", "https://cdn.pixabay.com/video/2025/11/24/317899_tiny.mp4"),
    ("barbed2", "https://cdn.pixabay.com/video/2019/10/25/28276-368763972_tiny.mp4")
]

os.makedirs("sample_footage/previews", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews/{name}.mp4"
        r = requests.get(url, headers=headers, timeout=15)
        with open(mp4_path, "wb") as f:
            f.write(r.content)
        
        cap = cv2.VideoCapture(mp4_path)
        ret, frame = cap.read()
        if ret:
            img_path = f"sample_footage/previews/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
