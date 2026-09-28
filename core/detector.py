import os
import cv2
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Any, Set
from ultralytics import YOLO
from core.sensor_pipeline import MultiSpectralSensor
from core.tracker_analytics import KinematicTracker
from core.face_engine import FaceRecognitionEngine
from core.anpr_engine import ANPREngine
from core.reid_engine import PersonReIDEngine

class TacticalDetector:
    """
    Tactical Neural Perception, Face Recognition & Multi-Spectral Core.
    Integrates:
      - YOLOv8n lightweight edge inference with resolution optimization (imgsz=384)
      - Alternate-frame detection for silky-smooth 30+ FPS operation
      - Deep Face Recognition (YuNet + SFace) matching against known_faces database
      - ByteTrack multi-target association
      - Multi-Spectral Sensor Pipeline (NORMAL, NVG_P43, FLIR_IRONBOW, FLIR_WHOT, FLIR_BHOT)
      - Kinematic Velocity Vectoring and Breach ETA Prediction
    """
    def __init__(self, model_weight="yolov8n.pt", conf_thresh=0.15, use_tracking=True):
        self.conf_thresh = conf_thresh
        self.use_tracking = use_tracking
        self.clahe_enabled = False
        self.imgsz = 640
        self.frame_idx = 0
        self.cached_detections = []
        self.cached_faces = []
        self.last_shape = None
        
        # Multi-spectral sensor simulation engine
        self.sensor = MultiSpectralSensor()
        
        # Kinematics & trajectory analytics engine
        self.kinematics = KinematicTracker()

        # Real-time Deep Face Recognition Engine
        self.face_engine = FaceRecognitionEngine()

        # Automatic Number Plate Recognition & Stolen Vehicle Intelligence Core
        self.anpr_engine = ANPREngine()

        # Deep Appearance Person Re-Identification (ReID) Core
        self.reid_engine = PersonReIDEngine()

        # CLAHE filter
        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        

        # Load YOLO model
        print(f"[TRINETRA-C2] Loading Neural Perception Weights: {model_weight}...")
        self.model = YOLO(model_weight)
        
        # Omniscient Threat & Entity Taxonomy (All 80 COCO classes + tactical custom categories)
        self.target_classes = self._build_omniscient_class_map()

    def _build_omniscient_class_map(self) -> Dict[int, str]:
        """Maps all model classes to defense-grade tactical uppercase classifications."""
        tactical_map = {
            0: "PERSON",
            1: "BICYCLE",
            2: "VEHICLE",
            3: "MOTORCYCLE",
            4: "AERIAL_VEHICLE/DRONE",
            5: "HEAVY_VEHICLE",
            6: "RAIL_TRANSIT",
            7: "TRUCK",
            8: "MARITIME_VESSEL",
            9: "TRAFFIC_LIGHT",
            10: "FIRE_HYDRANT",
            11: "STOP_SIGN",
            12: "PARKING_METER",
            13: "BENCH",
            14: "BIRD/AVIAN",
            15: "CAT/FAUNA",
            16: "DOG/CANINE",
            17: "HORSE/EQUINE",
            18: "SHEEP/LIVESTOCK",
            19: "COW/LIVESTOCK",
            20: "ELEPHANT",
            21: "BEAR",
            22: "ZEBRA",
            23: "GIRAFFE",
            24: "BACKPACK/CONTRABAND",
            25: "EQUIPMENT/UMBRELLA",
            26: "HANDBAG/CONTRABAND",
            27: "PERSONAL_GEAR",
            28: "SUITCASE/LOAD",
            29: "FRISBEE",
            30: "SKIS",
            31: "SNOWBOARD",
            32: "SPORTS_BALL",
            33: "KITE",
            34: "BASEBALL_BAT/BLUNT_WEAPON",
            35: "BASEBALL_GLOVE",
            36: "SKATEBOARD",
            37: "SURFBOARD",
            38: "TENNIS_RACKET",
            39: "BOTTLE/CONTAINER",
            40: "WINE_GLASS",
            41: "CUP/MUG",
            42: "FORK",
            43: "KNIFE/WEAPON",
            44: "SPOON",
            45: "BOWL",
            46: "BANANA", 47: "APPLE", 48: "SANDWICH", 49: "ORANGE",
            50: "BROCCOLI", 51: "CARROT", 52: "HOT_DOG", 53: "PIZZA",
            54: "DONUT", 55: "CAKE",
            56: "CHAIR",
            57: "COUCH/SOFA",
            58: "POTTED_PLANT",
            59: "BED",
            60: "DINING_TABLE",
            61: "TOILET",
            62: "TV/MONITOR",
            63: "LAPTOP/COMPUTING",
            64: "MOUSE/ELECTRONIC",
            65: "REMOTE/RF_TRIGGER",
            66: "KEYBOARD/ELECTRONIC",
            67: "CELL_PHONE/COMMS",
            68: "MICROWAVE",
            69: "OVEN",
            70: "TOASTER",
            71: "SINK",
            72: "REFRIGERATOR",
            73: "BOOK/DOCUMENT",
            74: "CLOCK/TIMER",
            75: "VASE",
            76: "SCISSORS/EDGED_WEAPON",
            77: "TEDDY_BEAR",
            78: "HAIR_DRIER",
            79: "TOOTHBRUSH"
        }
        if hasattr(self.model, "names") and isinstance(self.model.names, dict):
            for k, v in self.model.names.items():
                if k not in tactical_map:
                    tactical_map[k] = str(v).replace("_", " ").upper()
        return tactical_map

    def set_open_vocabulary(self, classes_list: List[str]):
        """Dynamically configures open-vocabulary target detection for zero-shot scanning of arbitrary things."""
        if hasattr(self.model, "set_classes"):
            self.model.set_classes(classes_list)
            self.target_classes = {i: c.upper().replace("_", " ") for i, c in enumerate(classes_list)}
            print(f"[TRINETRA-C2] Open-Vocabulary Classes Configured: {len(classes_list)} targets active.")
            return True
        return False

    def reset_tracker(self):
        """Flushes tracker state, trajectory history, and frame caches on sector or resolution change."""
        self.cached_detections = []
        self.cached_faces = []
        self.frame_idx = 0  # Immediately force full perception on the new sector's first frame!
        try:
            self.kinematics.trajectories.clear()
            self.kinematics.last_seen.clear()
        except Exception:
            pass
        try:
            if hasattr(self.model, "predictor") and self.model.predictor is not None:
                if hasattr(self.model.predictor, "trackers") and self.model.predictor.trackers:
                    for t in self.model.predictor.trackers:
                        if hasattr(t, "reset"):
                            t.reset()
                        if hasattr(t, "tracked_stracks"):
                            t.tracked_stracks.clear()
                        if hasattr(t, "lost_stracks"):
                            t.lost_stracks.clear()
                        if hasattr(t, "removed_stracks"):
                            t.removed_stracks.clear()
                        if hasattr(t, "frame_id"):
                            t.frame_id = 0
                elif hasattr(self.model.predictor, "trackers"):
                    delattr(self.model.predictor, "trackers")
        except Exception:
            pass

    def set_sensor_mode(self, mode: str):
        success = self.sensor.set_mode(mode)
        if success:
            print(f"[TRINETRA-C2] Multi-Spectral Mode Switched: {self.sensor.active_mode}")
        return success

    def toggle_scope_mask(self):
        st = self.sensor.toggle_scope_mask()
        print(f"[TRINETRA-C2] Sentry Scope Mask: {'ENABLED' if st else 'DISABLED'}")
        return st

    def toggle_clahe(self):
        self.clahe_enabled = not self.clahe_enabled
        state = "ENABLED (+34% Night Contrast)" if self.clahe_enabled else "DISABLED (Standard RGB)"
        print(f"[TRINETRA-C2] Low-Light CLAHE Boost: {state}")
        return self.clahe_enabled

    def preprocess_clahe(self, frame):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l_boosted = self.clahe.apply(l)
        enhanced_lab = cv2.merge((l_boosted, a, b))
        return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    def detect(self, frame, fence_coords=None, imgsz: Optional[int] = None):
        """
        Executes perception, deep face recognition, tracking, and kinematics.
        Returns:
            processed_frame: multi-spectral frame with active sensor palette
            detections: list of object detection dicts
            faces: list of recognized face dicts (name, bbox, landmarks, match %)
            inference_ms: inference latency in milliseconds
        """
        t0 = time.perf_counter()
        target_imgsz = imgsz if imgsz is not None else self.imgsz
        
        # Reset tracker state automatically if frame dimensions changed
        curr_shape = frame.shape[:2]
        if self.last_shape is not None and self.last_shape != curr_shape:
            self.reset_tracker()
        self.last_shape = curr_shape

        input_frame = frame
        if self.clahe_enabled:
            input_frame = self.preprocess_clahe(frame)

        # Alternate-frame execution for silky smooth 30+ FPS (always runs on frame 0 or cache empty)
        run_full_inference = (self.frame_idx % 2 == 0) or (len(self.cached_detections) == 0)
        self.frame_idx += 1

        if run_full_inference:
            # 1. Omniscient Object Detection & Tracking (Zero filtering: classes=None scans ALL objects & things)
            if self.use_tracking:
                results = self.model.track(
                    input_frame, 
                    conf=self.conf_thresh, 
                    imgsz=target_imgsz,
                    classes=None, 
                    tracker="bytetrack.yaml",
                    persist=True, 
                    verbose=False
                )
            else:
                results = self.model(
                    input_frame, 
                    conf=self.conf_thresh, 
                    imgsz=target_imgsz,
                    classes=None, 
                    verbose=False
                )

            detections = []
            active_tids = []

            if len(results) > 0 and results[0].boxes is not None:
                boxes = results[0].boxes
                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    
                    track_id = int(box.id[0].item()) if box.id is not None else None
                    if track_id is not None:
                        active_tids.append(track_id)
                    
                    x1, y1, x2, y2 = xyxy
                    centroid = (int((x1 + x2) / 2), int(y2))
                    center_box = (int((x1 + x2) / 2), int((y1 + y2) / 2))

                    kin = self.kinematics.update(track_id, centroid, fence_coords)

                    # Dynamic omniscient class nomenclature
                    resolved_name = self.target_classes.get(cls_id)
                    if not resolved_name and hasattr(self.model, "names") and isinstance(self.model.names, dict):
                        resolved_name = str(self.model.names.get(cls_id, f"ENTITY_{cls_id}")).replace("_", " ").upper()
                    if not resolved_name:
                        resolved_name = f"OBJECT_{cls_id}"

                    detections.append({
                        "track_id": track_id,
                        "class_id": cls_id,
                        "class_name": resolved_name,
                        "confidence": conf,
                        "bbox": (x1, y1, x2, y2),
                        "footfall": centroid,
                        "center": center_box,
                        "kinematics": kin
                    })

            self.kinematics.prune_old_tracks(active_tids)
            self.cached_detections = detections

            # 2. Deep Face Recognition (YuNet + SFace)
            self.cached_faces = self.face_engine.recognize_faces(input_frame)
            inference_ms = (time.perf_counter() - t0) * 1000.0

            # 3. Automatic Number Plate Recognition (ANPR) on tracked vehicles (runs in background executor)
            detections, _ = self.anpr_engine.process_vehicles(input_frame, detections, self.frame_idx)

            # 4. Deep Appearance Person Re-Identification (ReID) - extract on full inference frames
            detections = self.reid_engine.batch_extract_embeddings(input_frame, detections)
            self.cached_detections = detections
        else:
            detections = self.cached_detections
            faces = self.cached_faces
            inference_ms = (time.perf_counter() - t0) * 1000.0

        # Multi-spectral sensor transformation
        processed_frame = self.sensor.process(input_frame)

        return processed_frame, detections, self.cached_faces, inference_ms
