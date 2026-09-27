import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
clips = [
    ("surv_cam1", "sample_footage/previews8/surv_cam1.mp4"),
    ("sec_1", "sample_footage/previews7/sec_1.mp4"),
    ("sec_2", "sample_footage/previews7/sec_2.mp4"),
    ("intruder2", "sample_footage/previews5/intruder2.mp4")
]

for name, p in clips:
    cap = cv2.VideoCapture(p)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 20)
    ret, frame = cap.read()
    cap.release()
    if ret:
        res = model(frame, verbose=False)[0]
        cv2.imwrite(f"sample_footage/{name}_inspect.jpg", res.plot())
        print(f"Saved {name}")
