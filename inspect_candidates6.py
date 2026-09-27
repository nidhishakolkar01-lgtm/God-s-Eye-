import os
import cv2
import requests

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

urls = [
    ("border_cross_1", "https://cdn.pixabay.com/video/2016/09/13/5072-183299851_tiny.mp4"),
    ("border_cross_2", "https://cdn.pixabay.com/video/2021/02/18/65621-515085097_tiny.mp4"),
    ("border_cross_3", "https://cdn.pixabay.com/video/2016/02/17/2196-155813511_tiny.mp4"),
    ("sec_patrol_1", "https://cdn.pixabay.com/video/2022/09/30/133084-755697289_tiny.mp4"),
    ("sec_patrol_2", "https://cdn.pixabay.com/video/2020/05/03/37946-415263561_tiny.mp4")
]

os.makedirs("sample_footage/previews6", exist_ok=True)

for name, url in urls:
    try:
        mp4_path = f"sample_footage/previews6/{name}.mp4"
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
            img_path = f"sample_footage/previews6/{name}_preview.jpg"
            cv2.imwrite(img_path, frame)
            print(f"{name}: {frame.shape}, Size: {os.path.getsize(mp4_path)//1024} KB")
        cap.release()
    except Exception as e:
        print(f"Error {name}: {e}")
