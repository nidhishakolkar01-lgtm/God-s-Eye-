import cv2
import shutil
from core.detector import TacticalDetector
from core.tripwire import ExclusionPolygonZone
from core.hud_renderer import TacticalHUDRenderer

# Test checkpoint_1.mp4 with tactical HUD
cap = cv2.VideoCapture("sample_footage/previews2/checkpoint_1.mp4")
detector = TacticalDetector(model_weight="yolov8n.pt", conf_thresh=0.25)
zone = ExclusionPolygonZone(persistence_threshold=1)
hud = TacticalHUDRenderer()

# Set zone across the security barricade line in checkpoint_1
# Frame is 540x960
zone.points = [
    (140, 480),
    (380, 220),
    (750, 220),
    (880, 480)
]

# Fast forward to 4 seconds where vehicles & police are active
cap.set(cv2.CAP_PROP_POS_MSEC, 4200)
ret, frame = cap.read()
if ret:
    processed_frame, dets, ms = detector.detect(frame)
    # Check breaches
    breaches = zone.evaluate_detections(dets)
    zone.draw_zone(processed_frame, is_breached=len(breaches)>0)
    final_hud = hud.draw_hud(
        processed_frame,
        detections=dets,
        active_breaches=breaches,
        fps=28.4,
        latency_ms=12.1,
        clahe_on=False,
        muted=False
    )
    cv2.imwrite("sample_footage/checkpoint_godseye_preview.jpg", final_hud)
    shutil.copyfile("sample_footage/checkpoint_godseye_preview.jpg", "C:/Users/nidhi/.gemini/antigravity/brain/d76144da-8b19-430f-b39d-cfecb36a1c42/checkpoint_godseye_preview.jpg")
    print("Checkpoint God's Eye preview saved!")
cap.release()
