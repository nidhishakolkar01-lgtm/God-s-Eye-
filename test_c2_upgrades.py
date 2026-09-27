import sys
import numpy as np
import cv2

print("[TEST 1/5] Testing MultiSpectralSensor...")
from core.sensor_pipeline import MultiSpectralSensor
sensor = MultiSpectralSensor()
blank = np.zeros((480, 640, 3), dtype=np.uint8)

# Test all modes
for mode in ["NORMAL", "NVG_P43", "FLIR_IRONBOW", "FLIR_WHOT", "FLIR_BHOT"]:
    sensor.set_mode(mode)
    out = sensor.process(blank)
    assert out.shape == (480, 640, 3), f"Shape mismatch in {mode}"
print("  -> MultiSpectralSensor OK (All 5 spectral modes verified)")

print("[TEST 2/5] Testing Sentry Scope Mask...")
sensor.toggle_scope_mask()
masked = sensor.process(blank)
assert masked.shape == (480, 640, 3)
sensor.toggle_scope_mask()
print("  -> Sentry Scope Mask OK")

print("[TEST 3/5] Testing KinematicTracker & Breach ETA...")
from core.tracker_analytics import KinematicTracker
kin = KinematicTracker()
# Simulate target moving towards fence at (100, 200) -> (100, 220)
fence = [(0, 300), (640, 300)]
res1 = kin.update(1, (100, 100), fence)
import time; time.sleep(0.08)
res2 = kin.update(1, (100, 150), fence)
assert res2["speed"] > 0
print(f"  -> KinematicTracker OK (Calculated speed: {res2['speed']} px/s, Heading: {res2['heading_deg']} deg)")

print("[TEST 4/5] Testing GeoTelemetry MGRS & Recon Math...")
from core.geo_telemetry import GeoTelemetry
# Amritsar Wagah border
mgrs = GeoTelemetry.latlon_to_mgrs(31.604, 74.572)
recon = GeoTelemetry.compute_recon_metrics()
assert "43R" in mgrs or "44R" in mgrs
print(f"  -> GeoTelemetry OK (Amritsar Wagah MGRS: {mgrs}, GSD: {recon['gsd_cm_px']} cm/px, {recon['niirs_rating']})")

print("[TEST 5/5] Testing Cryptographic Evidence Logger & Section 65B Certificate...")
from core.evidence_logger import CryptographicEvidenceLogger
logger = CryptographicEvidenceLogger(output_dir="evidence")
entry = logger.log_incident(
    blank, 
    {"track_id": 42, "class_name": "PERSON", "confidence": 0.94, "bbox": [10, 10, 50, 100], "footfall": [30, 100]},
    manual=True,
    sector_info={"name": "SECTOR-01 // PUNJAB PERIMETER WALL", "mgrs": mgrs},
    sensor_mode="NVG_P43"
)
assert entry is not None
html_cert = logger.generate_certificate_html(entry["incident_uuid"])
assert "SECTION 65B(4)" in html_cert
assert entry["forensic_integrity"]["sha256_hash"] in html_cert
print(f"  -> Evidence Logger & Section 65B Cert OK (UUID: {entry['incident_uuid']})")

print("\n=======================================================")
print(" ALL 5/5 C2 SYSTEMS UPGRADE TESTS PASSED SUCCESSFULLY! ")
print("=======================================================\n")
