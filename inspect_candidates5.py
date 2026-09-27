import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("climb_fence1", "https://cdn.pixabay.com/video/2022/04/12/113732-699252948_tiny.mp4"),
    ("climb_fence2", "https://cdn.pixabay.com/video/2019/09/04/26557-358041226_tiny.mp4"),
    ("intruder1", "https://cdn.pixabay.com/video/2022/08/09/127326-738105504_tiny.mp4"),
    ("intruder2", "https://cdn.pixabay.com/video/2017/05/21/9277-218389902_tiny.mp4"),
    ("cctv_night1", "https://cdn.pixabay.com/video/2023/03/12/154384-807362369_tiny.mp4"),
    ("cctv_night2", "https://cdn.pixabay.com/video/2025/06/13/285663_tiny.mp4")
]

os.makedirs("sample_footage/previews5", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews5/{name}.mp4"
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
            img_path = f"sample_footage/previews5/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
