import cv2
from ultralytics import YOLO

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture("sample_footage/rvss_border_crossing.mp4")
fps = cap.get(cv2.CAP_PROP_FPS) or 25

for sec in [15, 25, 35, 42]:
    cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
    ret, frame = cap.read()
    if ret:
        res = model(frame, verbose=False, conf=0.3)[0]
        dets = [f"{model.names[int(c)]}:{float(conf):.2f}" for c, conf in zip(res.boxes.cls, res.boxes.conf)]
        out_f = f"sample_footage/rvss_{sec}s.jpg"
        cv2.imwrite(out_f, res.plot())
        print(f"RVSS at {sec}s: {len(dets)} detections -> {dets[:6]}")
cap.release()
