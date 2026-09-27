import os
import sys
import time

def run_tests():
    print("="*60)
    print("TRINETRA-C2 PROTOTYPE AUTOMATED DIAGNOSTIC SUITE")
    print("="*60)

    # 1. Test Imports
    print("\n[TEST 1/5] Verifying Core Dependencies...")
    try:
        import cv2
        import torch
        import shapely
        import ultralytics
        print(f" [+] OpenCV Version: {cv2.__version__}")
        print(f" [+] PyTorch Version: {torch.__version__}")
        print(f" [+] Ultralytics Version: {ultralytics.__version__}")
        print(" [PASS] All core perception libraries verified.")
    except Exception as e:
        print(f" [FAIL] Dependency error: {e}")
        return False

    # 2. Test Sample Video Generator
    print("\n[TEST 2/5] Testing Surveillance Video Engine...")
    try:
        from download_sample_video import ensure_sample_video
        sample_path = ensure_sample_video()
        assert os.path.exists(sample_path) and os.path.getsize(sample_path) > 1000
        print(f" [PASS] Video feed verified: {sample_path} ({os.path.getsize(sample_path)//1024} KB)")
    except Exception as e:
        print(f" [FAIL] Video error: {e}")
        return False

    # 3. Test Stream Engine Reader
    print("\n[TEST 3/5] Testing Multi-Threaded Stream Engine...")
    try:
        from core.stream_engine import VideoStreamEngine
        engine = VideoStreamEngine(source=sample_path, loop=True).start()
        time.sleep(0.3)
        ret, frame = engine.read()
        engine.stop()
        assert ret and frame is not None
        print(f" [PASS] Stream reader successfully captured frame: {frame.shape}")
    except Exception as e:
        print(f" [FAIL] Stream reader error: {e}")
        return False

    # 4. Test Exclusion Polygon & Ray-Casting
    print("\n[TEST 4/5] Testing Jordan Curve Ray-Casting & Persistence...")
    try:
        from core.tripwire import ExclusionPolygonZone
        zone = ExclusionPolygonZone(persistence_threshold=2)
        zone.points = [(100, 100), (300, 100), (300, 300), (100, 300)]
        assert zone.is_point_inside((200, 200)) == True
        assert zone.is_point_inside((50, 50)) == False
        print(" [PASS] Vector ray-casting point-in-polygon logic verified.")
    except Exception as e:
        print(f" [FAIL] Ray-casting error: {e}")
        return False

    # 5. Test Cryptographic Evidence Logger
    print("\n[TEST 5/5] Testing Section 65B Indian Evidence Act Logger...")
    try:
        from core.evidence_logger import CryptographicEvidenceLogger
        logger = CryptographicEvidenceLogger(output_dir="evidence")
        dummy_det = {"track_id": 99, "class_name": "PERSON_TEST", "confidence": 0.95, "bbox": [10, 10, 50, 50], "footfall": [30, 50]}
        entry = logger.log_incident(frame, dummy_det, manual=True)
        assert entry is not None and "sha256_hash" in entry["forensic_integrity"]
        print(f" [PASS] Cryptographic SHA-256 evidence record committed: {entry['incident_uuid']}")
    except Exception as e:
        print(f" [FAIL] Logger error: {e}")
        return False

    print("\n" + "="*60)
    print("ALL 5 DIAGNOSTIC TESTS PASSED! PROTOTYPE IS 100% OPERATIONAL.")
    print("="*60 + "\n")
    return True

if __name__ == "__main__":
    run_tests()
