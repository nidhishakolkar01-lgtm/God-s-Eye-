"""
PROJECT TRINETRA-C2 // AUTONOMOUS AIRBORNE VISUAL TRACKING & PID INTERCEPTOR
Combines Real-Time Zero-Lag RTSP Stream, YOLOv8 Neural Perception,
Closed-Loop PID Visual Servoing, Tactical HUD Telemetry, and Section-65B Forensics.
"""

import os
import cv2
import time
import threading
import numpy as np
from ultralytics import YOLO

from core.drone_flight_controller import DroneFlightController
from core.audio_alert import TacticalAudioAlert
from core.evidence_logger import CryptographicEvidenceLogger

# Configure low-latency TCP RTSP transport
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|max_delay;0"
RTSP_URL = "rtsp://192.168.1.1:7070/webcam"


class ZeroLagStreamReader:
    """Non-blocking background RTSP frame grabber discarding stale network buffers."""
    def __init__(self, url):
        self.url = url
        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.lock = threading.Lock()
        self.latest_frame = None
        self.running = True

        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _worker(self):
        while self.running:
            if not self.cap.isOpened():
                time.sleep(0.4)
                self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                continue

            if self.cap.grab():
                ret, frame = self.cap.retrieve()
                if ret and frame is not None:
                    with self.lock:
                        self.latest_frame = frame
            else:
                time.sleep(0.01)

    def read(self):
        with self.lock:
            if self.latest_frame is not None:
                return True, self.latest_frame.copy()
            return False, None

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()


def main():
    print("=======================================================================")
    print("   PROJECT TRINETRA-C2 // AUTONOMOUS DRONE VISUAL SERVOING SENTRY     ")
    print("=======================================================================")
    print(f"[INIT] Establishing optical connection to: {RTSP_URL} ...")

    stream = ZeroLagStreamReader(RTSP_URL)
    flight = DroneFlightController(drone_ip="192.168.1.1", command_port=50000)
    audio = TacticalAudioAlert(cooldown=4.0)
    logger = CryptographicEvidenceLogger(output_dir="evidence")

    # Load YOLO AI model
    print("[AI-CORE] Initializing YOLOv8 Perception Engine...")
    model = YOLO("yolov8n.pt")

    # Wait for first optical frame
    print("[INIT] Syncing with drone camera...")
    for _ in range(25):
        ret, test_f = stream.read()
        if ret and test_f is not None:
            print("[SUCCESS] Optical Sensor Synced & Ready!")
            break
        time.sleep(0.2)

    # Async AI Inference variables
    cached_dets = []
    infer_lock = threading.Lock()
    running = True
    clahe_active = False
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    def ai_inference_worker():
        nonlocal cached_dets, running
        while running:
            ret, frame = stream.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue

            h, w = frame.shape[:2]
            small = cv2.resize(frame, (320, 240))
            results = model.track(small, persist=True, verbose=False, conf=0.28)

            dets = []
            if results and len(results) > 0 and results[0].boxes is not None:
                scale_x = w / 320.0
                scale_y = h / 240.0
                for box in results[0].boxes:
                    xyxy = box.xyxy[0].cpu().numpy()
                    x1 = int(xyxy[0] * scale_x)
                    y1 = int(xyxy[1] * scale_y)
                    x2 = int(xyxy[2] * scale_x)
                    y2 = int(xyxy[3] * scale_y)

                    cls_id = int(box.cls[0].item()) if box.cls is not None else 0
                    cls_name = model.names.get(cls_id, "OBJECT").upper()
                    conf = float(box.conf[0].item()) if box.conf is not None else 0.0
                    track_id = int(box.id[0].item()) if box.id is not None else None

                    dets.append({
                        "bbox": (x1, y1, x2, y2),
                        "class_name": cls_name,
                        "confidence": conf,
                        "track_id": track_id
                    })

            with infer_lock:
                cached_dets = dets

            time.sleep(0.015)

    infer_thread = threading.Thread(target=ai_inference_worker, daemon=True)
    infer_thread.start()

    print("\n" + "="*70)
    print("                    TACTICAL C2 FLIGHT KEYBINDINGS                    ")
    print("="*70)
    print(" [T] AUTO-TAKEOFF          : Arm motors and ascend to auto-hover (1.2m)")
    print(" [L] AUTO-LAND             : Safely descend and disarm motors")
    print(" [A] TOGGLE AI TRACKING    : Engage closed-loop PID Autonomous Visual Tracking")
    print(" [SPACE / K] KILL SWITCH   : INSTANT EMERGENCY MOTOR CUTOFF")
    print(" [C] TOGGLE CLAHE          : Hardware Night-Vision contrast filter")
    print(" [S] SEC-65B SNAPSHOT      : Commit SHA-256 Tamper-Proof Evidence Snapshot")
    print(" [Q / ESC] QUIT            : Land drone & disconnect gracefully")
    print("="*70 + "\n")

    fps_start = time.time()
    frame_count = 0
    fps = 30.0

    sector_info = {
        "id": 5,
        "name": "SECTOR-05 // AIRBORNE DRONE RECON",
        "codename": "TRINETRA-AIRBORNE-E88-05",
        "lat": 31.608,
        "lng": 74.578,
        "mgrs": "43R EQ 5980 9700",
        "type": "AIRBORNE RECON SENTRY // FPV"
    }

    while True:
        ret, raw_frame = stream.read()
        if not ret or raw_frame is None:
            time.sleep(0.005)
            continue

        frame_count += 1
        if frame_count % 20 == 0:
            fps = round(20.0 / (time.time() - fps_start), 1)
            fps_start = time.time()

        # Upscale frame smoothly for crisp HUD display
        h, w = raw_frame.shape[:2]
        if w < 640:
            frame = cv2.resize(raw_frame, (640, int(640 * (h / w))), interpolation=cv2.INTER_LINEAR)
            scale = 640.0 / w
        else:
            frame = raw_frame.copy()
            scale = 1.0

        if clahe_active:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = clahe.apply(l)
            lab = cv2.merge((l, a, b))
            frame = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        fh, fw = frame.shape[:2]
        cx_screen, cy_screen = fw // 2, fh // 2

        with infer_lock:
            current_dets = list(cached_dets)

        # Select primary target: Prioritize PERSON, else largest detected object
        primary_target = None
        for det in current_dets:
            if det["class_name"] == "PERSON":
                primary_target = det
                break
        if not primary_target and current_dets:
            primary_target = current_dets[0]

        # Update PID Visual Servoing
        if primary_target:
            orig_bbox = primary_target["bbox"]
            flight.update_visual_servoing(orig_bbox, w, h)
        else:
            flight.update_visual_servoing(None, w, h)

        telem = flight.get_telemetry()

        # Render Detections & Targeting Crosshairs
        for det in current_dets:
            x1 = int(det["bbox"][0] * scale)
            y1 = int(det["bbox"][1] * scale)
            x2 = int(det["bbox"][2] * scale)
            y2 = int(det["bbox"][3] * scale)

            cls = det["class_name"]
            conf = int(det["confidence"] * 100)
            tid = det.get("track_id", "SYS")
            is_primary = (det == primary_target)

            color = (0, 255, 255) if is_primary else (0, 200, 100)
            if flight.auto_tracking_active and is_primary:
                color = (0, 80, 255)  # Orange lock-on color

            # Military Corner Reticles
            line_len = max(12, min(24, (x2 - x1) // 4))
            cv2.line(frame, (x1, y1), (x1 + line_len, y1), color, 2)
            cv2.line(frame, (x1, y1), (x1, y1 + line_len), color, 2)
            cv2.line(frame, (x2, y1), (x2 - line_len, y1), color, 2)
            cv2.line(frame, (x2, y1), (x2, y1 + line_len), color, 2)
            cv2.line(frame, (x1, y2), (x1 + line_len, y2), color, 2)
            cv2.line(frame, (x1, y2), (x1, y2 - line_len), color, 2)
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, 2)
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, 2)

            label = f"{'LOCK' if is_primary and flight.auto_tracking_active else 'TARGET'}: {cls} [{conf}%]"
            cv2.putText(frame, label, (x1, max(18, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

            # Draw vector tracking line from screen center to primary target
            if is_primary:
                tx = (x1 + x2) // 2
                ty = (y1 + y2) // 2
                cv2.line(frame, (cx_screen, cy_screen), (tx, ty), color, 1, cv2.LINE_AA)
                cv2.circle(frame, (tx, ty), 4, color, -1)

        # Center Crosshairs
        cv2.drawMarker(frame, (cx_screen, cy_screen), (0, 255, 0), cv2.MARKER_CROSS, 26, 1)

        # -------------------------------------------------------------------------
        # TACTICAL TELEMETRY HUD RIBBONS
        # -------------------------------------------------------------------------
        # Top Header Ribbon
        cv2.rectangle(frame, (0, 0), (fw, 32), (10, 14, 18), -1)
        flight_state_label = "MANUAL"
        state_color = (0, 255, 119)
        if telem["emergency_stop"]:
            flight_state_label = "EMERGENCY STOP [KILLED]"
            state_color = (0, 0, 255)
        elif telem["auto_tracking"]:
            flight_state_label = "AUTONOMOUS PID SERVOING [ACTIVE LOCK]"
            state_color = (0, 140, 255)
        elif telem["is_flying"]:
            flight_state_label = "AIRBORNE AUTO-HOVER"
            state_color = (0, 240, 255)

        cv2.putText(frame, f"TRINETRA-C2 // {flight_state_label}", (12, 21),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, state_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS: {fps} | CLAHE: {'ON' if clahe_active else 'OFF'}", (fw - 200, 21),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 119), 1, cv2.LINE_AA)

        # Bottom Flight Command & Telemetry Ribbon
        cv2.rectangle(frame, (0, fh - 40), (fw, fh), (10, 14, 18), -1)
        tele_str = (
            f"YAW: {telem['yaw']} ({telem['yaw_offset_pct']:+0.0f}%) | "
            f"PITCH: {telem['pitch']} ({telem['pitch_offset_pct']:+0.0f}%) | "
            f"THROTTLE: {telem['throttle']} ({telem['throttle_offset_pct']:+0.0f}%) | "
            f"ARMED: {'YES' if telem['is_armed'] else 'NO'}"
        )
        cv2.putText(frame, tele_str, (12, fh - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 240, 255), 1, cv2.LINE_AA)

        # Visual Help Sidebar Overlay
        help_bg = np.zeros((100, 190, 3), dtype=np.uint8)
        cv2.putText(help_bg, "[T] Takeoff  [L] Land", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        cv2.putText(help_bg, "[A] Auto-Track (PID)", (10, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1)
        cv2.putText(help_bg, "[SPACE] Kill Switch", (10, 64), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        cv2.putText(help_bg, "[S] Sec-65B Snapshot", (10, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 0), 1)
        frame[40:140, 10:200] = cv2.addWeighted(frame[40:140, 10:200], 0.3, help_bg, 0.7, 0)

        cv2.imshow("TRINETRA-C2: Autonomous Drone HUD & Flight Interceptor", frame)

        # Keyboard Intercept Loop
        key = cv2.waitKey(1) & 0xFF
        if key in [ord('q'), ord('Q'), 27]:
            break
        elif key in [ord('t'), ord('T')]:
            flight.trigger_takeoff()
        elif key in [ord('l'), ord('L')]:
            flight.trigger_land()
        elif key in [ord('a'), ord('A')]:
            is_active = flight.toggle_autotrack()
            print(f"[C2] Autonomous Visual PID Tracking: {'ENGAGED' if is_active else 'DISENGAGED'}")
        elif key in [ord(' '), ord('k'), ord('K')]:
            flight.trigger_emergency_stop()
        elif key in [ord('c'), ord('C')]:
            clahe_active = not clahe_active
            print(f"[C2] CLAHE Night Vision: {'ON' if clahe_active else 'OFF'}")
        elif key in [ord('s'), ord('S')]:
            snap_path = logger.log_manual_snapshot(
                frame,
                sector_info=sector_info,
                sensor_mode="AIRBORNE_OPTICAL"
            )
            print(f"[SEC-65B] Forensic Snapshot Committed: {snap_path}")

    running = False
    flight.close()
    stream.stop()
    cv2.destroyAllWindows()
    print("[C2] Flight Sentry Session Terminated.")

if __name__ == "__main__":
    main()
