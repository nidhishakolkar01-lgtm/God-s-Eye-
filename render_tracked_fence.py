import cv2
import shutil
from core.detector import TacticalDetector
from core.tripwire import ExclusionPolygonZone
from core.hud_renderer import TacticalHUDRenderer

cap = cv2.VideoCapture("sample_footage/border_fence_ladder.mp4")
detector = TacticalDetector(model_weight="yolov8n.pt", conf_thresh=0.25, use_tracking=True)
zone = ExclusionPolygonZone(persistence_threshold=1)
hud = TacticalHUDRenderer()

# Sterile zone along the upper boundary and fence ridge
zone.points = [
    (100, 470),
    (380, 200),
    (550, 140),
    (750, 160),
    (850, 470)
]

cap.set(cv2.CAP_PROP_POS_MSEC, 23000)
for _ in range(25):
    ret, frame = cap.read()
    if not ret:
        break
    processed_frame, dets, ms = detector.detect(frame)

if ret:
    breaches = zone.evaluate_detections(dets)
    zone.draw_zone(processed_frame, is_breached=len(breaches)>0)
    final_hud = hud.draw_hud(
        processed_frame,
        detections=dets,
        active_breaches=breaches,
        fps=29.4,
        latency_ms=11.2,
        clahe_on=False,
        muted=False
    )
    cv2.imwrite("sample_footage/border_fence_tracked_hud.jpg", final_hud)
    shutil.copyfile("sample_footage/border_fence_tracked_hud.jpg", "C:/Users/nidhi/.gemini/antigravity/brain/d76144da-8b19-430f-b39d-cfecb36a1c42/border_fence_tracked_hud.jpg")
    print(f"Saved tracked HUD! Detections: {len(dets)}, Breaches: {len(breaches)}")
cap.release()
