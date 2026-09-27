import os
import cv2
import time
import argparse

from core.stream_engine import VideoStreamEngine
from core.detector import TacticalDetector
from core.tripwire import ExclusionPolygonZone
from core.hud_renderer import TacticalHUDRenderer
from core.audio_alert import TacticalAudioAlert
from core.evidence_logger import CryptographicEvidenceLogger
from download_sample_video import ensure_sample_video

SECTORS = {
    1: {"name": "SECTOR-01 // BORDER PERIMETER FENCE", "source": "sample_footage/border_fence_ladder.mp4", "preset": 1},
    2: {"name": "SECTOR-02 // THERMAL RVSS NIGHT SENTRY", "source": "sample_footage/rvss_border_crossing.mp4", "preset": 2},
    3: {"name": "SECTOR-03 // FORWARD SECURITY CHECKPOST", "source": "sample_footage/previews2/checkpoint_1.mp4", "preset": 3},
    4: {"name": "SECTOR-04 // LIVE OPTICAL SENSOR", "source": 0, "preset": 4}
}

def main():
    parser = argparse.ArgumentParser(description="TRINETRA-C2 Autonomous Border Surveillance Prototype")
    parser.add_argument("--source", type=str, default=None, help="Custom video source: 0 for webcam, or path to MP4/RTSP stream")
    parser.add_argument("--sector", type=int, default=1, choices=[1, 2, 3, 4], help="Initial Camera Sector (1: Border Fence, 2: RVSS Thermal, 3: Checkpost, 4: Live)")
    parser.add_argument("--weights", type=str, default="yolov8n.pt", help="YOLO model weights file")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence detection threshold")
    parser.add_argument("--headless", action="store_true", help="Run in headless verification mode (no GUI window)")
    parser.add_argument("--web", action="store_true", help="Launch World Monitor-inspired Tactical C2 Web Dashboard on http://localhost:8080")
    args = parser.parse_args()

    if args.web:
        import uvicorn
        from server import app
        port = 8080
        print("\n" + "="*70)
        print(" PROJECT TRINETRA-C2 // TACTICAL C2 WEB DASHBOARD")
        print(" Sponsoring Authority: Ministry of Home Affairs (MHA) | PS 26187")
        print(f" Server Endpoint: http://localhost:{port}")
        print("="*70 + "\n")
        try:
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
        except OSError:
            port = 8081
            print(f"\n[NOTICE] Port 8080 occupied. Launching automatically on http://localhost:{port}...\n")
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
        return

    active_sector_id = args.sector
    if args.source is not None:
        video_source = args.source
        sector_name = "CUSTOM // SURVEILLANCE FEED"
    else:
        sec_info = SECTORS.get(active_sector_id, SECTORS[1])
        video_source = sec_info["source"]
        sector_name = sec_info["name"]

    print(f"\n{'='*70}")
    print(" PROJECT TRINETRA-C2 // AUTONOMOUS TACTICAL SURVEILLANCE C2")
    print(" Sponsoring Authority: Ministry of Home Affairs (MHA) | PS 26187")
    print(f"{'='*70}")
    print(f" [•] Active Sector:      {sector_name}")
    print(f" [•] Video Stream Feed:  {video_source}")
    print(f" [•] Perception Core:    {args.weights} (Confidence: {args.conf})")
    print(f" [•] Evidence Protocol:  Section 65B Indian Evidence Act Compliance")
    print(f"{'='*70}\n")

    # Initialize Modules
    stream = VideoStreamEngine(source=video_source, loop=True).start()
    detector = TacticalDetector(model_weight=args.weights, conf_thresh=args.conf, use_tracking=True)
    zone = ExclusionPolygonZone(persistence_threshold=3)
    hud = TacticalHUDRenderer()
    audio = TacticalAudioAlert(cooldown=3.5)
    logger = CryptographicEvidenceLogger(output_dir="evidence")

    # Wait for first frame to set default polygon
    time.sleep(0.5)
    ret, frame = stream.read()
    if not ret or frame is None:
        print("[ERROR] Could not read video stream. Exiting.")
        stream.stop()
        return

    h, w = frame.shape[:2]
    zone.set_preset_corridor(w, h, sector_id=active_sector_id)

    # Mouse Callback for Interactive Polygon Drawing
    drawing = False
    window_name = "TRINETRA-C2 // COMMAND & CONTROL HUD (MHA PS-26187)"

    def mouse_callback(event, x, y, flags, param):
        nonlocal drawing
        if event == cv2.EVENT_LBUTTONDOWN:
            if not drawing:
                zone.clear()
                drawing = True
            zone.add_point((x, y))
            print(f"[TRINETRA-C2] Added Polygon Vertex: ({x}, {y})")
        elif event == cv2.EVENT_RBUTTONDOWN:
            drawing = False
            print(f"[TRINETRA-C2] Sealed Exclusion Polygon with {len(zone.points)} vertices.")

    if not args.headless:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
        cv2.setMouseCallback(window_name, mouse_callback)

    # FPS Calculation
    fps_start_time = time.time()
    fps_counter = 0
    current_fps = 30.0

    paused = False
    print("\n[READY] Tactical Sentry Active. Press 'Q' to quit.\n")

    try:
        while True:
            if not paused:
                ret, frame = stream.read()
                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

                # Run Perception Core (YOLO + CLAHE)
                processed_frame, detections, latency_ms = detector.detect(frame)

                # Evaluate Detections against Exclusion Polygon
                active_breaches = zone.evaluate_detections(detections)
                is_breached = len(active_breaches) > 0

                # Trigger Spoken Tactical Klaxon if incursion detected
                if is_breached:
                    audio.trigger_breach_alert(intruder_count=len(active_breaches))
                    for breach in active_breaches:
                        logger.log_incident(frame, breach, manual=False)

                # Render Tactical Exclusion Zone Polygon
                zone.draw_zone(processed_frame, is_breached=is_breached)

                # Calculate Smooth FPS
                fps_counter += 1
                if time.time() - fps_start_time >= 1.0:
                    current_fps = fps_counter / (time.time() - fps_start_time)
                    fps_counter = 0
                    fps_start_time = time.time()

                # Render Military Tactical HUD Overlay
                final_hud_frame = hud.draw_hud(
                    processed_frame, 
                    detections=detections, 
                    active_breaches=active_breaches,
                    fps=current_fps, 
                    latency_ms=latency_ms, 
                    clahe_on=detector.clahe_enabled,
                    muted=audio.muted,
                    sector_label=sector_name
                )

                if args.headless:
                    # In headless mode, run 30 frames and log summary
                    if fps_counter > 25:
                        print(f"[HEADLESS TEST PASSED] Sector: {sector_name}, FPS: {current_fps:.1f}, Latency: {latency_ms:.1f}ms, Detections: {len(detections)}")
                        break
                    continue

                cv2.imshow(window_name, final_hud_frame)

            # Keyboard Hotkey Controls
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:  # Q or ESC
                print("[TRINETRA-C2] Shutdown Signal Received.")
                break
            elif key in [ord('1'), ord('2'), ord('3'), ord('4')]:
                new_sec = int(chr(key))
                if new_sec in SECTORS and new_sec != active_sector_id:
                    print(f"\n[TRINETRA-C2] Switching to Sector {new_sec}...")
                    stream.stop()
                    active_sector_id = new_sec
                    sec_info = SECTORS[new_sec]
                    video_source = sec_info["source"]
                    sector_name = sec_info["name"]
                    stream = VideoStreamEngine(source=video_source, loop=True).start()
                    time.sleep(0.4)
                    s_ret, s_frame = stream.read()
                    if s_ret and s_frame is not None:
                        sh, sw = s_frame.shape[:2]
                        zone.set_preset_corridor(sw, sh, sector_id=active_sector_id)
                    print(f"[TRINETRA-C2] Sector {new_sec} ONLINE: {sector_name}\n")
            elif key == ord('c'):             # C: Toggle CLAHE Night Boost
                detector.toggle_clahe()
            elif key == ord('z'):             # Z: Reset Exclusion Zone
                print("[TRINETRA-C2] Custom Polygon Drawing Mode Active. Click to add points, Right-click to seal.")
                zone.clear()
                drawing = True
            elif key == ord('m'):             # M: Mute audio
                audio.toggle_mute()
            elif key == ord('s'):             # S: Manual Evidence Capture
                if len(detections) > 0:
                    logger.log_incident(frame, detections[0], manual=True)
                else:
                    logger.log_incident(frame, {"class_name": "MANUAL_SWEEP"}, manual=True)
            elif key == 32:                   # SPACE: Pause
                paused = not paused
                print("[TRINETRA-C2] Stream " + ("PAUSED" if paused else "RESUMED"))

    finally:
        stream.stop()
        if not args.headless:
            cv2.destroyAllWindows()
        print("[TRINETRA-C2] Sentry Core Terminated Gracefully.")

if __name__ == "__main__":
    main()
