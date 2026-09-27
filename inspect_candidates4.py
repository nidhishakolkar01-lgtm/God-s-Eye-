import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("prison_fence", "https://cdn.pixabay.com/video/2017/07/23/10783-226624891_tiny.mp4"),
    ("military_base", "https://cdn.pixabay.com/video/2021/02/17/65521-514501899_tiny.mp4"),
    ("night_vision", "https://cdn.pixabay.com/video/2017/08/30/11722-231759069_tiny.mp4"),
    ("security_gate", "https://cdn.pixabay.com/video/2021/08/25/86343-592491757_tiny.mp4"),
    ("border_wall_1", "https://cdn.pixabay.com/video/2019/01/04/20466-309694567_tiny.mp4"),
    ("border_wall_2", "https://cdn.pixabay.com/video/2022/12/02/141443-777657268_tiny.mp4")
]

os.makedirs("sample_footage/previews4", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews4/{name}.mp4"
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
            img_path = f"sample_footage/previews4/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
