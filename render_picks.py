import cv2, os
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

picks = [
    ("thermal1", "sample_footage/previews3/thermal1.mp4"),
    ("border_wall_2", "sample_footage/previews4/border_wall_2.mp4"),
    ("military_base", "sample_footage/previews4/military_base.mp4"),
    ("prison_fence", "sample_footage/previews4/prison_fence.mp4"),
    ("border_cross_3", "sample_footage/previews6/border_cross_3.mp4"),
    ("flir3", "sample_footage/previews_godseye/flir3.mp4")
]

for name, path in picks:
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * 0.4))
    ret, frame = cap.read()
    cap.release()
    if ret and frame is not None:
        res = model(frame, verbose=False, conf=0.25)[0]
        out_f = f"sample_footage/pick_{name}.jpg"
        cv2.imwrite(out_f, res.plot())
        print(f"Saved {out_f}")
