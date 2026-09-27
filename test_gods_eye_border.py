import cv2
from core.detector import TacticalDetector
from core.gods_eye_engine import GodsEyeEngine

det = TacticalDetector()
engine = GodsEyeEngine()

cap = cv2.VideoCapture('sample_footage/border_fence_ladder.mp4')
cap.set(cv2.CAP_PROP_POS_FRAMES, 350)
ret, frame = cap.read()
if ret:
    proc_frame, dets, lat = det.detect(frame)
    print(f'Detected {len(dets)} targets on the ladder/fence!')
    hud_frame = engine.render_gods_eye_hud(
        proc_frame,
        detections=dets,
        active_breaches=dets[:1],
        fps=28.5,
        latency_ms=lat,
        sector_label="SECTOR-01 // PUNJAB PERIMETER WALL",
        mgrs="43R EQ 5940 9662"
    )
    cv2.imwrite("gods_eye_border_test.jpg", hud_frame)
    print("[OK] Rendered gods_eye_border_test.jpg successfully!")
cap.release()
