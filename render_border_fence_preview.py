import cv2
import shutil
from core.detector import TacticalDetector
from core.tripwire import ExclusionPolygonZone
from core.hud_renderer import TacticalHUDRenderer

cap = cv2.VideoCapture("sample_footage/border_fence_ladder.mp4")
detector = TacticalDetector(model_weight="yolov8n.pt", conf_thresh=0.3)
zone = ExclusionPolygonZone(persistence_threshold=1)
hud = TacticalHUDRenderer()

# Frame size: 854x480
# Set exclusion zone right on top of the border wall / fence where the climber is scaling!
# Border fence runs roughly from (0, 420) to (760, 110)
zone.points = [
    (320, 200),
    (480, 140),
    (780, 480),
    (440, 480)
]

# Fast forward to 24 seconds where the intruder is scaling the fence
cap.set(cv2.CAP_PROP_POS_MSEC, 24000)
ret, frame = cap.read()
if ret:
    processed_frame, dets, ms = detector.detect(frame)
    breaches = zone.evaluate_detections(dets)
    zone.draw_zone(processed_frame, is_breached=len(breaches)>0)
    final_hud = hud.draw_hud(
        processed_frame,
        detections=dets,
        active_breaches=breaches,
        fps=29.1,
        latency_ms=11.4,
        clahe_on=False,
        muted=False
    )
    cv2.imwrite("sample_footage/border_fence_godseye_preview.jpg", final_hud)
    print(f"Saved border_fence_godseye_preview.jpg! Breaches detected: {len(breaches)}")
cap.release()
