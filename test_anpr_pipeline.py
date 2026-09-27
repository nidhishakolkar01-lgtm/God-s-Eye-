import cv2
import numpy as np
import time
from core.anpr_engine import ANPREngine
from core.detector import TacticalDetector

print("--- TEST 1: ANPREngine Unit Verification ---")
engine = ANPREngine()
print(f"Active watchlist items: {len(engine.watchlist)}")

# Test Normalization
raw_inputs = ["JK02B1892", "PB-02-AK-4921", "dl 8c am 1102", "HR26DQ5551", "1K02B1892"]
for r in raw_inputs:
    norm, conf = engine.normalize_plate_text(r)
    cat, risk, msg, model, is_alert = engine.query_watchlist(norm)
    print(f"Input: {r:<15} -> Cleaned: {norm:<15} | Cat: {cat:<22} | Alert: {is_alert}")

print("\n--- TEST 2: ANPR Extraction & OCR on Synthetic Plate ---")
v_crop = np.ones((200, 300, 3), dtype=np.uint8) * 60
cv2.rectangle(v_crop, (75, 140), (225, 180), (240, 240, 240), -1)
cv2.rectangle(v_crop, (75, 140), (225, 180), (0, 0, 0), 2)
cv2.putText(v_crop, "JK 02 B 1892", (82, 168), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

plate_crop, rel_box = engine.extract_plate_crop(v_crop)
print(f"Extracted plate ROI box: {rel_box}")

engine._ocr_worker(track_id=101, plate_crop=plate_crop, vehicle_type="VEHICLE", rel_box=rel_box)
cached = engine.vehicle_cache.get(101)
print("Cached ANPR Result:", cached)

print("\n--- TEST 3: TacticalDetector on Checkpoint Frame ---")
det = TacticalDetector()
frame = cv2.imread("checkpoint_frame_sample.jpg")
proc_frame, dets, faces, lat = det.detect(frame)
print(f"Detections count: {len(dets)} | Latency: {lat:.1f}ms")
vehicle_dets = [d for d in dets if d["class_name"] in ["VEHICLE", "TRUCK", "HEAVY_VEHICLE", "MOTORCYCLE"]]
print(f"Vehicles tracked: {len(vehicle_dets)}")
for vd in vehicle_dets:
    tid = vd.get("track_id")
    cname = vd.get("class_name")
    anpr_plate = vd.get("anpr", {}).get("plate", "NONE")
    print(f"  Track #{tid}: {cname} at {vd['bbox']} -> ANPR: {anpr_plate}")
print("\nALL ANPR TESTS COMPLETED SUCCESSFULLY!")
