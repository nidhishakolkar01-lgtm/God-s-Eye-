import cv2
import time
import threading
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from core.stream_engine import VideoStreamEngine

class CameraNetworkManager:
    """
    Project TRINETRA // Multi-Node CCTV Stream & Sentry Network Manager
    Manages concurrent RTSP feeds, HTTP MJPEG, USB webcams, and pre-recorded border corridor streams.
    Enables dynamic runtime camera onboarding, stream auto-reconnect, and 2x2 composite matrix rendering.
    """
    def __init__(self, initial_sectors: Dict[int, Dict]):
        self.lock = threading.Lock()
        self.streams: Dict[int, VideoStreamEngine] = {}
        self.camera_info: Dict[int, Dict] = {}
        self.active_camera_id: int = 1
        self.default_sector_ids = set(initial_sectors.keys())
        
        # Initialize default cameras
        for sid, sec in initial_sectors.items():
            self.register_camera(
                camera_id=sid,
                name=sec["name"],
                codename=sec["codename"],
                source=sec["source"],
                cam_type=sec["type"],
                lat=sec["lat"],
                lng=sec["lng"],
                mgrs=sec["mgrs"],
                auto_start=(sid == 1)
            )

    def register_camera(self, camera_id: int, name: str, codename: str, source: Any,
                        cam_type: str, lat: float = 31.604, lng: float = 74.572,
                        mgrs: str = "43R EQ 5940 9662", auto_start: bool = False) -> Dict:
        """Registers a new camera node (RTSP, Phone IP, USB webcam, or video)."""
        with self.lock:
            # Parse integer webcam source if numeric string
            if isinstance(source, str) and source.isdigit():
                source = int(source)

            protocol = "USB/LOCAL"
            src_str = str(source).lower()
            if src_str.startswith("rtsp://"):
                protocol = "RTSP (H.264/H.265)"
            elif src_str.startswith("http://") or src_str.startswith("https://"):
                protocol = "HTTP/MJPEG/HLS"
            elif src_str.endswith(".mp4") or src_str.endswith(".avi") or src_str.endswith(".mkv"):
                protocol = "SIMULATED SENTRY FILE"

            info = {
                "id": camera_id,
                "name": name,
                "codename": codename,
                "source": source,
                "type": cam_type,
                "protocol": protocol,
                "lat": lat,
                "lng": lng,
                "mgrs": mgrs,
                "is_active": False,
                "fps": 0.0,
                "resolution": "854x480",
                "last_frame_time": 0.0,
                "status": "STANDBY"
            }
            self.camera_info[camera_id] = info
            
            if auto_start:
                self._start_stream_locked(camera_id)
                
            return info

    def add_custom_camera(self, name: str, source: str, cam_type: str = "OPTICAL CCTV",
                          lat: float = 31.604, lng: float = 74.572, mgrs: str = "43R EQ 5940 9662") -> Dict:
        """Dynamically registers and provisions a new camera stream at runtime."""
        with self.lock:
            # Generate next available ID
            existing_ids = list(self.camera_info.keys())
            next_id = max(existing_ids) + 1 if existing_ids else 1
            codename = f"TRINETRA-CCTV-NODE-{next_id:02d}"

        return self.register_camera(
            camera_id=next_id,
            name=name,
            codename=codename,
            source=source,
            cam_type=cam_type,
            lat=lat,
            lng=lng,
            mgrs=mgrs,
            auto_start=False
        )

    def remove_custom_camera(self, camera_id: int) -> bool:
        """Removes a camera stream and stops its worker."""
        with self.lock:
            if camera_id not in self.camera_info:
                return False
            # Prevent removing initial default sectors
            if camera_id in self.default_sector_ids:
                return False

            if camera_id in self.streams:
                try:
                    self.streams[camera_id].stop()
                except Exception:
                    pass
                del self.streams[camera_id]

            del self.camera_info[camera_id]
            if self.active_camera_id == camera_id:
                self.active_camera_id = 1
            return True

    def _start_stream_locked(self, camera_id: int):
        """Starts stream acquisition thread for a camera."""
        info = self.camera_info.get(camera_id)
        if not info:
            return

        if camera_id in self.streams:
            self.streams[camera_id].stop()

        try:
            stream = VideoStreamEngine(source=info["source"], loop=True).start()
            self.streams[camera_id] = stream
            info["is_active"] = True
            info["status"] = "LIVE ONLINE"
            info["resolution"] = f"{stream.width}x{stream.height}"
            info["fps"] = round(stream.fps, 1)
            print(f"[CAM-MANAGER] Started stream for Cam #{camera_id}: {info['name']} ({info['protocol']})")
        except Exception as e:
            info["status"] = f"ERROR: {e}"
            info["is_active"] = False

    def assign_slot_stream(self, slot_id: int, source: Any, name: str, codename: str,
                           lat: float = 31.604, lng: float = 74.572,
                           mgrs: str = "43R EQ 5940 9662", cam_type: str = "OPTICAL SENTRY",
                           set_as_primary: bool = False) -> Dict:
        """
        Dynamically reassigns a 2x2 matrix slot (1-4) or primary feed to a specified stream source.
        Gracefully replaces the running stream engine for that slot without disrupting other channels.
        """
        with self.lock:
            if isinstance(source, str) and source.isdigit():
                source = int(source)

            if slot_id in self.streams:
                try:
                    self.streams[slot_id].stop()
                except Exception as e:
                    print(f"[CAM-MANAGER] Error stopping previous stream for slot {slot_id}: {e}")

            protocol = "RTSP" if str(source).startswith("rtsp://") else "OPTICAL"
            info = {
                "id": slot_id,
                "name": name,
                "codename": codename,
                "source": source,
                "type": cam_type,
                "protocol": protocol,
                "lat": lat,
                "lng": lng,
                "mgrs": mgrs,
                "is_active": (slot_id == self.active_camera_id or set_as_primary),
                "fps": 0.0,
                "resolution": "854x480",
                "last_frame_time": 0.0,
                "status": "LIVE ONLINE"
            }
            self.camera_info[slot_id] = info
            self._start_stream_locked(slot_id)

            if set_as_primary:
                self.active_camera_id = slot_id

            print(f"[CAM-MANAGER] Slot #{slot_id} reassigned to {name} ({source})")
            return info

    def activate_camera(self, camera_id: int):
        """Switches primary active focus camera and releases other live network connections."""
        with self.lock:
            if camera_id not in self.camera_info:
                return False
            
            for cid, s in list(self.streams.items()):
                if cid != camera_id:
                    src_str = str(self.camera_info.get(cid, {}).get("source", "")).lower()
                    if src_str.startswith("rtsp://") or src_str.startswith("http://"):
                        try:
                            s.stop()
                        except Exception:
                            pass
                        self.streams.pop(cid, None)
                        if cid in self.camera_info:
                            self.camera_info[cid]["is_active"] = False

            self.active_camera_id = camera_id
            if camera_id not in self.streams or not self.streams[camera_id].running:
                self._start_stream_locked(camera_id)
            return True

    def get_frame(self, camera_id: int) -> Tuple[bool, Optional[np.ndarray]]:
        """Retrieves latest fresh frame from specified camera."""
        with self.lock:
            stream = self.streams.get(camera_id)
            if not stream:
                if camera_id in self.camera_info:
                    self._start_stream_locked(camera_id)
                    stream = self.streams.get(camera_id)
            
            if stream:
                return stream.read()
            return False, None

    def probe_local_video_devices(self) -> List[Dict[str, Any]]:
        """Scans for accessible local video capture indexes (USB webcams / virtual capture devices)."""
        available = []
        for dev_idx in range(4):
            cap = cv2.VideoCapture(dev_idx, cv2.CAP_DSHOW if hasattr(cv2, 'CAP_DSHOW') else cv2.CAP_ANY)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    h, w = frame.shape[:2]
                    available.append({
                        "index": dev_idx,
                        "name": f"USB Video Capture Device #{dev_idx}",
                        "resolution": f"{w}x{h}",
                        "type": "OPTICAL USB SENSOR"
                    })
                cap.release()
        return available

    def render_multiview_matrix(self, target_w: int = 1280, target_h: int = 720) -> np.ndarray:
        """
        Renders a 2x2 multi-camera composite sentry matrix for simultaneous multi-node surveillance.
        """
        matrix = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        half_w = target_w // 2
        half_h = target_h // 2

        cams = list(self.camera_info.keys())[:4]
        positions = [
            (0, 0, half_w, half_h),
            (half_w, 0, half_w, half_h),
            (0, half_h, half_w, half_h),
            (half_w, half_h, half_w, half_h)
        ]

        for i, cid in enumerate(cams):
            gx, gy, gw, gh = positions[i]
            info = self.camera_info[cid]
            ret, frame = self.get_frame(cid)

            if ret and frame is not None:
                resized = cv2.resize(frame, (gw, gh))
            else:
                resized = np.zeros((gh, gw, 3), dtype=np.uint8)
                cv2.putText(resized, f"CAM #{cid} STANDBY / CONNECTING...", (20, gh // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 240, 255), 1, cv2.LINE_AA)

            # Header banner
            cv2.rectangle(resized, (0, 0), (gw, 24), (10, 14, 18), -1)
            is_primary = (cid == self.active_camera_id)
            title_col = (0, 255, 119) if is_primary else (0, 240, 255)
            badge_text = f"CAM #{cid} // {info['name'][:24]} | {info.get('protocol', 'OPTICAL')}"
            if is_primary:
                badge_text += " [PRIMARY]"
            cv2.putText(resized, badge_text, (8, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.32, title_col, 1, cv2.LINE_AA)

            # Border
            border_col = (0, 255, 119) if is_primary else (40, 50, 60)
            cv2.rectangle(resized, (0, 0), (gw - 1, gh - 1), border_col, 2 if is_primary else 1)

            matrix[gy:gy + gh, gx:gx + gw] = resized

        # Divider crosshairs
        cv2.line(matrix, (half_w, 0), (half_w, target_h), (0, 240, 255), 1, cv2.LINE_AA)
        cv2.line(matrix, (0, half_h), (target_w, half_h), (0, 240, 255), 1, cv2.LINE_AA)

        return matrix

    def get_cameras_summary(self) -> List[Dict]:
        """Returns JSON-serializable list of all registered cameras."""
        with self.lock:
            result = []
            for cid, info in self.camera_info.items():
                is_streaming = (cid in self.streams and self.streams[cid].running)
                item = dict(info)
                item["is_active"] = (cid == self.active_camera_id)
                item["is_streaming"] = is_streaming
                result.append(item)
            return result

    def stop_all(self):
        """Stops all background camera threads."""
        with self.lock:
            for stream in self.streams.values():
                stream.stop()
            self.streams.clear()
