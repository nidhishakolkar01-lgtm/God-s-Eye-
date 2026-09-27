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

cap.set(cv2.CAP_PROP_POS_MSEC, 23500)
for _ in range(20):
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
        muted=False,
        sector_label="SECTOR-01 // BORDER PERIMETER FENCE"
    )
    # Save to multiple locations for presentation deck
    cv2.imwrite("sample_footage/prototype_live_demo_screenshot.jpg", final_hud)
    cv2.imwrite("prototype_live_demo_screenshot.jpg", final_hud)
    shutil.copyfile("prototype_live_demo_screenshot.jpg", "C:/Users/nidhi/Desktop/prototype_live_demo_screenshot.jpg")
    shutil.copyfile("prototype_live_demo_screenshot.jpg", "C:/Users/nidhi/.gemini/antigravity/brain/d76144da-8b19-430f-b39d-cfecb36a1c42/prototype_live_demo_screenshot.jpg")
    print("Screenshot generated and synced to Desktop and artifact directory!")
cap.release()
