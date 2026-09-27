import cv2
import shutil
from core.detector import TacticalDetector
from core.tripwire import ExclusionPolygonZone
from core.hud_renderer import TacticalHUDRenderer

cap = cv2.VideoCapture("sample_footage/border_fence_ladder.mp4")
detector = TacticalDetector(model_weight="yolov8n.pt", conf_thresh=0.25)
zone = ExclusionPolygonZone(persistence_threshold=1)
hud = TacticalHUDRenderer()

# Exclusion zone specifically on the upper ridge of the border wall (the sterile breach zone)
zone.points = [
    (150, 420),
    (420, 160),
    (600, 120),
    (750, 190),
    (450, 470)
]

# Run 10 frames to initialize ByteTrack tracker smoothly
cap.set(cv2.CAP_PROP_POS_MSEC, 23500)
for _ in range(12):
    ret, frame = cap.read()
    if not ret:
        break
    processed_frame, dets, ms = detector.track(frame)

if ret:
    breaches = zone.evaluate_detections(dets)
    zone.draw_zone(processed_frame, is_breached=len(breaches)>0)
    final_hud = hud.draw_hud(
        processed_frame,
        detections=dets,
        active_breaches=breaches,
        fps=28.7,
        latency_ms=11.8,
        clahe_on=False,
        muted=False
    )
    cv2.imwrite("sample_footage/border_fence_tracked_preview.jpg", final_hud)
    print(f"Tracked preview saved! Active breaches: {len(breaches)}")
cap.release()
