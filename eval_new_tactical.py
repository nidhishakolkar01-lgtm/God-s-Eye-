import cv2, os, shutil
from ultralytics import YOLO

model = YOLO("yolov8n.pt")

mapping = [
    ("sample_footage/G68Lr2LAjYs.mp4", "sample_footage/rvss_border_crossing.mp4"),
    ("sample_footage/hQN5alpt3Jw.mp4", "sample_footage/flir_thermal_perimeter.mp4"),
    ("sample_footage/enV2BRAIpDg.mp4", "sample_footage/border_fence_ladder.mp4")
]

for src, dst in mapping:
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"Renamed {src} -> {dst}")

for name, path in [("rvss", "sample_footage/rvss_border_crossing.mp4"),
                   ("flir", "sample_footage/flir_thermal_perimeter.mp4"),
                   ("ladder", "sample_footage/border_fence_ladder.mp4")]:
    if not os.path.exists(path):
        continue
    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    dur = total / fps if fps > 0 else 0
    print(f"\n{name} ({path}): {w}x{h}, {fps:.1f}fps, {dur:.1f}s ({total} frames)")
    
    # Extract multiple frames
    for pct in [0.2, 0.4, 0.6, 0.8]:
        fnum = int(total * pct)
        cap.set(cv2.CAP_PROP_POS_FRAMES, fnum)
        ret, frame = cap.read()
        if ret and frame is not None:
            res = model(frame, verbose=False, conf=0.25)[0]
            dets = [f"{model.names[int(c)]}:{float(conf):.2f}" for c, conf in zip(res.boxes.cls, res.boxes.conf)]
            out_img = f"sample_footage/{name}_pct{int(pct*100)}.jpg"
            cv2.imwrite(out_img, res.plot())
            print(f"  Frame @ {pct*100:.0f}% ({fnum}): Dets ({len(dets)}) -> {dets[:6]}")
    cap.release()
