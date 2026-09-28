import os
# Configure low-latency TCP transport for drone RTSP video feeds across the server
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|max_delay;0"
# Constrain PyTorch thread count and memory footprint for cloud deployment (512MB RAM cap)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
import torch
torch.set_grad_enabled(False)
try:
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
except Exception:
    pass
import cv2
import time
import json
import base64
import asyncio
import threading
import numpy as np
from typing import Dict, Any, Optional
from fastapi import FastAPI, Response, Request
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.stream_engine import VideoStreamEngine
from core.detector import TacticalDetector
from core.tripwire import ExclusionPolygonZone
from core.hud_renderer import TacticalHUDRenderer
from core.audio_alert import TacticalAudioAlert
from core.evidence_logger import CryptographicEvidenceLogger
from core.geo_telemetry import GeoTelemetry
from core.gods_eye_engine import GodsEyeEngine
from core.satellite_engine import SatelliteOrbitalEngine
from core.camera_manager import CameraNetworkManager
from core.reid_engine import GlobalEntityTracker
from core.hardware_bridge import HardwarePeripheralBridge
from core.global_camera_catalog import GlobalCameraCatalog
from core.interdiction_engine import InterdictionDispatchEngine
from core.alert_dispatcher import AlertDispatcher

app = FastAPI(title="Project TRINETRA-C2 // Autonomous Border Surveillance C2")

os.makedirs("static", exist_ok=True)
os.makedirs("evidence", exist_ok=True)
os.makedirs("known_faces", exist_ok=True)

# Sector Catalog with Geospatial Border Coordinates and MGRS Grid
SECTORS = {
    1: {
        "id": 1,
        "name": "SECTOR-01 // PUNJAB PERIMETER WALL",
        "codename": "TRINETRA-PUNJAB-OUTPOST-04",
        "location": "Amritsar-Wagah Frontier Corridor",
        "lat": 31.604,
        "lng": 74.572,
        "mgrs": GeoTelemetry.latlon_to_mgrs(31.604, 74.572),
        "source": "sample_footage/border_fence_ladder.mp4",
        "type": "ELEVATED MAST CCTV // OPTICAL",
        "stsi_base": 78,
        "status": "ELEVATED THREAT",
        "preset": 1
    },
    2: {
        "id": 2,
        "name": "SECTOR-02 // PERIMETER SECURITY CORDON",
        "codename": "TRINETRA-FRONTIER-SENTRY-02",
        "location": "Forward Operational Perimeter Post // Sector 2",
        "lat": 31.842,
        "lng": 74.912,
        "mgrs": GeoTelemetry.latlon_to_mgrs(31.842, 74.912),
        "source": "sample_footage/perimeter_sentry_daylight.mp4",
        "type": "ELEVATED MAST CCTV // OPTICAL SENTRY",
        "stsi_base": 76,
        "status": "STERILE CORRIDOR WATCH",
        "preset": 2
    },
    3: {
        "id": 3,
        "name": "SECTOR-03 // HIGHWAY ANPR CORRIDOR",
        "codename": "TRINETRA-HIGHWAY-ANPR-03",
        "location": "Strategic Highway Transit Corridor NH-44",
        "lat": 32.610,
        "lng": 74.720,
        "mgrs": GeoTelemetry.latlon_to_mgrs(32.610, 74.720),
        "source": "sample_footage/previews2/checkpoint_1.mp4",
        "type": "HIGHWAY HIGH-SPEED ANPR / SENTRY",
        "stsi_base": 82,
        "status": "ANPR INTERDICTION",
        "preset": 3
    },
    4: {
        "id": 4,
        "name": "SECTOR-04 // HIGHWAY INTERDICTION CHECKPOINT",
        "codename": "TRINETRA-TRANSIT-CHECKPOINT-04",
        "location": "Transit Highway Strategic Interdiction Axis",
        "lat": 32.726,
        "lng": 74.857,
        "mgrs": GeoTelemetry.latlon_to_mgrs(32.726, 74.857),
        "source": "sample_footage/previews7/sec_2.mp4",
        "type": "TACTICAL INTERDICTION // ANPR SENTINEL",
        "stsi_base": 84,
        "status": "ACTIVE INTERDICTION",
        "preset": 4
    },
    5: {
        "id": 5,
        "name": "SECTOR-05 // AIRBORNE DRONE RECON",
        "codename": "TRINETRA-AIRBORNE-E88-05",
        "location": "Tactical Low-Altitude Aerial Patrol (E88 Plus)",
        "lat": 31.608,
        "lng": 74.578,
        "mgrs": GeoTelemetry.latlon_to_mgrs(31.608, 74.578),
        "source": "sample_footage/previews_godseye/drone_track1.mp4",
        "type": "AIRBORNE RECON SENTRY // FPV",
        "stsi_base": 82,
        "status": "AIRBORNE PATROL ACTIVE",
        "preset": 5
    }
}

class C2State:
    def __init__(self):
        self.lock = threading.Lock()
        self.active_sector = 1
        self.detector = TacticalDetector(model_weight="yolov8n.pt", conf_thresh=0.15, use_tracking=True)
        self.zone = ExclusionPolygonZone(persistence_threshold=2)
        self.hud = TacticalHUDRenderer()
        self.audio = TacticalAudioAlert(cooldown=3.5)
        self.logger = CryptographicEvidenceLogger(output_dir="evidence")
        self.gods_eye = GodsEyeEngine()
        self.satellite_engine = SatelliteOrbitalEngine()
        self.camera_mgr = CameraNetworkManager(SECTORS)
        self.global_tracker = GlobalEntityTracker(similarity_threshold=0.70)
        self.hardware_bridge = HardwarePeripheralBridge()
        self.global_catalog = GlobalCameraCatalog()
        self.interdiction_engine = InterdictionDispatchEngine()
        self.alert_dispatcher = AlertDispatcher()
        self.gods_eye_mode = True
        self.multiview_mode = False
        self.zone_visible = True
        self.stream: Optional[VideoStreamEngine] = None
        
        # Defense Policies
        self.auto_handoff_enabled = False  # Keep camera steady by default; manual toggleable via UI
        self.last_handoff_time = time.time()
        self.handoff_cooldown = 45.0  # At least 45 seconds between automated handoffs
        self.latest_handoff_event = None
        
        # Telemetry Cache
        self.current_fps = 30.0
        self.current_latency = 11.2
        self.tracked_count = 0
        self.active_breaches = []
        self.cached_faces = []
        self.latest_encoded_frame = None
        self.encoded_frame_id = 0
        self.sector_version = 0
        self.running = True

        # Multi-Threaded Decoupled Perception & Smooth Streaming
        self.inference_lock = threading.Lock()
        self.latest_raw_frame = None
        self.cached_dets = []
        self.cached_breaches = []
        
        # Pipeline Background Thread
        self.thread = None
        self.init_sector(1)

    def init_sector(self, sector_id: int):
        with self.lock:
            self.active_sector = sector_id
            self.sector_version += 1
            
            # Switch camera and release inactive video stream decoders to save 80% CPU
            self.camera_mgr.activate_camera(sector_id, allow_multiview=self.multiview_mode)
            self.stream = self.camera_mgr.streams.get(sector_id)
            info = SECTORS.get(sector_id, SECTORS[1])
            
            # Read first pre-buffered frame immediately (0ms delay)
            ret, frame = self.stream.read() if self.stream else (False, None)
            if ret and frame is not None:
                h, w = frame.shape[:2]
                self.zone.set_preset_corridor(w, h, sector_id=sector_id)
            else:
                self.zone.set_preset_corridor(854, 480, sector_id=sector_id)
                
            # Flawlessly reset ByteTrack internal states and force full inference on frame 0
            self.detector.reset_tracker()
            
            # Atomically flush all old bounding boxes, breaches, and face caches under inference_lock
            with self.inference_lock:
                self.latest_raw_frame = frame if (ret and frame is not None) else None
                self.cached_dets = []
                self.cached_faces = []
                self.cached_breaches = []
                self.active_breaches = []
                self.tracked_count = 0
                self.current_latency = 0.0
                
            # Clear audio alert cooldowns so old alerts do not bleed across sectors
            self.audio.last_alert_time = 0.0
            self.audio.last_vehicle_alert = 0.0
            
            print(f"[C2-CORE] Initialized Sector {sector_id}: {info['name']} (MGRS: {info['mgrs']})")

    def switch_source(self, new_source):
        with self.lock:
            if self.stream:
                self.stream.stop()
            src = new_source
            if isinstance(src, str) and src.isdigit():
                src = int(src)
            self.stream = VideoStreamEngine(source=src, loop=True).start()
            time.sleep(0.3)
            ret, frame = self.stream.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                if isinstance(src, int) or str(src) in ["0", "1", "2"] or "webcam" in str(src).lower():
                    self.zone.clear()
                    print(f"[C2-CORE] Custom / Webcam mode active: Cleared exclusion corridor polygon.")
                else:
                    self.zone.set_preset_corridor(w, h, sector_id=self.active_sector)
            self.detector.reset_tracker()
            print(f"[C2-CORE] Switched video source to: {new_source}")

    def run_inference_worker(self):
        """Asynchronous background neural perception worker (YOLOv8 + YuNet/SFace + ANPR + ReID)."""
        while self.running:
            try:
                if not self.stream:
                    time.sleep(0.01)
                    continue
                with self.inference_lock:
                    frame_to_process = self.latest_raw_frame.copy() if self.latest_raw_frame is not None else None
                    frame_sector = self.active_sector
                    frame_version = self.sector_version
                    
                if frame_to_process is None:
                    time.sleep(0.01)
                    continue

                sec_info = SECTORS.get(frame_sector, SECTORS[1])
                fence_pts = self.zone.points if len(self.zone.points) >= 2 else None
                
                # Sector 1 uses 640 for distant fence climbers; Sectors 2-5 use 480 for 2x faster CPU inference
                target_imgsz = 640 if frame_sector == 1 else 480
                processed_frame, dets, faces, lat_ms = self.detector.detect(
                    frame_to_process, fence_coords=fence_pts, imgsz=target_imgsz
                )

                # Check if sector was switched while inference was running: discard stale results immediately
                with self.inference_lock:
                    if self.sector_version != frame_version or self.active_sector != frame_sector:
                        continue

                breaches, suppressed = self.zone.evaluate_detections(dets)
                is_breached = len(breaches) > 0

                if is_breached:
                    self.audio.trigger_breach_alert(intruder_count=len(breaches))
                    for b in breaches:
                        logged = self.logger.log_incident(
                            frame_to_process, 
                            b, 
                            manual=False, 
                            sector_info=sec_info, 
                            sensor_mode=self.detector.sensor.active_mode
                        )
                        # Multi-channel instant alert dispatch (Telegram Bot & Webhook)
                        sec_hash = logged.get("sha256", "N/A") if logged else "N/A"
                        alert_payload = {
                            "sector_name": sec_info.get("name", "BORDER CORRIDOR"),
                            "mgrs": sec_info.get("mgrs", "N/A"),
                            "threat_level": "CRITICAL INCURSION DETECTED",
                            "sec65b_hash": sec_hash,
                            "intruder_class": b.get("class_name", "PERSON"),
                            "timestamp": time.time()
                        }
                        self.alert_dispatcher.trigger_alert(alert_payload, frame_to_process)

                # ANPR Vehicle Watchlist Interdiction Check
                for det in dets:
                    anpr = det.get("anpr")
                    if anpr and anpr.get("is_alert") and not anpr.get("_server_alerted"):
                        anpr["_server_alerted"] = True
                        self.audio.trigger_vehicle_alert(anpr.get("plate", ""), anpr.get("category", "STOLEN VEHICLE"))
                        self.logger.log_incident(
                            frame_to_process,
                            det,
                            manual=False,
                            sector_info=sec_info,
                            sensor_mode=self.detector.sensor.active_mode
                        )

                # ReID & Global Entity Tracking
                for det in dets:
                    if det.get("class_name") == "PERSON":
                        emb = det.get("reid_embedding")
                        face_name = None
                        if faces:
                            fx1, fy1, fx2, fy2 = det["bbox"]
                            for f in faces:
                                bx, by, bw, bh = f["bbox"]
                                if (fx1 - 15 <= bx <= fx2 + 15) and f.get("is_known"):
                                    face_name = f.get("name")
                                    break

                        gid, sim, transit = self.global_tracker.match_or_create(
                            embedding=emb,
                            camera_id=frame_sector,
                            sector_name=sec_info["name"],
                            bbox=det["bbox"],
                            face_name=face_name
                        )
                        det["global_id"] = gid
                        det["reid_sim"] = sim
                        det["reid_transit"] = transit
                    else:
                        det["global_id"] = f"ID#{det.get('track_id', 1)}"

                # Hardware Turret Visual Tracking & Actuator Kinematics
                fh, fw = frame_to_process.shape[:2]
                primary_target_bbox = None
                primary_target_obj = None
                if breaches:
                    primary_target_obj = breaches[0].get("detection")
                    if primary_target_obj and "bbox" in primary_target_obj:
                        primary_target_bbox = primary_target_obj["bbox"]
                elif dets:
                    primary_target_obj = dets[0]
                    primary_target_bbox = dets[0]["bbox"]
                self.hardware_bridge.update(primary_target_bbox, (fw, fh))

                # Autonomous QRT Interdiction
                self.interdiction_engine.update_realtime_kinematics(
                    sector_info=sec_info,
                    primary_target=primary_target_obj,
                    breach_count=len(breaches)
                )

                # Autonomous Kinematic Handoff
                if self.auto_handoff_enabled and (time.time() - self.last_handoff_time > self.handoff_cooldown):
                    trigger_handoff = False
                    handoff_reason = ""
                    handoff_target_id = None
                    if breaches:
                        b_det = breaches[0].get("detection", {})
                        bx1, by1, bx2, by2 = b_det.get("bbox", [0, 0, 0, 0])
                        b_cx = (bx1 + bx2) / 2.0
                        kin = b_det.get("kinematics", {})
                        vx, vy = kin.get("velocity", (0, 0))
                        handoff_target_id = b_det.get("global_id") or f"ID#{b_det.get('track_id', 1)}"
                        if (b_cx < fw * 0.06 and vx < -4.0) or (b_cx > fw * 0.94 and vx > 4.0):
                            trigger_handoff = True
                            handoff_reason = f"Perimeter incursion egress at x={int(b_cx)}px (vx={vx:+.1f})"
                    if trigger_handoff:
                        curr_sec = self.active_sector
                        next_sec = (curr_sec % 4) + 1
                        self.last_handoff_time = time.time()
                        self.latest_handoff_event = {
                            "event": "AUTONOMOUS_HANDOFF",
                            "from_sector": curr_sec,
                            "from_name": sec_info["name"],
                            "to_sector": next_sec,
                            "to_name": SECTORS[next_sec]["name"],
                            "target_id": handoff_target_id,
                            "reason": handoff_reason,
                            "timestamp": time.time(),
                            "time_str": time.strftime("%H:%M:%S")
                        }
                        self.init_sector(next_sec)
                        continue

                # Atomically commit new detections ONLY if sector is still matching
                with self.inference_lock:
                    if self.sector_version == frame_version and self.active_sector == frame_sector:
                        self.cached_dets = dets
                        self.cached_faces = faces
                        self.cached_breaches = breaches
                        self.current_latency = lat_ms
                        self.tracked_count = len(dets)
                        self.active_breaches = breaches

                time.sleep(0.01)
            except Exception as e:
                print(f"[C2-INFERENCE ERROR] {e}")
                time.sleep(0.02)

    def run_pipeline(self):
        """High-Performance 32 FPS Smooth Rolling Visual Render & Streaming Pipeline."""
        fps_start = time.time()
        fps_frames = 0
        target_dt = 1.0 / 30.0  # Rock-solid 30.0 FPS cadence
        while self.running:
            loop_t0 = time.perf_counter()
            try:
                if not self.stream:
                    time.sleep(0.02)
                    continue
                    
                ret, frame = self.stream.read()
                if not ret or frame is None:
                    time.sleep(0.01)
                    continue

                # Standardize frame to 854x480 for fast rendering and low latency
                fh, fw = frame.shape[:2]
                if fw != 854 or fh != 480:
                    frame = cv2.resize(frame, (854, 480), interpolation=cv2.INTER_LINEAR)

                with self.inference_lock:
                    self.latest_raw_frame = frame
                    dets = list(self.cached_dets)
                    faces = list(self.cached_faces)
                    breaches = list(self.cached_breaches)
                    lat_ms = self.current_latency

                sec_info = SECTORS.get(self.active_sector, SECTORS[1])
                processed_frame = self.detector.sensor.process(frame)
                is_breached = len(breaches) > 0

                if self.multiview_mode:
                    fh, fw = processed_frame.shape[:2]
                    hud_frame = self.camera_mgr.render_multiview_matrix(fw, fh)
                elif self.gods_eye_mode:
                    hud_frame = self.gods_eye.render_gods_eye_hud(
                        processed_frame,
                        detections=dets,
                        active_breaches=breaches,
                        fps=self.current_fps,
                        latency_ms=lat_ms,
                        sector_label=sec_info["name"],
                        mgrs=sec_info["mgrs"],
                        zone_obj=(self.zone if self.zone_visible else None),
                        faces=faces
                    )
                else:
                    if self.zone_visible:
                        self.zone.draw_zone(processed_frame, is_breached=is_breached)
                    recon = GeoTelemetry.compute_recon_metrics()
                    gsd_text = f"GSD: {recon['gsd_cm_px']}cm | {recon['niirs_rating']}"
                    hud_frame = self.hud.draw_hud(
                        processed_frame,
                        detections=dets,
                        active_breaches=breaches,
                        fps=self.current_fps,
                        latency_ms=lat_ms,
                        clahe_on=self.detector.clahe_enabled,
                        sensor_mode=self.detector.sensor.active_mode,
                        mgrs=sec_info["mgrs"],
                        gsd_text=gsd_text,
                        muted=self.audio.muted,
                        sector_label=sec_info["name"],
                        is_godeye_mode=False
                    )

                _, buf = cv2.imencode(".jpg", hud_frame, [cv2.IMWRITE_JPEG_QUALITY, 68])
                self.latest_encoded_frame = buf.tobytes()
                self.encoded_frame_id += 1

                fps_frames += 1
                if time.time() - fps_start >= 1.0:
                    self.current_fps = fps_frames / (time.time() - fps_start)
                    fps_frames = 0
                    fps_start = time.time()

                rem = target_dt - (time.perf_counter() - loop_t0)
                if rem > 0:
                    time.sleep(rem)

            except Exception as e:
                print(f"[C2-PIPELINE ERROR] {e}")
                time.sleep(0.01)

c2 = C2State()
pipe_thread = threading.Thread(target=c2.run_pipeline, daemon=True)
infer_thread = threading.Thread(target=c2.run_inference_worker, daemon=True)
pipe_thread.start()
infer_thread.start()

# API Models
class ActionPayload(BaseModel):
    sector: Optional[int] = None
    mode: Optional[str] = None
    source: Optional[str] = None
    name: Optional[str] = None
    image_b64: Optional[str] = None

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/api/sectors")
async def get_sectors():
    res = []
    for sid, s in SECTORS.items():
        stsi = s["stsi_base"]
        if sid == c2.active_sector and len(c2.active_breaches) > 0:
            stsi = min(98, stsi + len(c2.active_breaches) * 12)
        item = dict(s)
        item["stsi"] = stsi
        item["is_active"] = (sid == c2.active_sector)
        res.append(item)
    return res

@app.get("/api/telemetry")
async def get_telemetry():
    sec_info = SECTORS.get(c2.active_sector, SECTORS[1])
    stsi = sec_info["stsi_base"]
    if len(c2.active_breaches) > 0:
        stsi = min(98, stsi + len(c2.active_breaches) * 12)

    recon = GeoTelemetry.compute_recon_metrics()
    
    return {
        "sector_id": c2.active_sector,
        "sector_name": sec_info["name"],
        "codename": sec_info["codename"],
        "mgrs": sec_info["mgrs"],
        "lat": sec_info["lat"],
        "lng": sec_info["lng"],
        "fps": round(c2.current_fps, 1),
        "latency_ms": round(c2.current_latency, 1),
        "tracked_count": c2.tracked_count,
        "breach_count": len(c2.active_breaches),
        "is_breached": len(c2.active_breaches) > 0,
        "sensor_mode": c2.detector.sensor.active_mode,
        "scope_mask": c2.detector.sensor.scope_mask_enabled,
        "auto_handoff": c2.auto_handoff_enabled,
        "clahe_enabled": c2.detector.clahe_enabled,
        "audio_muted": c2.audio.muted,
        "gods_eye_mode": c2.gods_eye_mode,
        "show_aux_hud": c2.gods_eye.show_aux_hud,
        "zone_visible": c2.zone_visible,
        "faces_detected": len(c2.cached_faces),
        "enrolled_faces_count": len(c2.detector.face_engine.known_names),
        "anpr_scans_count": len(c2.detector.anpr_engine.scan_logs),
        "anpr_watchlist_count": len(c2.detector.anpr_engine.watchlist),
        "latest_anpr": c2.detector.anpr_engine.scan_logs[0] if c2.detector.anpr_engine.scan_logs else None,
        "reid_entities_count": len(c2.global_tracker.entities),
        "reid_transits_count": len(c2.global_tracker.transit_logs),
        "multiview_mode": c2.multiview_mode,
        "hardware": c2.hardware_bridge.get_full_telemetry(),
        "global_cams_count": len(c2.global_catalog.cameras),
        "interdiction": c2.interdiction_engine.active_intercept,
        "interdiction_orders_count": len(c2.interdiction_engine.dispatch_history),
        "farr": c2.zone.get_farr_metrics(),
        "alerts_config": c2.alert_dispatcher.get_config(),
        "stsi": stsi,
        "gsd_cm_px": recon["gsd_cm_px"],
        "niirs": recon["niirs_rating"],
        "sun_azimuth": recon["sun_azimuth_deg"],
        "latest_handoff": c2.latest_handoff_event,
        "status": "CRITICAL INCURSION DETECTED" if len(c2.active_breaches) > 0 else sec_info["status"]
    }

@app.post("/api/control/toggle_auto_handoff")
def toggle_auto_handoff_api():
    c2.auto_handoff_enabled = not c2.auto_handoff_enabled
    return {"auto_handoff": c2.auto_handoff_enabled}

@app.get("/api/cameras/stream/{cam_id}")
def stream_single_camera(cam_id: str):
    cam = c2.global_catalog.get_camera(cam_id)
    src = cam["source"] if cam else "sample_footage/border_fence_ladder.mp4"
    def gen():
        cap = cv2.VideoCapture(src)
        while True:
            ret, f = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            f = cv2.resize(f, (480, 270))
            name_lbl = cam['name'] if cam else cam_id
            cv2.putText(f, f"INTERCEPT // {name_lbl}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 240, 255), 1, cv2.LINE_AA)
            _, buf = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 60])
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
            time.sleep(0.04)
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/stream")
async def stream_video():
    async def frame_generator():
        last_frame_id = -1
        while True:
            fid = c2.encoded_frame_id
            if fid != last_frame_id:
                frame_bytes = c2.latest_encoded_frame
                if frame_bytes:
                    last_frame_id = fid
                    yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
            await asyncio.sleep(0.005)
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/snapshot")
async def get_snapshot():
    if c2.latest_encoded_frame:
        return Response(content=c2.latest_encoded_frame, media_type="image/jpeg")
    return JSONResponse({"status": "error", "message": "No frame available yet"}, status_code=503)

@app.get("/api/satellites")
async def get_satellites():
    return c2.satellite_engine.get_satellite_telemetry()

@app.get("/api/satellites/passes")
async def get_satellite_passes():
    return c2.satellite_engine.evaluate_sector_passes(SECTORS)

@app.get("/api/reid/entities")
async def get_reid_entities():
    c2.global_tracker.prune_stale_entities()
    return {
        "entities": c2.global_tracker.get_gallery_summary(),
        "total": len(c2.global_tracker.entities)
    }

@app.get("/api/reid/transits")
async def get_reid_transits():
    return {
        "transits": list(c2.global_tracker.transit_logs),
        "total": len(c2.global_tracker.transit_logs)
    }

@app.get("/api/cameras/list")
async def get_cameras():
    return c2.camera_mgr.get_cameras_summary()

class CustomCameraPayload(BaseModel):
    name: str
    source: str
    cam_type: Optional[str] = "OPTICAL CCTV"
    lat: Optional[float] = 31.604
    lng: Optional[float] = 74.572
    mgrs: Optional[str] = "43R EQ 5940 9662"

class AlertConfigPayload(BaseModel):
    telegram_enabled: Optional[bool] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    webhook_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    cooldown_seconds: Optional[float] = None

@app.post("/api/cameras/add_custom")
def add_custom_camera_api(payload: CustomCameraPayload):
    info = c2.camera_mgr.add_custom_camera(
        name=payload.name,
        source=payload.source,
        cam_type=payload.cam_type or "OPTICAL CCTV",
        lat=payload.lat or 31.604,
        lng=payload.lng or 74.572,
        mgrs=payload.mgrs or "43R EQ 5940 9662"
    )
    return {"status": "success", "camera": info}

@app.post("/api/cameras/delete/{camera_id}")
def delete_camera_api(camera_id: int):
    success = c2.camera_mgr.remove_custom_camera(camera_id)
    if success:
        return {"status": "success", "message": f"Camera #{camera_id} removed successfully"}
    return JSONResponse({"status": "error", "message": "Cannot delete primary default sector cameras (1-4)."}, status_code=400)

@app.get("/api/cameras/scan_devices")
def scan_local_devices_api():
    devices = c2.camera_mgr.probe_local_video_devices()
    return {"status": "success", "devices": devices, "count": len(devices)}

@app.get("/api/alerts/config")
def get_alerts_config_api():
    return c2.alert_dispatcher.get_config()

@app.post("/api/alerts/config")
def set_alerts_config_api(payload: AlertConfigPayload):
    updates = {}
    if payload.telegram_enabled is not None:
        updates["telegram_enabled"] = payload.telegram_enabled
    if payload.telegram_bot_token is not None and payload.telegram_bot_token.strip():
        updates["telegram_bot_token"] = payload.telegram_bot_token.strip()
    if payload.telegram_chat_id is not None and payload.telegram_chat_id.strip():
        updates["telegram_chat_id"] = payload.telegram_chat_id.strip()
    if payload.webhook_enabled is not None:
        updates["webhook_enabled"] = payload.webhook_enabled
    if payload.webhook_url is not None and payload.webhook_url.strip():
        updates["webhook_url"] = payload.webhook_url.strip()
    if payload.cooldown_seconds is not None:
        updates["cooldown_seconds"] = payload.cooldown_seconds
        
    saved = c2.alert_dispatcher.save_config(updates)
    return {"status": "success", "config": saved}

@app.post("/api/alerts/test")
def test_alert_api():
    res = c2.alert_dispatcher.test_alert()
    return res

@app.post("/api/control/toggle_multiview")
def toggle_multiview_api():
    c2.multiview_mode = not c2.multiview_mode
    return {"multiview_mode": c2.multiview_mode}

# ===================================================================
# GLOBAL CAMERA DIRECTORY & OPEN FEEDS GATEWAY ENDPOINTS
# ===================================================================
@app.get("/api/cameras/global/list")
def get_global_cameras():
    return {
        "cameras": c2.global_catalog.get_all_cameras(),
        "total": len(c2.global_catalog.cameras)
    }

class GlobalAssignPayload(BaseModel):
    slot_id: int  # 1 to 4
    camera_id: str
    set_primary: Optional[bool] = False

@app.post("/api/cameras/global/assign")
def assign_global_camera(payload: GlobalAssignPayload):
    cam = c2.global_catalog.get_camera(payload.camera_id)
    if not cam:
        return JSONResponse({"status": "error", "message": f"Camera {payload.camera_id} not found in catalog."}, status_code=404)
    
    slot_id = max(1, min(4, payload.slot_id))
    
    # Update SECTORS catalog entry
    SECTORS[slot_id] = {
        "id": slot_id,
        "name": cam["name"],
        "codename": cam["codename"],
        "location": cam.get("location", cam["name"]),
        "lat": cam["lat"],
        "lng": cam["lng"],
        "mgrs": cam["mgrs"],
        "source": cam["source"],
        "type": cam["type"],
        "stsi_base": SECTORS.get(slot_id, {}).get("stsi_base", 60),
        "status": "ONLINE // ACTIVE STREAM",
        "preset": slot_id
    }
    
    assigned_info = c2.camera_mgr.assign_slot_stream(
        slot_id=slot_id,
        source=cam["source"],
        name=cam["name"],
        codename=cam["codename"],
        lat=cam["lat"],
        lng=cam["lng"],
        mgrs=cam["mgrs"],
        cam_type=cam["type"],
        set_as_primary=payload.set_primary or (slot_id == c2.active_sector)
    )
    
    # If this slot is active sector or requested as primary, switch pipeline stream
    if payload.set_primary or (slot_id == c2.active_sector):
        c2.active_sector = slot_id
        c2.switch_source(cam["source"])
        
    return {
        "status": "success",
        "slot_id": slot_id,
        "is_primary": (slot_id == c2.active_sector),
        "assigned": assigned_info
    }

class GlobalAddCameraPayload(BaseModel):
    name: str
    source: str
    lat: float
    lng: float
    type: Optional[str] = "CUSTOM RTSP / IP STREAM"
    location: Optional[str] = "Operator Registered Stream"
    region: Optional[str] = "CUSTOM"

@app.post("/api/cameras/global/add")
def add_global_camera(payload: GlobalAddCameraPayload):
    new_cam = c2.global_catalog.add_custom_camera(
        name=payload.name,
        source=payload.source,
        lat=payload.lat,
        lng=payload.lng,
        cam_type=payload.type or "CUSTOM RTSP / IP STREAM",
        location=payload.location or "Operator Registered Stream",
        region=payload.region or "CUSTOM"
    )
    return {"status": "success", "camera": new_cam}

# ===================================================================
# AUTONOMOUS QRT INTERDICTION DISPATCH & HANDOFF ENDPOINTS
# ===================================================================
@app.get("/api/interdiction/status")
async def get_interdiction_status():
    return {
        "active_intercept": c2.interdiction_engine.active_intercept,
        "qrt_units": list(c2.interdiction_engine.qrt_units.values()),
        "recent_orders_count": len(c2.interdiction_engine.dispatch_history)
    }

class QRTDispatchPayload(BaseModel):
    operator_callsign: Optional[str] = "C2-COMMANDER"
    heading_deg: Optional[float] = None
    speed_mps: Optional[float] = None
    eta_sec: Optional[float] = None
    target_id: Optional[str] = None
    classification: Optional[str] = None

@app.post("/api/interdiction/dispatch")
def dispatch_interdiction(payload: QRTDispatchPayload):
    sec_info = SECTORS.get(c2.active_sector, SECTORS[1])
    active_int = c2.interdiction_engine.active_intercept
    
    target_intel = {
        "id": payload.target_id or (active_int.get("target_id") if active_int else "G-01"),
        "class_name": payload.classification or (active_int.get("target_class") if active_int else "PERSON"),
        "heading_deg": payload.heading_deg if payload.heading_deg is not None else (active_int["vector"]["heading_deg"] if active_int else 45.0),
        "speed_mps": payload.speed_mps if payload.speed_mps is not None else (active_int["vector"]["speed_mps"] if active_int else 3.5),
        "eta_sec": payload.eta_sec if payload.eta_sec is not None else (active_int["vector"]["time_to_intercept_sec"] if active_int else 38.0)
    }
    
    order = c2.interdiction_engine.generate_dispatch_order(
        target_intel=target_intel,
        sector_info=sec_info,
        operator_callsign=payload.operator_callsign or "C2-COMMANDER"
    )
    
    # Trigger audio announcement if enabled
    c2.audio.trigger_breach_alert(intruder_count=1)
    
    return {"status": "success", "order": order}

@app.get("/api/interdiction/orders")
async def get_interdiction_orders():
    return {
        "orders": c2.interdiction_engine.dispatch_history,
        "count": len(c2.interdiction_engine.dispatch_history)
    }

@app.get("/api/interdiction/ticket/{order_uuid}")
def get_interdiction_ticket(order_uuid: str):
    html = c2.interdiction_engine.generate_ticket_html(order_uuid)
    return HTMLResponse(content=html)

# ===================================================================
# HARDWARE GATEWAY & TURRET ACTUATOR ENDPOINTS
# ===================================================================
@app.get("/api/hardware/status")
async def get_hardware_status():
    return c2.hardware_bridge.get_full_telemetry()

class TurretJogPayload(BaseModel):
    pan_delta: Optional[float] = 0.0
    tilt_delta: Optional[float] = 0.0

@app.post("/api/hardware/turret/jog")
def jog_turret_api(payload: TurretJogPayload):
    c2.hardware_bridge.jog(payload.pan_delta or 0.0, payload.tilt_delta or 0.0)
    return {"status": "success", "turret": c2.hardware_bridge.get_full_telemetry()["turret"]}

class TurretSetAnglePayload(BaseModel):
    pan: float
    tilt: float

@app.post("/api/hardware/turret/set_angle")
def set_turret_angle_api(payload: TurretSetAnglePayload):
    c2.hardware_bridge.set_angle(payload.pan, payload.tilt)
    return {"status": "success", "turret": c2.hardware_bridge.get_full_telemetry()["turret"]}

@app.post("/api/hardware/turret/center")
def center_turret_api():
    c2.hardware_bridge.center_turret()
    return {"status": "success", "turret": c2.hardware_bridge.get_full_telemetry()["turret"]}

@app.post("/api/hardware/turret/toggle_autotrack")
def toggle_autotrack_api():
    st = c2.hardware_bridge.toggle_autotrack()
    return {"status": "success", "auto_track": st}

@app.post("/api/hardware/turret/toggle_autopatrol")
def toggle_autopatrol_api():
    st = c2.hardware_bridge.toggle_autopatrol()
    return {"status": "success", "auto_patrol": st}

@app.post("/api/hardware/ircut/toggle")
def toggle_ircut_api():
    res = c2.hardware_bridge.toggle_ircut()
    return {"status": "success", "ircut": res}

class ConnectSerialPayload(BaseModel):
    port: str

@app.post("/api/hardware/connect_serial")
def connect_serial_api(payload: ConnectSerialPayload):
    ok = c2.hardware_bridge.connect_serial(payload.port)
    return {"status": "success" if ok else "failed", "connected": ok}

@app.get("/api/faces/list")
async def get_enrolled_faces():
    return {
        "identities": c2.detector.face_engine.known_names,
        "count": len(c2.detector.face_engine.known_names)
    }

@app.post("/api/faces/enroll")
def enroll_face_api(payload: ActionPayload):
    name = payload.name or "UNKNOWN_SUBJECT"
    frame_to_enroll = None
    if payload.image_b64:
        try:
            img_data = base64.b64decode(payload.image_b64.split(",")[-1])
            np_arr = np.frombuffer(img_data, np.uint8)
            frame_to_enroll = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        except Exception as e:
            return JSONResponse({"status": "error", "message": f"Base64 decode failed: {e}"}, status_code=400)
    else:
        ret, frame = c2.stream.read() if c2.stream else (False, None)
        if ret and frame is not None:
            frame_to_enroll = frame

    if frame_to_enroll is None:
        return JSONResponse({"status": "error", "message": "No valid frame available for face enrollment."}, status_code=400)

    res = c2.detector.face_engine.enroll_face(frame_to_enroll, name, save_to_disk=True)
    return res

@app.get("/api/evidence")
async def get_evidence():
    ledger_path = os.path.join("evidence", "sec65b_evidence_ledger.json")
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                return records[-30:][::-1]
        except Exception:
            return []
    return []

@app.get("/api/evidence/certificate/{incident_uuid}")
def get_certificate(incident_uuid: str):
    html_doc = c2.logger.generate_certificate_html(incident_uuid)
    return HTMLResponse(content=html_doc)

@app.get("/api/anpr/logs")
async def get_anpr_logs():
    return {
        "logs": c2.detector.anpr_engine.scan_logs,
        "count": len(c2.detector.anpr_engine.scan_logs)
    }

@app.get("/api/anpr/watchlist")
async def get_anpr_watchlist():
    return {
        "watchlist": c2.detector.anpr_engine.watchlist,
        "count": len(c2.detector.anpr_engine.watchlist)
    }

class WatchlistAddPayload(BaseModel):
    plate: str
    category: Optional[str] = "STOLEN VEHICLE"
    risk: Optional[str] = "CRITICAL THREAT // LEVEL 1"
    vehicle_model: Optional[str] = "SUSPECT VEHICLE"
    alert_msg: Optional[str] = ""

@app.post("/api/anpr/watchlist")
def add_anpr_watchlist(payload: WatchlistAddPayload):
    entry = c2.detector.anpr_engine.add_to_watchlist(
        plate=payload.plate,
        category=payload.category or "STOLEN VEHICLE",
        risk=payload.risk or "CRITICAL THREAT // LEVEL 1",
        vehicle_model=payload.vehicle_model or "SUSPECT VEHICLE",
        alert_msg=payload.alert_msg or ""
    )
    return {"status": "success", "entry": entry}

@app.post("/api/control/{action}")
def control_action(action: str, payload: Optional[ActionPayload] = None):
    if action == "switch_sector":
        if payload and payload.sector in SECTORS:
            c2.init_sector(payload.sector)
            return {"status": "success", "sector": payload.sector}
    elif action == "switch_source":
        if payload and payload.source is not None:
            c2.switch_source(payload.source)
            return {"status": "success", "source": payload.source}
    elif action == "set_sensor_mode":
        if payload and payload.mode:
            ok = c2.detector.set_sensor_mode(payload.mode)
            c2.hardware_bridge.sync_sensor_mode(c2.detector.sensor.active_mode)
            return {"status": "success" if ok else "invalid_mode", "mode": c2.detector.sensor.active_mode}
    elif action == "toggle_scope":
        st = c2.detector.toggle_scope_mask()
        return {"status": "success", "scope_mask": st}
    elif action == "toggle_autohandoff":
        c2.auto_handoff_enabled = not c2.auto_handoff_enabled
        return {"status": "success", "auto_handoff": c2.auto_handoff_enabled}
    elif action == "toggle_clahe":
        st = c2.detector.toggle_clahe()
        return {"status": "success", "clahe": st}
    elif action == "toggle_mute":
        st = c2.audio.toggle_mute()
        return {"status": "success", "muted": st}
    elif action == "toggle_godseye":
        c2.gods_eye_mode = not c2.gods_eye_mode
        return {"status": "success", "gods_eye_mode": c2.gods_eye_mode}
    elif action == "toggle_hud_overlays":
        st = c2.gods_eye.toggle_aux_hud()
        return {"status": "success", "show_aux_hud": st}
    elif action == "toggle_zone":
        c2.zone_visible = not c2.zone_visible
        return {"status": "success", "zone_visible": c2.zone_visible}
    elif action == "capture_evidence":
        ret, frame = c2.stream.read() if c2.stream else (False, None)
        if ret and frame is not None:
            sec_info = SECTORS.get(c2.active_sector, SECTORS[1])
            c2.logger.log_incident(
                frame, 
                {"class_name": "MANUAL_OPERATOR_SWEEP", "track_id": 999, "confidence": 1.0}, 
                manual=True,
                sector_info=sec_info,
                sensor_mode=c2.detector.sensor.active_mode
            )
            return {"status": "success", "message": "Forensic evidence committed with SHA-256 hash"}
    elif action == "reset_sensors":
        c2.detector.sensor.active_mode = "NORMAL"
        c2.detector.sensor.scope_mask_enabled = False
        c2.detector.clahe_enabled = False
        c2.hardware_bridge.sync_sensor_mode("NORMAL")
        ret, frame = c2.stream.read() if c2.stream else (False, None)
        if ret and frame is not None:
            h, w = frame.shape[:2]
            src_str = str(c2.stream.source).lower() if c2.stream else ""
            if src_str in ["0", "1", "2"] or "webcam" in src_str:
                c2.zone.clear()
            else:
                c2.zone.set_preset_corridor(w, h, sector_id=c2.active_sector)
        return {
            "status": "success",
            "message": "Stream reset to default daylight optical RGB",
            "sensor_mode": "NORMAL",
            "scope_mask": False,
            "clahe_enabled": False
        }
    elif action == "reset_zone":
        c2.zone.clear()
        return {"status": "success", "message": "Exclusion polygon reset"}
    return JSONResponse({"status": "error", "message": "Invalid action"}, status_code=400)

app.mount("/evidence", StaticFiles(directory="evidence"), name="evidence")
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    default_port = int(os.environ.get("PORT", 8080))
    port = default_port
    print("\n" + "="*70)
    print(" PROJECT TRINETRA-C2 // AUTONOMOUS TACTICAL C2 WEB DASHBOARD")
    print(" Sponsoring Authority: Ministry of Home Affairs (MHA) | PS 26187")
    print(f" Server Endpoint: http://0.0.0.0:{port}")
    print("="*70 + "\n")
    try:
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
    except OSError:
        port = default_port + 1
        print(f"\n[NOTICE] Port {default_port} occupied. Launching automatically on http://0.0.0.0:{port}...\n")
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
