import cv2, os
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

for v in ["sample_footage/special_forces.webm", "sample_footage/military_intel.webm"]:
    cap = cv2.VideoCapture(v)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = total / fps if fps > 0 else 0
    base = os.path.basename(v).split(".")[0]
    
    for pct in [0.2, 0.4, 0.6, 0.8]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * pct))
        ret, frame = cap.read()
        if ret and frame is not None:
            res = model(frame, verbose=False, conf=0.25)[0]
            dets = [model.names[int(c)] for c in res.boxes.cls]
            out_img = f"sample_footage/{base}_{int(pct*100)}.jpg"
            cv2.imwrite(out_img, res.plot())
            print(f"{base} @ {pct*100}%: {w}x{h}, {dur:.1f}s -> {dets}")
    cap.release()
