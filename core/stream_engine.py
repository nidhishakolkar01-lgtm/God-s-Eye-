import os
import cv2
import time
import threading
import numpy as np
from typing import Union, Tuple, Optional

# Enable ultra-low latency TCP transport for RTSP feeds across the platform
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|fflags;nobuffer|max_delay;0"

class VideoStreamEngine:
    """
    High-Performance Zero-Lag Threaded Video Stream Reader.
    Features:
      - Direct support for Local Webcams (Device 0, 1, 2 via DirectShow)
      - Real-time IP Webcams & Drone RTSP Streams with zero buffer buildup
      - Smooth looped playback for border surveillance footage
      - Dedicated async frame grabbing to ensure consumer always receives newest real-time frame
    """
    def __init__(self, source: Union[int, str] = 0, loop: bool = True):
        self.source = source
        self.loop = loop
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.lock = threading.Lock()
        self.new_frame_event = threading.Event()
        
        self.current_frame: Optional[np.ndarray] = None
        self.fps = 30.0
        self.width = 1280
        self.height = 720
        self.total_frames = 0
        self.frame_idx = 0
        self.is_live = False
        
        self._init_source()

    def _init_source(self):
        src = self.source
        if isinstance(src, str) and src.isdigit():
            src = int(src)

        # Detect if live stream (webcam, rtsp, or http)
        if isinstance(src, int):
            self.is_live = True
            # On Windows, DirectShow is fast & non-blocking
            self.cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(src)
        else:
            str_src = str(src).lower()
            if str_src.startswith("rtsp://") or str_src.startswith("http://") or str_src.startswith("https://") or str_src.startswith("udp://"):
                self.is_live = True
                self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
            else:
                self.is_live = False
                self.cap = cv2.VideoCapture(src)

        if not self.cap or not self.cap.isOpened():
            print(f"[STREAM-ENGINE] Connecting to live source: {self.source} ...")
            placeholder = np.zeros((720, 1280, 3), dtype=np.uint8)
            cv2.putText(placeholder, f"SYNCHRONIZING SENTRY FEED: {self.source}", (40, 360),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 240, 255), 2)
            self.current_frame = placeholder
            self.fps = 30.0
            self.width = 1280
            self.height = 720
            return

        # Optimize buffer for live cameras
        if self.is_live:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        if self.fps <= 0 or self.fps > 120:
            self.fps = 30.0

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not self.is_live else 0
        print(f"[STREAM-ENGINE] Connected: source={self.source} | live={self.is_live} | {self.width}x{self.height} @ {self.fps:.1f} FPS")

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()
        return self

    def _capture_worker(self):
        frame_interval = 1.0 / max(self.fps, 10.0)
        
        while self.running:
            t_start = time.perf_counter()

            # Handle reconnection if cap not opened initially
            if not self.cap or not self.cap.isOpened():
                time.sleep(0.5)
                src = self.source
                if isinstance(src, str) and (src.startswith("rtsp://") or src.startswith("http://") or src.startswith("udp://")):
                    self.cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
                else:
                    self.cap = cv2.VideoCapture(src)
                if self.cap and self.cap.isOpened():
                    if self.is_live:
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    print(f"[STREAM-ENGINE] Reconnected to live stream: {self.source}")
                continue

            # For live streams, use grab/retrieve for zero-lag pipeline
            if self.is_live:
                if self.cap.grab():
                    ret, frame = self.cap.retrieve()
                    if ret and frame is not None:
                        with self.lock:
                            self.current_frame = frame
                            self.frame_idx += 1
                        self.new_frame_event.set()
                else:
                    time.sleep(0.01)
            else:
                # Video file playback
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    if self.loop and self.total_frames > 0:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        self.frame_idx = 0
                        time.sleep(0.01)
                        continue
                    else:
                        break

                with self.lock:
                    self.current_frame = frame
                    self.frame_idx += 1
                self.new_frame_event.set()

                # For video files, throttle to natural playback speed
                elapsed = time.perf_counter() - t_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0.001:
                    time.sleep(sleep_time)

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Returns the freshest unread or latest frame without buffer delay."""
        with self.lock:
            if self.current_frame is None:
                return False, None
            return True, self.current_frame.copy()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=0.5)
        if self.cap and self.cap.isOpened():
            self.cap.release()
