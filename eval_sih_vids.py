import cv2, os
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

vids = [
    "sample_footage/sih_candidate_vids/parth_test.mp4",
    "sample_footage/sih_candidate_vids/riddhi_border.mp4",
    "sample_footage/sih_candidate_vids/raghav_test.mp4"
]

for v in vids:
    cap = cv2.VideoCapture(v)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = total / fps if fps > 0 else 0
    
    base = os.path.basename(v).split(".")[0]
    
    # Grab frames at 25%, 50%, 75%
    for pct in [0.25, 0.5, 0.75]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * pct))
        ret, frame = cap.read()
        if ret and frame is not None:
            res = model(frame, verbose=False, conf=0.25)[0]
            dets = [model.names[int(c)] for c in res.boxes.cls]
            out_img = f"sample_footage/sih_candidate_vids/{base}_{int(pct*100)}.jpg"
            cv2.imwrite(out_img, res.plot())
            print(f"{base} @ {pct*100}%: {w}x{h}, {dur:.1f}s, Dets: {dets[:8]}")
    cap.release()
