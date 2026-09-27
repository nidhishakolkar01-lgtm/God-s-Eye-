import cv2, os, glob
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

all_vids = sorted(glob.glob("sample_footage/**/*.mp4", recursive=True) + glob.glob("sample_footage/**/*.webm", recursive=True))

print(f"Total videos to scan: {len(all_vids)}")

results = []
for v in all_vids:
    # Skip previews ending in preview.mp4 if duplicates
    cap = cv2.VideoCapture(v)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    dur = total_frames / fps if fps > 0 else 0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    if dur < 2 or w == 0 or h == 0:
        cap.release()
        continue
    
    # Sample at 25%, 50%, 75%
    detected_classes = set()
    sample_frames = [int(total_frames * 0.25), int(total_frames * 0.50), int(total_frames * 0.75)]
    for fno in sample_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fno)
        ret, frame = cap.read()
        if ret and frame is not None:
            res = model(frame, verbose=False, conf=0.3)[0]
            for c in res.boxes.cls:
                detected_classes.add(model.names[int(c)])
    cap.release()
    
    results.append((v, f"{w}x{h}", f"{dur:.1f}s", list(detected_classes)))

for v, res, dur, dets in results:
    if any(k in dets for k in ['person', 'car', 'truck', 'bus']):
        print(f"TACTICAL CANDIDATE: {v} | {res} | {dur} | Detections: {dets}")
