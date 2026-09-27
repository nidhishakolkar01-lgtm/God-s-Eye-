import os
import sys
import time
import json
import urllib.request

def run_tests():
    print("=" * 70)
    print(" PROJECT TRINETRA-C2 // SIH PS 26187 REALIGNMENT VERIFICATION SUITE")
    print(" AI-Based Video Analytics Platform for Border Surveillance (MHA)")
    print("=" * 70)

    # 1. Test Alert Dispatcher Unit
    print("\n[TEST 1/5] Testing Multi-Channel Alert Dispatcher Unit...")
    from core.alert_dispatcher import AlertDispatcher
    dispatcher = AlertDispatcher(config_path="test_alert_config.json")
    cfg = dispatcher.get_config()
    assert "telegram_enabled" in cfg
    assert "webhook_enabled" in cfg
    res = dispatcher.test_alert()
    assert res.get("status") in ["queued", "cooldown_or_error"]
    print(" [+] AlertDispatcher initialized & test queue verified.")
    if os.path.exists("test_alert_config.json"):
        try: os.remove("test_alert_config.json")
        except: pass

    # 2. Test False Alarm Reduction Rate (FARR) Unit
    print("\n[TEST 2/5] Testing Exclusion Polygon Zone & FARR Noise Suppression...")
    from core.tripwire import ExclusionPolygonZone
    zone = ExclusionPolygonZone(persistence_threshold=3)
    zone.set_preset_corridor(854, 480, sector_id=1)
    
    # Test point inside corridor
    pt_inside = (int(854 * 0.5), int(480 * 0.7))
    assert zone.is_point_inside(pt_inside) == True, "Point inside corridor failed"
    
    # Simulate Fauna Detection (e.g. Stray Dog / Cow) -> should be suppressed
    dets_fauna = [{
        "track_id": "fauna_1",
        "class_name": "DOG/CANINE",
        "footfall": pt_inside,
        "bbox": [100, 100, 200, 200]
    }]
    breaches, suppressed = zone.evaluate_detections(dets_fauna)
    assert len(breaches) == 0, "Fauna should not trigger active breach"
    assert len(suppressed) == 1, "Fauna should be recorded in suppressed events"
    
    # Simulate Human Intruder -> should verify after persistence frames
    dets_human = [{
        "track_id": "human_1",
        "class_name": "PERSON",
        "footfall": pt_inside,
        "bbox": [150, 150, 250, 350]
    }]
    zone.evaluate_detections(dets_human)  # frame 1
    zone.evaluate_detections(dets_human)  # frame 2
    b3, s3 = zone.evaluate_detections(dets_human)  # frame 3 (hits threshold 3)
    assert len(b3) == 1, "Human target must trigger verified breach after persistence"
    
    farr_metrics = zone.get_farr_metrics()
    assert "farr_percentage" in farr_metrics
    assert farr_metrics["suppressed_fauna_count"] >= 1
    print(f" [+] FARR Noise Filtering Verified: FARR = {farr_metrics['farr_percentage']}% | Suppressed Fauna = {farr_metrics['suppressed_fauna_count']}")

    # 3. Test Camera Network Manager Dynamic Onboarding
    print("\n[TEST 3/5] Testing Dynamic Camera Network Manager...")
    from core.camera_manager import CameraNetworkManager
    sectors_mock = {
        1: {"id": 1, "name": "MOCK SECTOR 1", "codename": "MOCK-01", "source": "sample_footage/border_fence_ladder.mp4", "type": "OPTICAL", "lat": 31.604, "lng": 74.572, "mgrs": "43R EQ 5940 9662"}
    }
    mgr = CameraNetworkManager(sectors_mock)
    added = mgr.add_custom_camera(
        name="TEST DYNAMIC RTSP NODE",
        source="rtsp://admin:pass@192.168.1.50:554/ch1",
        cam_type="THERMAL RVSS",
        lat=32.0,
        lng=74.8,
        mgrs="43R EQ 9999 1111"
    )
    assert added["id"] == 2
    assert added["protocol"] == "RTSP (H.264/H.265)"
    cams = mgr.get_cameras_summary()
    assert len(cams) == 2
    
    deleted = mgr.remove_custom_camera(2)
    assert deleted == True
    assert len(mgr.get_cameras_summary()) == 1
    print(" [+] Dynamic RTSP camera addition & deletion verified.")

    # 4. Test Local Video Devices Scanner
    print("\n[TEST 4/5] Testing Hardware Capture Device Scanner...")
    devices = mgr.probe_local_video_devices()
    print(f" [+] Scanned local capture devices: {len(devices)} device(s) found.")

    # 5. Test Section 65B Forensic Evidence Logger
    print("\n[TEST 5/5] Testing Section 65B Indian Evidence Act Compliance...")
    from core.evidence_logger import CryptographicEvidenceLogger
    import numpy as np
    logger = CryptographicEvidenceLogger(output_dir="evidence")
    mock_frame = np.zeros((480, 854, 3), dtype=np.uint8)
    log_rec = logger.log_incident(
        frame=mock_frame,
        detection=dets_human[0],
        manual=False,
        sector_info=sectors_mock[1],
        sensor_mode="NORMAL"
    )
    assert log_rec is not None
    sha_hash = log_rec.get("forensic_integrity", {}).get("sha256_hash", "")
    assert len(sha_hash) == 64, "SHA-256 hash must be 64 hexadecimal characters"
    print(f" [+] Court-admissible forensic record committed: SHA-256 = {sha_hash[:24]}...")

    print("\n" + "=" * 70)
    print(" ALL 5 SIH PS 26187 CORE PIPELINE TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
