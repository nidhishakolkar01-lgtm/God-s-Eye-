import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture("sample_footage/baltic_border.webm")
fps = cap.get(cv2.CAP_PROP_FPS) or 25

timestamps = [10, 30, 50, 75, 100, 130]
for ts in timestamps:
    cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
    ret, frame = cap.read()
    if ret and frame is not None:
        res = model(frame, verbose=False, conf=0.2)[0]
        out_f = f"sample_footage/baltic_{ts}s.jpg"
        cv2.imwrite(out_f, res.plot())
        print(f"Baltic {ts}s: {[model.names[int(c)] for c in res.boxes.cls]}")
cap.release()
