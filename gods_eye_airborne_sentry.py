"""
PROJECT TRINETRA-C2 // AUTONOMOUS AIRBORNE SENTRY & CLOSED-LOOP PID INTERCEPTOR (E88 PLUS)
Features:
 - Persistent Biometric Identity Latching (Holds Face ID & Target Lock during in-flight motion & vibrations)
 - Multi-Scale 640px Super-Sampling Inference (Detects distant persons, faces, and objects at 3-5m range)
 - Autonomous Closed-Loop PID Visual Servoing (Auto-Yaw, Altitude Hold, Standoff Distance)
 - Dual Neural Perception: Official YOLOv8n (80 COCO Classes) + OpenCV YuNet (Face) + SFace (128D Biometrics)
 - Dual-Camera Split Demuxer: Automatically extracts crystal-clear Front FPV Camera
 - Real-Time Optical Super-Clarity & De-blur ISP (Unsharp Mask + LAB CLAHE)
 - Fast & Furious 7 God's Eye Tactical HUD: Rotating Stadiametric Radar, Target Brackets, Dossier Badges
 - Section-65B Indian Evidence Act Cryptographic Forensic Ledger (SHA-256)
 - Tactical Audio Klaxon & Voice Alert Synthesis
"""

import os
import cv2
import time
import math
import argparse
import threading
import numpy as np
from typing import List, Dict, Tuple, Optional
from ultralytics import YOLO

from core.face_engine import FaceRecognitionEngine
from core.drone_flight_controller import DroneFlightController
from core.ground_station_bridge import GroundStationRFBridge
from core.audio_alert import TacticalAudioAlert
from core.evidence_logger import CryptographicEvidenceLogger

# Force low-latency TCP RTSP transport
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|max_delay;0"
DEFAULT_RTSP_URL = "rtsp://192.168.1.1:7070/webcam"


class OpticalEnhancer:
    """Real-Time Tactical Image Enhancement & Anti-Jello De-Blur Engine."""
    def __init__(self):
        self.mode = 1  # 1: TACTICAL CRISP, 2: ULTRA EDGE, 3: NVG GREEN, 0: RAW
        self.clahe = cv2.createCLAHE(clipLimit=2.8, tileGridSize=(8, 8))
        self.modes_desc = {
            0: "RAW SENSOR (UNFILTERED)",
            1: "TACTICAL CRISP (DE-BLUR + CLAHE)",
            2: "ULTRA EDGE (LAPLACIAN HIGH-PASS)",
            3: "NVG NIGHT-VISION (PHOSPHOR GREEN)"
        }

    def cycle_mode(self) -> str:
        self.mode = (self.mode + 1) % 4
        return self.modes_desc[self.mode]

    def enhance(self, frame: np.ndarray) -> np.ndarray:
        if frame is None or frame.size == 0 or self.mode == 0:
            return frame

        # Mode 1: Tactical Crisp (Unsharp Mask + LAB CLAHE)
        if self.mode == 1:
            gaussian = cv2.GaussianBlur(frame, (0, 0), 2.0)
            crisp = cv2.addWeighted(frame, 1.6, gaussian, -0.6, 0)
            lab = cv2.cvtColor(crisp, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l_enhanced = self.clahe.apply(l)
            return cv2.cvtColor(cv2.merge((l_enhanced, a, b)), cv2.COLOR_LAB2BGR)

        # Mode 2: Ultra Edge (Laplacian High-Pass)
        elif self.mode == 2:
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
            sharpened = cv2.filter2D(frame, -1, kernel)
            lab = cv2.cvtColor(sharpened, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l_enhanced = self.clahe.apply(l)
            return cv2.cvtColor(cv2.merge((l_enhanced, a, b)), cv2.COLOR_LAB2BGR)

        # Mode 3: NVG Phosphor Night Vision
        elif self.mode == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            clahe_gray = self.clahe.apply(gray)
            nvg = np.zeros_like(frame)
            nvg[:, :, 1] = clahe_gray
            nvg[:, :, 0] = (clahe_gray * 0.25).astype(np.uint8)
            return nvg

        return frame


class LensDemuxer:
    """Handles Dual-Lens Split Streams, extracting clean forward FPV lens."""
    def __init__(self):
        self.mode = 1  # 1: FRONT LENS ONLY, 2: FULL COMPOSITE, 3: BOTTOM LENS
        self.modes_desc = {
            0: "AUTO LENS DETECT",
            1: "FRONT LENS (FPV RECON)",
            2: "FULL DUAL SPLIT (RAW)",
            3: "BOTTOM LENS (OPTICAL FLOW)"
        }

    def cycle_mode(self) -> str:
        self.mode = (self.mode + 1) % 4
        return self.modes_desc[self.mode]

    def demux(self, raw_frame: np.ndarray) -> np.ndarray:
        if raw_frame is None or raw_frame.size == 0:
            return raw_frame
        h, w = raw_frame.shape[:2]
        if self.mode == 1 or (self.mode == 0 and h > w * 0.85):
            return raw_frame[0 : h // 2, 0 : w]
        elif self.mode == 3:
            return raw_frame[h // 2 : h, 0 : w]
        return raw_frame


class TacticalStreamReader:
    """Zero-Lag Multi-Source Frame Grabber with Auto-Reconnect."""
    def __init__(self, initial_source="rtsp://192.168.1.1:7070/webcam"):
        self.source = initial_source
        self.cap: Optional[cv2.VideoCapture] = None
        self.lock = threading.Lock()
        self.latest_frame: Optional[np.ndarray] = None
        self.running = True
        self.is_connected = False
        self.source_label = str(initial_source)
        self._init_capture()

        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()

    def _init_capture(self):
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass

        src = self.source
        if isinstance(src, str) and src.isdigit():
            src = int(src)

        if isinstance(src, int):
            self.source_label = f"WEBCAM #{src}"
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(src)
        else:
            str_s = str(src).lower()
            if "rtsp://" in str_s:
                self.source_label = "E88 DRONE FPV [TCP RTSP:7070]"
                self.cap = cv2.VideoCapture(str(src), cv2.CAP_FFMPEG)
            elif "http://" in str_s or "https://" in str_s:
                self.source_label = "IP CAMERA"
                self.cap = cv2.VideoCapture(str(src), cv2.CAP_FFMPEG)
            else:
                self.source_label = f"SAMPLE FOOTAGE ({os.path.basename(str(src))})"
                self.cap = cv2.VideoCapture(str(src))

        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.is_connected = True
        else:
            self.is_connected = False

    def switch_source(self, new_source):
        with self.lock:
            self.source = new_source
            self._init_capture()
            print(f"[STREAM] Switched source to: {self.source_label}")

    def _worker(self):
        while self.running:
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.3)
                with self.lock:
                    self._init_capture()
                continue

            if self.cap.grab():
                ret, frame = self.cap.retrieve()
                if ret and frame is not None:
                    with self.lock:
                        self.latest_frame = frame
                        self.is_connected = True
                else:
                    time.sleep(0.01)
            else:
                if isinstance(self.source, str) and not self.source.startswith(("rtsp://", "http://", "https://")):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    time.sleep(0.02)
                else:
                    self.is_connected = False
                    time.sleep(0.02)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        with self.lock:
            if self.latest_frame is not None:
                return True, self.latest_frame.copy()
            return False, None

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()


def main():
    parser = argparse.ArgumentParser(description="TRINETRA-C2 Autonomous Airborne Recon Sentry & Closed-Loop PID Interceptor")
    parser.add_argument("--source", type=str, default=DEFAULT_RTSP_URL, help="Video stream source")
    parser.add_argument("--conf", type=float, default=0.09, help="YOLO confidence threshold (0.05 - 0.30)")
    args = parser.parse_args()

    print("=" * 80)
    print("   PROJECT TRINETRA-C2 // AUTONOMOUS AIRBORNE SENTRY & CLOSED-LOOP PID INTERCEPTOR   ")
    print("=" * 80)
    print(f"[INIT] Video Stream Target: {args.source}")

    enhancer = OpticalEnhancer()
    demuxer = LensDemuxer()
    stream = TacticalStreamReader(args.source)
    flight = DroneFlightController(drone_ip="192.168.1.1", command_port=50000)
    rf_bridge = GroundStationRFBridge()
    audio = TacticalAudioAlert(cooldown=4.0)
    logger = CryptographicEvidenceLogger(output_dir="evidence")

    # Load Dual Neural Perception Engines
    print("[AI-CORE] Initializing YuNet & SFace Biometric Face Recognition Engine [Airborne Mode]...")
    face_engine = FaceRecognitionEngine(
        models_dir="models",
        known_faces_dir="known_faces",
        cosine_threshold=0.28
    )

    yolo_weights = "yolov8n.pt"
    print(f"[AI-CORE] Initializing Official YOLOv8 Perception Model [{yolo_weights}]...")
    yolo_model = YOLO(yolo_weights)

    # Synchronize Stream
    print("[INIT] Synchronizing with optical sensor...")
    synced = False
    for _ in range(30):
        ret, test_f = stream.read()
        if ret and test_f is not None:
            print(f"[SUCCESS] Optical Sensor Synced! Raw Resolution: {test_f.shape[1]}x{test_f.shape[0]}")
            synced = True
            break
        time.sleep(0.15)

    # Persistent Biometric Identity & Track History Database
    track_identity_memory: Dict[int, Dict] = {}
    cached_dets: List[Dict] = []
    cached_faces: List[Dict] = []
    infer_lock = threading.Lock()
    running = True
    selected_target_idx = 0
    inference_fps = 0.0
    anim_tick = 0

    # Asynchronous AI Worker Thread
    def ai_perception_worker():
        nonlocal cached_dets, cached_faces, running, inference_fps, track_identity_memory
        last_infer_t = time.time()
        infer_count = 0

        while running:
            ret, raw_frame = stream.read()
            if not ret or raw_frame is None:
                time.sleep(0.01)
                continue

            # 1. Demux & Optical De-blur Enhancement
            demuxed = demuxer.demux(raw_frame)
            enhanced_input = enhancer.enhance(demuxed)
            fh, fw = enhanced_input.shape[:2]

            # 2. Multi-Scale Super-Sampling for Distant Faces & Objects
            # Upscale 2x if native resolution is low (<600px) so distant targets are 4x larger in feature space
            if fw < 600:
                scale_up = 2.0
                super_sampled = cv2.resize(enhanced_input, (int(fw * scale_up), int(fh * scale_up)), interpolation=cv2.INTER_CUBIC)
            else:
                scale_up = 1.0
                super_sampled = enhanced_input

            # 3. YuNet Face Detection & SFace Recognition (on Super-Sampled Frame)
            detected_faces = face_engine.recognize_faces(super_sampled)
            # Map face bounding boxes back to native frame coordinates
            if scale_up != 1.0 and detected_faces:
                for f in detected_faces:
                    bx, by, bw, bh = f["bbox"]
                    f["bbox"] = (int(bx / scale_up), int(by / scale_up), int(bw / scale_up), int(bh / scale_up))
                    if "landmarks" in f:
                        f["landmarks"] = [(int(lx / scale_up), int(ly / scale_up)) for lx, ly in f["landmarks"]]

            # 4. YOLOv8 Multi-Class Object Tracking (High-Sensitivity Airborne Mode)
            results = yolo_model.track(
                super_sampled,
                persist=True,
                verbose=False,
                conf=args.conf,
                imgsz=640,
                tracker="bytetrack.yaml"
            )

            dets = []
            now_t = time.time()

            if results and len(results) > 0 and results[0].boxes is not None:
                for box in results[0].boxes:
                    xyxy = box.xyxy[0].cpu().numpy().astype(float)
                    if scale_up != 1.0:
                        xyxy /= scale_up

                    x1, y1, x2, y2 = [int(v) for v in xyxy]
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(fw, x2), min(fh, y2)

                    cls_id = int(box.cls[0].item()) if box.cls is not None else 0
                    raw_cls = yolo_model.names.get(cls_id, "OBJECT").upper()
                    conf = float(box.conf[0].item()) if box.conf is not None else 0.0
                    track_id = int(box.id[0].item()) if box.id is not None else 1

                    # Match face with Person body
                    associated_face = None
                    if raw_cls == "PERSON" and detected_faces:
                        for f in detected_faces:
                            bx, by, bw, bh = f["bbox"]
                            if (x1 - 30 <= bx <= x2 + 30) and (y1 - 30 <= by <= y2 + 30):
                                associated_face = f
                                break

                    # PERSISTENT IDENTITY LATCHING:
                    # If this track was identified in a previous frame, remember their identity!
                    if associated_face and associated_face["is_known"]:
                        track_identity_memory[track_id] = {
                            "name": associated_face["name"],
                            "confidence": associated_face["confidence_pct"] / 100.0,
                            "is_known": True,
                            "last_seen": now_t
                        }
                    elif associated_face:
                        if track_id not in track_identity_memory or not track_identity_memory[track_id]["is_known"]:
                            track_identity_memory[track_id] = {
                                "name": associated_face["name"],
                                "confidence": associated_face["confidence_pct"] / 100.0,
                                "is_known": False,
                                "last_seen": now_t
                            }

                    # Check persistent identity cache
                    mem = track_identity_memory.get(track_id)
                    display_label = raw_cls
                    target_type = "TACTICAL OBJECT"
                    is_hvt = False

                    if mem and raw_cls == "PERSON":
                        display_label = mem["name"]
                        target_type = "PERSONNEL" if mem["is_known"] else "UNKNOWN SUSPECT"
                        is_hvt = mem["is_known"]
                    elif associated_face:
                        display_label = associated_face["name"]
                        target_type = "PERSONNEL" if associated_face["is_known"] else "UNKNOWN SUSPECT"
                        is_hvt = associated_face["is_known"]
                    elif raw_cls == "PERSON":
                        target_type = "HUMAN ENTITY"
                    elif raw_cls in ["CELL PHONE", "REMOTE"]:
                        target_type = "COMMS / TRIGGER"
                    elif raw_cls in ["BACKPACK", "SUITCASE", "HANDBAG"]:
                        target_type = "PAYLOAD / CONTRABAND"
                    elif raw_cls in ["CAR", "TRUCK", "BUS", "MOTORCYCLE", "BICYCLE"]:
                        target_type = "MOTORIZED VEHICLE"
                    elif raw_cls in ["BOTTLE", "CUP", "KNIFE", "SCISSORS"]:
                        target_type = "EQUIPMENT / ITEM"

                    dets.append({
                        "bbox": (x1, y1, x2, y2),
                        "class_name": display_label,
                        "raw_class": raw_cls,
                        "target_type": target_type,
                        "confidence": conf,
                        "track_id": track_id,
                        "associated_face": associated_face,
                        "is_hvt": is_hvt,
                        "is_face_only": False
                    })

                    if raw_cls == "PERSON":
                        audio.trigger_breach_alert(intruder_count=1)

            # 5. Add Isolated Faces not bound to YOLO Person boxes
            for f in detected_faces:
                bx, by, bw, bh = f["bbox"]
                fx1, fy1 = max(0, bx), max(0, by)
                fx2, fy2 = min(fw, bx + bw), min(fh, by + bh)

                already_associated = any(
                    d.get("associated_face") is not None and d["associated_face"]["bbox"] == f["bbox"]
                    for d in dets
                )

                if not already_associated:
                    dets.append({
                        "bbox": (fx1, fy1, fx2, fy2),
                        "class_name": f["name"],
                        "raw_class": "FACE",
                        "target_type": "BIOMETRIC FACE",
                        "confidence": f["confidence_pct"] / 100.0,
                        "track_id": hash(f["name"]) % 900 + 100,
                        "associated_face": f,
                        "is_hvt": f["is_known"],
                        "is_face_only": True
                    })

            # Clean expired track memories (>60 seconds)
            expired_ids = [tid for tid, m in track_identity_memory.items() if now_t - m["last_seen"] > 60.0]
            for tid in expired_ids:
                del track_identity_memory[tid]

            with infer_lock:
                cached_dets = dets
                cached_faces = detected_faces

            infer_count += 1
            if time.time() - last_infer_t >= 1.0:
                inference_fps = round(infer_count / (time.time() - last_infer_t), 1)
                infer_count = 0
                last_infer_t = time.time()

            time.sleep(0.01)

    infer_thread = threading.Thread(target=ai_perception_worker, daemon=True)
    infer_thread.start()

    print("\n" + "=" * 80)
    print("                 AUTONOMOUS AIRBORNE MISSION KEYBINDINGS              ")
    print("=" * 80)
    print(" [SPACE]     : ENGAGE / DISENGAGE AUTONOMOUS PID VISUAL TRACKING")
    print(" [T]         : AUTONOMOUS TAKEOFF & ALTITUDE HOVER HOLD")
    print(" [L]         : AUTONOMOUS LAND & MOTOR DISARM")
    print(" [X]         : EMERGENCY INSTANT MOTOR CUT (KILL SWITCH)")
    print(" [D]         : Cycle Lens Mode (Front FPV / Dual Split / Downward Lens)")
    print(" [E]         : Cycle De-Blur Filter (Crisp / Ultra Edge / NVG / Raw)")
    print(" [TAB]       : Cycle Target Lock-On")
    print(" [V]         : Switch Video Source (Drone RTSP <-> Webcam <-> Sample)")
    print(" [S]         : Commit Section-65B SHA-256 Tamper-Proof Evidence Snapshot")
    print(" [M]         : Mute / Unmute Audio Sirens & Tactical Voice Alerts")
    print(" [Q / ESC]   : Disconnect & Safely Terminate Mission")
    print("=" * 80 + "\n")

    fps_start = time.time()
    frame_count = 0
    display_fps = 30.0

    sector_info = {
        "id": 5,
        "name": "SECTOR-05 // AIRBORNE DRONE RECON",
        "codename": "TRINETRA-AIRBORNE-E88-05",
        "lat": 31.608,
        "lng": 74.578,
        "mgrs": "43R EQ 5980 9700",
        "type": "AUTONOMOUS AIRBORNE RECON SENTINEL"
    }

    source_toggle_idx = 0
    available_sources = [
        DEFAULT_RTSP_URL,
        0,
        "sample_footage/previews_godseye/drone_track1.mp4"
    ]

    cv2.namedWindow("TRINETRA-C2: Autonomous Airborne Sentry & PID Interceptor", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("TRINETRA-C2: Autonomous Airborne Sentry & PID Interceptor", 1024, 768)

    while True:
        anim_tick = (anim_tick + 1) % 3600
        ret, raw_frame = stream.read()
        if not ret or raw_frame is None:
            standby = np.zeros((600, 800, 3), dtype=np.uint8)
            cv2.putText(standby, "PROJECT TRINETRA // AUTONOMOUS AIRBORNE SENTRY", (30, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 240, 255), 2, cv2.LINE_AA)
            cv2.putText(standby, f"SEARCHING OPTICAL LINK: {stream.source_label} ...", (30, 290),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 119), 1, cv2.LINE_AA)
            cv2.putText(standby, "Turn ON E88 Drone and connect PC WiFi to 'WIFI-UFO-XXXXXX'", (30, 340),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
            cv2.putText(standby, "Press [V] to switch source to Webcam or Sample Video.", (30, 390),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255), 1, cv2.LINE_AA)
            cv2.imshow("TRINETRA-C2: Autonomous Airborne Sentry & PID Interceptor", standby)
            key = cv2.waitKey(30) & 0xFF
            if key in [ord('q'), ord('Q'), 27]:
                break
            elif key in [ord('v'), ord('V')]:
                source_toggle_idx = (source_toggle_idx + 1) % len(available_sources)
                stream.switch_source(available_sources[source_toggle_idx])
            continue

        frame_count += 1
        if frame_count % 15 == 0:
            display_fps = round(15.0 / max(0.001, time.time() - fps_start), 1)
            fps_start = time.time()

        # 1. Lens Demuxer & Optical Enhancer
        demuxed_frame = demuxer.demux(raw_frame)
        enhanced_frame = enhancer.enhance(demuxed_frame)

        # 2. HD Canvas
        orig_h, orig_w = enhanced_frame.shape[:2]
        hud_w = max(960, orig_w)
        hud_h = int(hud_w * (orig_h / float(orig_w)))
        frame = cv2.resize(enhanced_frame, (hud_w, hud_h), interpolation=cv2.INTER_CUBIC)
        scale_x = hud_w / float(orig_w)
        scale_y = hud_h / float(orig_h)

        fh, fw = frame.shape[:2]
        cx_screen, cy_screen = fw // 2, fh // 2

        with infer_lock:
            current_dets = list(cached_dets)
            current_faces = list(cached_faces)

        # 3. Target Selection
        primary_target = None
        if current_dets:
            if selected_target_idx >= len(current_dets):
                selected_target_idx = 0

            def target_priority(det):
                if det.get("is_hvt"):
                    return 0
                if det.get("raw_class") == "FACE" or det.get("associated_face"):
                    return 1
                if det.get("raw_class") == "PERSON":
                    return 2
                if det.get("raw_class") in ["KNIFE", "SCISSORS", "BACKPACK", "CELL PHONE"]:
                    return 3
                return 4

            sorted_dets = sorted(current_dets, key=target_priority)
            primary_target = sorted_dets[selected_target_idx]

        # 4. Execute Autonomous Closed-Loop Visual Servoing Loop
        if primary_target and flight.auto_tracking_active:
            flight.update_visual_servoing(
                primary_target["bbox"],
                frame_w=orig_w,
                frame_h=orig_h
            )

        tele = flight.get_telemetry()
        if flight.auto_tracking_active:
            rf_bridge.set_flight_setpoints(tele["roll"], tele["pitch"], tele["throttle"], tele["yaw"], tele["flags"])

        # 5. Flight Director Guidance & Standoff Telemetry
        director_cue = "FLIGHT DIRECTOR: SCANNING AIRSPACE // NO ACTIVE TARGET"
        cue_color = (0, 240, 255)
        est_distance = 0.0
        yaw_deg = 0.0
        pitch_deg = 0.0
        target_cx, target_cy = cx_screen, cy_screen

        if primary_target:
            bx1 = int(primary_target["bbox"][0] * scale_x)
            by1 = int(primary_target["bbox"][1] * scale_y)
            bx2 = int(primary_target["bbox"][2] * scale_x)
            by2 = int(primary_target["bbox"][3] * scale_y)

            target_cx = (bx1 + bx2) // 2
            target_cy = (by1 + by2) // 2
            box_h = max(1, by2 - by1)
            box_w = max(1, bx2 - bx1)

            dx = target_cx - cx_screen
            dy = target_cy - cy_screen
            yaw_deg = round((dx / float(cx_screen)) * 32.5, 1)
            pitch_deg = round((-dy / float(cy_screen)) * 24.0, 1)

            focal_px = fh * 0.85
            if primary_target.get("is_face_only") or primary_target.get("raw_class") == "FACE":
                nominal_h = 0.22
            elif primary_target.get("raw_class") == "PERSON":
                nominal_h = 1.70
            elif primary_target.get("raw_class") in ["CAR", "TRUCK", "BUS"]:
                nominal_h = 1.50
            else:
                nominal_h = 0.35

            est_distance = round(max(0.3, min(15.0, (nominal_h * focal_px) / float(box_h))), 1)

            if yaw_deg > 3.0:
                yaw_str = f"YAW RIGHT +{abs(yaw_deg):.1f} deg"
            elif yaw_deg < -3.0:
                yaw_str = f"YAW LEFT -{abs(yaw_deg):.1f} deg"
            else:
                yaw_str = "BEARING LOCKED [0 deg]"

            if pitch_deg > 4.0:
                pitch_str = f"ELEVATE +{abs(pitch_deg):.1f} deg"
            elif pitch_deg < -4.0:
                pitch_str = f"DESCEND -{abs(pitch_deg):.1f} deg"
            else:
                pitch_str = "LEVEL"

            if est_distance > 2.8:
                dist_str = f"ADVANCE ({est_distance}m)"
            elif est_distance < 1.0:
                dist_str = f"RETREAT // STANDOFF BREACH ({est_distance}m)"
            else:
                dist_str = f"HOLD STANDOFF ({est_distance}m)"

            target_name = primary_target["class_name"]
            status_prefix = "[AUTONOMOUS PID LOCK]" if flight.auto_tracking_active else "[DIRECTOR MANUAL]"
            director_cue = f"{status_prefix} {yaw_str} | {pitch_str} | {dist_str} | LOCK: {target_name}"

            if abs(yaw_deg) <= 3.0 and 1.0 <= est_distance <= 2.8:
                cue_color = (0, 255, 120)
            elif est_distance < 1.0:
                cue_color = (0, 70, 255)
            else:
                cue_color = (0, 200, 255)

        # ---------------------------------------------------------------------
        # RENDER FAST & FURIOUS 7 GOD'S EYE CYBER HUD
        # ---------------------------------------------------------------------
        # Concentric Radar Scanner around primary target
        if primary_target:
            rad = min(40, max(22, int(min(box_w, box_h) * 0.25)))
            cv2.circle(frame, (target_cx, target_cy), rad, cue_color, 1, cv2.LINE_AA)
            cv2.circle(frame, (target_cx, target_cy), int(rad * 0.6), cue_color, 1, cv2.LINE_AA)

            ang_r = math.radians((anim_tick * 4) % 360)
            dx1 = int(rad * math.cos(ang_r))
            dy1 = int(rad * math.sin(ang_r))
            cv2.line(frame, (target_cx - dx1, target_cy - dy1), (target_cx + dx1, target_cy + dy1), cue_color, 1, cv2.LINE_AA)

        # Detection Reticles & Face Landmarks
        for det in current_dets:
            x1 = int(det["bbox"][0] * scale_x)
            y1 = int(det["bbox"][1] * scale_y)
            x2 = int(det["bbox"][2] * scale_x)
            y2 = int(det["bbox"][3] * scale_y)

            is_primary = (det == primary_target)
            is_face = det.get("is_face_only") or (det.get("raw_class") == "FACE")
            is_known = det.get("is_hvt", False)

            if is_primary:
                color = (0, 255, 255) if is_known else ((0, 240, 255) if is_face else (0, 255, 119))
            else:
                color = (0, 180, 220) if is_face else (0, 180, 90)

            # 3D Corner Reticles
            line_len = max(14, min(32, (x2 - x1) // 4))
            thick = 2 if is_primary else 1
            cv2.line(frame, (x1, y1), (x1 + line_len, y1), color, thick)
            cv2.line(frame, (x1, y1), (x1 + line_len, y1), color, thick)
            cv2.line(frame, (x2, y1), (x2 - line_len, y1), color, thick)
            cv2.line(frame, (x2, y1), (x2 - line_len, y1), color, thick)
            cv2.line(frame, (x1, y2), (x1 + line_len, y2), color, thick)
            cv2.line(frame, (x1, y2), (x1 + line_len, y2), color, thick)
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, thick)
            cv2.line(frame, (x2, y2), (x2 - line_len, y2), color, thick)

            # Floating Cyber Dossier Badge for Primary Target
            if is_primary:
                card_x = min(fw - 260, x2 + 15)
                card_y = max(70, y1)
                cv2.line(frame, (x2, y1 + 10), (card_x, card_y + 10), color, 1, cv2.LINE_AA)
                cv2.circle(frame, (card_x, card_y + 10), 3, color, -1)

                card_bg = np.zeros((80, 240, 3), dtype=np.uint8)
                cv2.putText(card_bg, f"TARGET: {det['class_name']}", (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)
                cv2.putText(card_bg, f"TYPE: {det['target_type']}", (8, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 240, 255), 1)
                cv2.putText(card_bg, f"CONF: {int(det['confidence']*100)}% | RANGE: {est_distance}m", (8, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 119), 1)
                rf_status = f"RF LINK: {rf_bridge.port_name}" if rf_bridge.is_connected else "RF LINK: STANDBY"
                cv2.putText(card_bg, rf_status, (8, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 200, 255), 1)
                frame[card_y:card_y+80, card_x:card_x+240] = cv2.addWeighted(frame[card_y:card_y+80, card_x:card_x+240], 0.2, card_bg, 0.8, 0)
                cv2.rectangle(frame, (card_x, card_y), (card_x + 240, card_y + 80), color, 1)

            # Face Landmark Dots
            assoc_face = det.get("associated_face")
            if assoc_face and "landmarks" in assoc_face:
                for lm in assoc_face["landmarks"]:
                    lx = int(lm[0] * scale_x)
                    ly = int(lm[1] * scale_y)
                    cv2.circle(frame, (lx, ly), 2, (0, 255, 255), -1)

            # Guidance Vector Line
            if is_primary:
                cv2.line(frame, (cx_screen, cy_screen), (target_cx, target_cy), color, 1, cv2.LINE_AA)
                cv2.circle(frame, (target_cx, target_cy), 5, (0, 0, 255), -1)

        # Center HUD Boresight Reticle
        cv2.drawMarker(frame, (cx_screen, cy_screen), (0, 255, 0), cv2.MARKER_CROSS, 28, 1)
        cv2.circle(frame, (cx_screen, cy_screen), 42, (0, 180, 0), 1)

        # ---------------------------------------------------------------------
        # TACTICAL TELEMETRY HUD RIBBONS
        # ---------------------------------------------------------------------
        # 1. Top Header Banner
        cv2.rectangle(frame, (0, 0), (fw, 32), (10, 14, 18), -1)
        auto_str = "AUTONOMOUS PID: [ENGAGED]" if flight.auto_tracking_active else "AUTONOMOUS PID: [STANDBY]"
        auto_col = (0, 255, 119) if flight.auto_tracking_active else (0, 200, 255)
        rf_txt = f"2.4GHz RF: [{rf_bridge.port_name}]" if rf_bridge.is_connected else "2.4GHz RF: STANDBY"
        cv2.putText(frame, f"TRINETRA-C2 // AIRBORNE RECON [E88] | {auto_str} | {rf_txt}", (12, 21),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.40, auto_col, 1, cv2.LINE_AA)
        cv2.putText(frame, f"DISP: {display_fps:.0f} FPS | AI: {inference_fps:.0f} FPS",
                    (fw - 220, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 119), 1, cv2.LINE_AA)

        # 2. Flight Director Guidance Ribbon
        cv2.rectangle(frame, (0, 32), (fw, 64), (18, 22, 28), -1)
        cv2.putText(frame, director_cue, (14, 54),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, cue_color, 1, cv2.LINE_AA)
        if primary_target:
            cv2.putText(frame, f"RANGE: {est_distance}m | BEARING: {yaw_deg:+.1f} deg | YAW_PID: {tele['yaw']} | PITCH_PID: {tele['pitch']}",
                        (fw - 460, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 240, 255), 1, cv2.LINE_AA)

        # 3. Bottom Mission Telemetry Ribbon
        cv2.rectangle(frame, (0, fh - 36), (fw, fh), (10, 14, 18), -1)
        tele_str = f"MGRS: 43R EQ 5980 9700 | 2.4GHz SETPOINTS: [R:{tele['roll']} P:{tele['pitch']} T:{tele['throttle']} Y:{tele['yaw']}] | SEC-65B: ACTIVE"
        cv2.putText(frame, tele_str, (12, fh - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 240, 255), 1, cv2.LINE_AA)

        # 4. Interactive Quick-Controls Box (Left Sidebar)
        help_bg = np.zeros((150, 250, 3), dtype=np.uint8)
        cv2.putText(help_bg, "[SPACE] AUTO-TRACK TOGGLE", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 119), 1)
        cv2.putText(help_bg, "[T]     AUTO TAKEOFF", (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 240, 255), 1)
        cv2.putText(help_bg, "[L]     AUTO LANDING", (10, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 255), 1)
        cv2.putText(help_bg, "[X]     EMERGENCY KILL SWITCH", (10, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 70, 255), 1)
        cv2.putText(help_bg, "[D]     Cycle Lens Mode", (10, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        cv2.putText(help_bg, "[E]     Cycle De-Blur Filter", (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        cv2.putText(help_bg, "[TAB]   Cycle Target Lock", (10, 128), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        cv2.putText(help_bg, "[V]     Switch Video Source", (10, 146), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
        frame[72:222, 10:260] = cv2.addWeighted(frame[72:222, 10:260], 0.2, help_bg, 0.8, 0)
        cv2.rectangle(frame, (10, 72), (260, 222), (0, 240, 255), 1)

        cv2.imshow("TRINETRA-C2: Autonomous Airborne Sentry & PID Interceptor", frame)

        # Keyboard Intercept Loop
        key = cv2.waitKey(1) & 0xFF
        if key in [ord('q'), ord('Q'), 27]:
            break
        elif key == 32:  # SPACE: Toggle Autonomous PID Visual Tracking
            st = flight.toggle_auto_tracking()
            print(f"[AUTONOMOUS-CORE] Visual Servoing PID Tracking: {'ENGAGED' if st else 'DISENGAGED'}")
        elif key in [ord('t'), ord('T')]:
            flight.trigger_takeoff()
            rf_bridge.trigger_takeoff()
        elif key in [ord('l'), ord('L')]:
            flight.trigger_land()
            rf_bridge.trigger_land()
        elif key in [ord('x'), ord('X')]:
            flight.trigger_emergency_stop()
            rf_bridge.trigger_emergency_stop()
            print("[AUTONOMOUS-CORE] EMERGENCY KILL SWITCH TRIGGERED: Motors CUT.")
        elif key in [ord('d'), ord('D')]:
            lens_name = demuxer.cycle_mode()
            print(f"[LENS] Optical Lens Mode: {lens_name}")
        elif key in [ord('e'), ord('E')]:
            mode_name = enhancer.cycle_mode()
            print(f"[OPTICS] Image Enhancement Filter: {mode_name}")
        elif key == 9:  # TAB Key: Cycle lock-on target
            if current_dets:
                selected_target_idx = (selected_target_idx + 1) % len(current_dets)
                print(f"[DIRECTOR] Lock-On Cycled to Target #{selected_target_idx + 1}: {sorted_dets[selected_target_idx]['class_name']}")
        elif key in [ord('v'), ord('V')]:
            source_toggle_idx = (source_toggle_idx + 1) % len(available_sources)
            stream.switch_source(available_sources[source_toggle_idx])
        elif key in [ord('s'), ord('S')]:
            snap_path = logger.log_manual_snapshot(
                frame,
                sector_info=sector_info,
                sensor_mode="AIRBORNE_OPTICAL"
            )
            print(f"[SEC-65B] Forensic Snapshot Committed: {snap_path}")
        elif key in [ord('m'), ord('M')]:
            audio.toggle_mute()

    running = False
    stream.stop()
    flight.stop()
    rf_bridge.close()
    cv2.destroyAllWindows()
    print("[C2] Autonomous Airborne Session Safely Terminated.")


if __name__ == "__main__":
    main()
