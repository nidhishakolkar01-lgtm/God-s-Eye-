import os

code = """import os
import cv2
import time
import json
import asyncio
import threading
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

app = FastAPI(title="Project TRINETRA-C2 // Autonomous Border Surveillance C2")

# Ensure static and evidence directories
os.makedirs("static", exist_ok=True)
os.makedirs("evidence", exist_ok=True)

# Sector Catalog with Geospatial Border Coordinates (India Frontier)
SECTORS = {
    1: {
        "id": 1,
        "name": "SECTOR-01 // PUNJAB PERIMETER WALL",
        "codename": "TRINETRA-PUNJAB-OUTPOST-04",
        "location": "Amritsar-Wagah Frontier Corridor",
        "lat": 31.604,
        "lng": 74.572,
        "source": "sample_footage/border_fence_ladder.mp4",
        "type": "ELEVATED MAST CCTV // OPTICAL",
        "stsi_base": 78,
        "status": "ELEVATED THREAT",
        "preset": 1
    },
    2: {
        "id": 2,
        "name": "SECTOR-02 // THAR NIGHT SENTRY",
        "codename": "TRINETRA-RAJASTHAN-FLIR-09",
        "location": "Jaisalmer Frontier Dune Sector",
        "lat": 27.023,
        "lng": 70.912,
        "source": "sample_footage/rvss_border_crossing.mp4",
        "type": "THERMAL RVSS // FORWARD FLIR",
        "stsi_base": 64,
        "status": "STERILE CORRIDOR WATCH",
        "preset": 2
    },
    3: {
        "id": 3,
        "name": "SECTOR-03 // JAMMU FORWARD CHECKPOST",
        "codename": "TRINETRA-JAMMU-MAST-02",
        "location": "R.S. Pura Security Transit Line",
        "lat": 32.610,
        "lng": 74.720,
        "source": "sample_footage/previews2/checkpoint_1.mp4",
        "type": "CHECKPOST TACTICAL SENTINEL",
        "stsi_base": 42,
        "status": "ACTIVE INSPECTION",
        "preset": 3
    },
    4: {
        "id": 4,
        "name": "SECTOR-04 // LOCAL TACTICAL SENSOR",
        "codename": "TRINETRA-HQ-DEPLOYABLE-01",
        "location": "Command Center USB / RTSP Node",
        "lat": 28.613,
        "lng": 77.209,
        "source": 0,
        "type": "LIVE OPTICAL RTSP / WEBCAM",
        "stsi_base": 15,
        "status": "LOCAL SENTRY",
        "preset": 4
    }
}

class C2State:
    def __init__(self):
        self.lock = threading.Lock()
        self.active_sector = 1
        self.detector = TacticalDetector(model_weight="yolov8n.pt", conf_thresh=0.25, use_tracking=True)
        self.zone = ExclusionPolygonZone(persistence_threshold=2)
        self.hud = TacticalHUDRenderer()
        self.audio = TacticalAudioAlert(cooldown=3.5)
        self.logger = CryptographicEvidenceLogger(output_dir="evidence")
        self.stream: Optional[VideoStreamEngine] = None
        
        # Telemetry Cache
        self.current_fps = 30.0
        self.current_latency = 11.2
        self.tracked_count = 0
        self.active_breaches = []
        self.latest_encoded_frame = None
        self.running = True
        
        # Pipeline Background Thread
        self.thread = None
        self.init_sector(1)

    def init_sector(self, sector_id: int):
        with self.lock:
            if self.stream:
                self.stream.stop()
            self.active_sector = sector_id
            info = SECTORS[sector_id]
            self.stream = VideoStreamEngine(source=info["source"], loop=True).start()
            time.sleep(0.4)
            ret, frame = self.stream.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                self.zone.set_preset_corridor(w, h, sector_id=sector_id)
            print(f"[C2-CORE] Initialized Sector {sector_id}: {info['name']}")

    def run_pipeline(self):
        fps_start = time.time()
        fps_frames = 0
        while self.running:
            if not self.stream:
                time.sleep(0.05)
                continue
                
            ret, frame = self.stream.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
                
            # Perception & Tracking
            processed_frame, dets, lat_ms = self.detector.detect(frame)
            
            # Tripwire Evaluation
            breaches = self.zone.evaluate_detections(dets)
            is_breached = len(breaches) > 0
            
            if is_breached:
                self.audio.trigger_breach_alert(intruder_count=len(breaches))
                for b in breaches:
                    self.logger.log_incident(frame, b, manual=False)
                    
            # Draw Zone & HUD
            self.zone.draw_zone(processed_frame, is_breached=is_breached)
            
            fps_frames += 1
            if time.time() - fps_start >= 1.0:
                self.current_fps = fps_frames / (time.time() - fps_start)
                fps_frames = 0
                fps_start = time.time()
                
            self.current_latency = lat_ms
            self.tracked_count = len(dets)
            self.active_breaches = breaches
            
            sec_name = SECTORS[self.active_sector]["name"]
            hud_frame = self.hud.draw_hud(
                processed_frame,
                detections=dets,
                active_breaches=breaches,
                fps=self.current_fps,
                latency_ms=lat_ms,
                clahe_on=self.detector.clahe_enabled,
                muted=self.audio.muted,
                sector_label=sec_name
            )
            
            # Encode to JPEG for fast HTTP streaming
            _, buf = cv2.imencode(".jpg", hud_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            self.latest_encoded_frame = buf.tobytes()
            time.sleep(0.01)

c2 = C2State()
pipe_thread = threading.Thread(target=c2.run_pipeline, daemon=True)
pipe_thread.start()

# API Models
class ActionPayload(BaseModel):
    sector: Optional[int] = None

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/api/sectors")
def get_sectors():
    res = []
    for sid, s in SECTORS.items():
        # Dynamic calculation of STSI based on live breach status
        stsi = s["stsi_base"]
        if sid == c2.active_sector and len(c2.active_breaches) > 0:
            stsi = min(98, stsi + len(c2.active_breaches) * 12)
        item = dict(s)
        item["stsi"] = stsi
        item["is_active"] = (sid == c2.active_sector)
        res.append(item)
    return res

@app.get("/api/telemetry")
def get_telemetry():
    sec_info = SECTORS[c2.active_sector]
    stsi = sec_info["stsi_base"]
    if len(c2.active_breaches) > 0:
        stsi = min(98, stsi + len(c2.active_breaches) * 12)
        
    return {
        "sector_id": c2.active_sector,
        "sector_name": sec_info["name"],
        "codename": sec_info["codename"],
        "fps": round(c2.current_fps, 1),
        "latency_ms": round(c2.current_latency, 1),
        "tracked_count": c2.tracked_count,
        "breach_count": len(c2.active_breaches),
        "is_breached": len(c2.active_breaches) > 0,
        "clahe_enabled": c2.detector.clahe_enabled,
        "audio_muted": c2.audio.muted,
        "stsi": stsi,
        "status": "CRITICAL INCURSION DETECTED" if len(c2.active_breaches) > 0 else sec_info["status"]
    }

@app.get("/api/stream")
def stream_video():
    def frame_generator():
        while True:
            if c2.latest_encoded_frame:
                yield (b"--frame\\r\\nContent-Type: image/jpeg\\r\\n\\r\\n" + c2.latest_encoded_frame + b"\\r\\n")
            time.sleep(0.033)
    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/evidence")
def get_evidence():
    ledger_path = os.path.join("evidence", "sec65b_evidence_ledger.json")
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                # Sort descending by timestamp
                return records[-30:][::-1]
        except Exception:
            return []
    return []

@app.post("/api/control/{action}")
def control_action(action: str, payload: Optional[ActionPayload] = None):
    if action == "switch_sector":
        if payload and payload.sector in SECTORS:
            c2.init_sector(payload.sector)
            return {"status": "success", "sector": payload.sector}
    elif action == "toggle_clahe":
        st = c2.detector.toggle_clahe()
        return {"status": "success", "clahe": st}
    elif action == "toggle_mute":
        st = c2.audio.toggle_mute()
        return {"status": "success", "muted": st}
    elif action == "capture_evidence":
        ret, frame = c2.stream.read() if c2.stream else (False, None)
        if ret and frame is not None:
            c2.logger.log_incident(frame, {"class_name": "MANUAL_OPERATOR_SWEEP", "track_id": 999, "confidence": 1.0}, manual=True)
            return {"status": "success", "message": "Forensic evidence committed with SHA-256 hash"}
    elif action == "reset_zone":
        c2.zone.clear()
        return {"status": "success", "message": "Exclusion polygon reset"}
    return JSONResponse({"status": "error", "message": "Invalid action"}, status_code=400)

# Serve evidence image files
app.mount("/evidence", StaticFiles(directory="evidence"), name="evidence")
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\\n" + "="*70)
    print(" PROJECT TRINETRA-C2 // AUTONOMOUS TACTICAL C2 WEB DASHBOARD")
    print(" Sponsoring Authority: Ministry of Home Affairs (MHA) | PS 26187")
    print(" Server Endpoint: http://localhost:8080")
    print("="*70 + "\\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8080, log_level="info")
"""

with open("server.py", "w", encoding="utf-8") as f:
    f.write(code)
print("server.py written successfully!")
