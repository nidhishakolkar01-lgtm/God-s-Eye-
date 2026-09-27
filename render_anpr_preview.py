import cv2
import numpy as np
from core.hud_renderer import TacticalHUDRenderer
from core.gods_eye_engine import GodsEyeEngine

hud = TacticalHUDRenderer()
godseye = GodsEyeEngine()

# Load checkpoint frame
frame = cv2.imread("checkpoint_frame_sample.jpg")
if frame is None:
    frame = np.zeros((540, 960, 3), dtype=np.uint8)

h, w = frame.shape[:2]

# Simulated vehicles with ANPR detections
dets = [
    {
        "track_id": 41,
        "class_id": 2,
        "class_name": "VEHICLE",
        "confidence": 0.94,
        "bbox": (440, 380, 595, 535),
        "footfall": (517, 535),
        "center": (517, 457),
        "kinematics": {"velocity": (-8.0, 2.0), "speed": 45.0, "is_imminent": False},
        "anpr": {
            "track_id": 41,
            "plate": "JK 02 B 1892",
            "confidence": 96.8,
            "category": "STOLEN VEHICLE",
            "risk": "CRITICAL THREAT // LEVEL 1",
            "alert_msg": "CRITICAL: Stolen Bolero Camper reported moving towards border checkpost. Engage interceptors.",
            "vehicle_model": "MAHINDRA BOLERO CAMPER",
            "is_alert": True,
            "vehicle_type": "VEHICLE",
            "plate_bbox": (42, 85, 75, 24)
        }
    },
    {
        "track_id": 18,
        "class_id": 5,
        "class_name": "HEAVY_VEHICLE",
        "confidence": 0.88,
        "bbox": (290, 190, 485, 395),
        "footfall": (387, 395),
        "center": (387, 292),
        "kinematics": {"velocity": (2.0, 1.0), "speed": 18.0, "is_imminent": False},
        "anpr": {
            "track_id": 18,
            "plate": "HR 26 DQ 5551",
            "confidence": 98.2,
            "category": "AUTHORIZED PATROL",
            "risk": "FRIENDLY // BSF QRT",
            "alert_msg": "VERIFIED: BSF Quick Reaction Team unit. Transit cleared.",
            "vehicle_model": "MARUTI GYPSY MIL-SPEC",
            "is_alert": False,
            "vehicle_type": "HEAVY_VEHICLE",
            "plate_bbox": (65, 125, 70, 20)
        }
    }
]

# 1. Render Tactical Standard HUD
hud_frame = frame.copy()
hud_frame = hud.draw_hud(
    hud_frame,
    detections=dets,
    active_breaches=[],
    fps=30.2,
    latency_ms=16.8,
    clahe_on=False,
    sensor_mode="NORMAL",
    mgrs="43R FN 2891 7412",
    gsd_text="GSD: 5.4cm | NIIRS-8",
    muted=False,
    sector_label="SECTOR-03 // JAMMU FORWARD CHECKPOST",
    is_godeye_mode=False
)

# 2. Render God's Eye Cyber HUD
godeye_frame = frame.copy()
godeye_frame = godseye.render_gods_eye_hud(
    godeye_frame,
    detections=dets,
    active_breaches=[],
    fps=30.5,
    latency_ms=16.5,
    sector_label="SECTOR-03 // JAMMU FORWARD CHECKPOST",
    mgrs="43R FN 2891 7412",
    zone_obj=None,
    faces=[]
)

# Save preview images
cv2.imwrite("anpr_tactical_hud_preview.jpg", hud_frame)
cv2.imwrite("anpr_godseye_preview.jpg", godeye_frame)
# Also copy to artifact directory for presentation
import shutil
shutil.copy("anpr_tactical_hud_preview.jpg", r"C:\Users\nidhi\.gemini\antigravity\brain\59c4d52a-f093-43af-9f3b-c8fd12950cb2\anpr_tactical_hud_preview.jpg")
shutil.copy("anpr_godseye_preview.jpg", r"C:\Users\nidhi\.gemini\antigravity\brain\59c4d52a-f093-43af-9f3b-c8fd12950cb2\anpr_godseye_preview.jpg")
print("Rendered and copied ANPR preview screenshots successfully!")
