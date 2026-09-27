import cv2
import time
import math
import collections
import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from typing import Dict, List, Tuple, Optional

class PersonReIDEngine:
    """
    Project TRINETRA // Deep Appearance Person Re-Identification (ReID) Engine
    Extracts 576-dimensional normalized L2 metric embeddings from cropped person bounding boxes
    using an optimized MobileNetV3 deep neural feature extractor backbone.
    Enables persistent cross-camera subject tracking across disconnected surveillance nodes.
    """
    def __init__(self, device: str = "cpu", similarity_threshold: float = 0.70):
        self.device = torch.device(device)
        self.similarity_threshold = similarity_threshold
        
        # 1. Initialize Neural Feature Extractor Backbone
        try:
            self.model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
            self.model.classifier = torch.nn.Identity()
            self.model.to(self.device)
            self.model.eval()
            self.enabled = True
            print("[REID-ENGINE] MobileNetV3 Deep Appearance Backbone Loaded Successfully.")
        except Exception as e:
            print(f"[REID-ENGINE] Initialization error: {e}")
            self.enabled = False

        # 2. Standard ReID Image Preprocessing (Aspect Ratio ~1.75:1)
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((224, 128)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        self._embedding_cache: Dict[Any, Tuple[float, np.ndarray]] = {}

    def extract_embedding(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """Extracts 576D normalized appearance embedding for a single person crop."""
        if not self.enabled:
            return None

        h, w = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        
        # Clamp to frame bounds
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(x1 + 1, min(w, x2))
        y2 = max(y1 + 1, min(h, y2))
        
        bw = x2 - x1
        bh = y2 - y1
        if bw < 18 or bh < 36:
            return None  # Crop too small for reliable feature extraction

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        try:
            # Convert BGR (OpenCV) to RGB
            crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            tensor = self.transform(crop_rgb).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                feat = self.model(tensor)
                feat = torch.nn.functional.normalize(feat, p=2, dim=1)
                emb = feat.cpu().numpy()[0]
                return emb
        except Exception:
            return None

    def batch_extract_embeddings(self, frame: np.ndarray, detections: List[Dict]) -> List[Dict]:
        """Extracts appearance embeddings for all person detections, caching to avoid CPU churn."""
        now = time.time()
        for det in detections:
            if det.get("class_name") == "PERSON":
                tid = det.get("track_id")
                # Check cache (refresh every 3 seconds per track)
                cached = self._embedding_cache.get(tid)
                if cached and (now - cached[0] < 3.0):
                    det["reid_embedding"] = cached[1]
                else:
                    emb = self.extract_embedding(frame, det["bbox"])
                    det["reid_embedding"] = emb
                    if emb is not None and tid is not None:
                        self._embedding_cache[tid] = (now, emb)
            else:
                det["reid_embedding"] = None
        return detections


class GlobalEntity:
    """Represents a unique human subject tracked across multiple cameras."""
    def __init__(self, global_id: str, initial_embedding: np.ndarray, camera_id: int,
                 sector_name: str, bbox: Tuple[int, int, int, int], face_name: Optional[str] = None):
        self.global_id = global_id
        self.embedding = initial_embedding
        self.first_seen_time = time.time()
        self.last_seen_time = self.first_seen_time
        self.current_camera_id = camera_id
        self.current_sector_name = sector_name
        self.face_name = face_name
        self.sighting_count = 1
        
        # Log of cameras and timestamps where this entity was observed
        self.sightings: List[Dict] = [{
            "camera_id": camera_id,
            "sector_name": sector_name,
            "time": self.first_seen_time,
            "bbox": bbox
        }]
        
        # Inter-camera transit events
        self.transit_events: List[Dict] = []

    def update_observation(self, embedding: np.ndarray, camera_id: int, sector_name: str,
                           bbox: Tuple[int, int, int, int], face_name: Optional[str] = None) -> Optional[Dict]:
        """Updates rolling appearance embedding and detects inter-camera transit."""
        now = time.time()
        transit_event = None

        # Check for cross-camera transit
        if camera_id != self.current_camera_id:
            elapsed_sec = round(now - self.last_seen_time, 1)
            transit_event = {
                "global_id": self.global_id,
                "face_name": self.face_name or "UNIDENTIFIED SUBJECT",
                "from_camera": self.current_camera_id,
                "from_sector": self.current_sector_name,
                "to_camera": camera_id,
                "to_sector": sector_name,
                "elapsed_sec": elapsed_sec,
                "timestamp": now
            }
            self.transit_events.append(transit_event)
            self.current_camera_id = camera_id
            self.current_sector_name = sector_name

        # Rolling EMA update of appearance embedding (alpha = 0.3)
        if embedding is not None:
            self.embedding = 0.7 * self.embedding + 0.3 * embedding
            # Re-normalize
            norm = np.linalg.norm(self.embedding)
            if norm > 1e-6:
                self.embedding /= norm

        self.last_seen_time = now
        self.sighting_count += 1
        if face_name:
            self.face_name = face_name

        self.sightings.append({
            "camera_id": camera_id,
            "sector_name": sector_name,
            "time": now,
            "bbox": bbox
        })

        return transit_event


class GlobalEntityTracker:
    """
    Cross-Camera Re-Identification Manager.
    Correlates local tracker detections from disparate cameras into a unified global entity grid.
    """
    def __init__(self, similarity_threshold: float = 0.70, max_gallery_age_sec: float = 3600.0):
        self.similarity_threshold = similarity_threshold
        self.max_gallery_age = max_gallery_age_sec
        self.entities: Dict[str, GlobalEntity] = {}
        self.next_global_idx = 1
        self.transit_logs: collections.deque = collections.deque(maxlen=50)

    def match_or_create(self, embedding: Optional[np.ndarray], camera_id: int, sector_name: str,
                        bbox: Tuple[int, int, int, int], face_name: Optional[str] = None) -> Tuple[str, float, Optional[Dict]]:
        """
        Matches a detected subject against the global gallery via cosine similarity.
        Returns: (global_id, best_similarity_score, transit_event_if_crossed_camera)
        """
        if embedding is None:
            # Fallback: create or assign unfeatured ID
            gid = f"G-{self.next_global_idx:02d}"
            self.next_global_idx += 1
            return gid, 0.0, None

        best_sim = -1.0
        best_entity = None

        # Compare against all known global entities
        for gid, entity in self.entities.items():
            sim = float(np.dot(entity.embedding, embedding))
            if sim > best_sim:
                best_sim = sim
                best_entity = entity

        transit_alert = None
        if best_sim >= self.similarity_threshold and best_entity is not None:
            # Match confirmed! Update existing global entity
            transit_alert = best_entity.update_observation(embedding, camera_id, sector_name, bbox, face_name)
            if transit_alert:
                self.transit_logs.appendleft(transit_alert)
            return best_entity.global_id, best_sim, transit_alert
        else:
            # New subject entered surveillance zone
            gid = f"G-{self.next_global_idx:02d}"
            self.next_global_idx += 1
            new_ent = GlobalEntity(gid, embedding, camera_id, sector_name, bbox, face_name)
            self.entities[gid] = new_ent
            return gid, best_sim if best_sim > 0 else 1.0, None

    def prune_stale_entities(self):
        """Removes subjects not observed in any camera for more than max_gallery_age."""
        now = time.time()
        to_del = [gid for gid, ent in self.entities.items() if now - ent.last_seen_time > self.max_gallery_age]
        for gid in to_del:
            del self.entities[gid]

    def get_gallery_summary(self) -> List[Dict]:
        """Returns JSON-serializable list of all actively tracked global entities."""
        summary = []
        now = time.time()
        for gid, ent in self.entities.items():
            summary.append({
                "global_id": ent.global_id,
                "face_name": ent.face_name,
                "current_camera_id": ent.current_camera_id,
                "current_sector_name": ent.current_sector_name,
                "sighting_count": ent.sighting_count,
                "first_seen_str": time.strftime("%H:%M:%S", time.localtime(ent.first_seen_time)),
                "last_seen_sec_ago": round(now - ent.last_seen_time, 1),
                "transit_count": len(ent.transit_events),
                "latest_transit": ent.transit_events[-1] if ent.transit_events else None
            })
        summary.sort(key=lambda x: x["last_seen_sec_ago"])
        return summary
