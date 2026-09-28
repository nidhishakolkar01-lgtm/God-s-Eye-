import os
import cv2
import time
import glob
import numpy as np
from typing import List, Dict, Tuple, Optional

class FaceRecognitionEngine:
    """
    Project TRINETRA // Real-Time Deep Face Recognition Engine
    Inspired by PySource's real-time face recognition architecture, powered by:
      - OpenCV YuNet (FaceDetectorYN): Ultra-fast (>100 FPS) deep face detector
      - OpenCV SFace (FaceRecognizerSF): 128-dimensional deep metric face recognizer
      - Cosine distance metric matching against known enrolled identities
    """
    def __init__(self, 
                 models_dir: str = "models", 
                 known_faces_dir: str = "known_faces",
                 cosine_threshold: float = 0.28):
        self.models_dir = models_dir
        self.known_faces_dir = known_faces_dir
        self.cosine_threshold = cosine_threshold
        
        self.yunet_path = os.path.join(models_dir, "face_detection_yunet_2023mar.onnx")
        self.sface_path = os.path.join(models_dir, "face_recognition_sface_2021dec.onnx")
        
        self.detector = None
        self.recognizer = None
        self.enabled = False
        
        self.known_names: List[str] = []
        self.known_features: List[np.ndarray] = []
        self.known_meta: List[Dict] = []
        
        # High value targets / personnel metadata
        self.hvt_watchlists = {
            "NIDHISH AMITABH AKOLKAR": {"risk": "C2 COMMAND OPERATOR", "clearance": "LEVEL 5 MASTER CLEARANCE"},
            "OFFICER SHARMA": {"risk": "FRIENDLY SENTRY", "clearance": "AUTHORIZED BORDER PATROL"}
        }

        self._init_models()
        self.reload_known_faces()

    def _init_models(self):
        try:
            if not os.path.exists(self.yunet_path) or not os.path.exists(self.sface_path):
                print(f"[FACE-ENGINE] Models missing at {self.models_dir}. Face recognition disabled.")
                return

            self.detector = cv2.FaceDetectorYN.create(
                model=self.yunet_path,
                config="",
                input_size=(320, 320),
                score_threshold=0.30,
                nms_threshold=0.3,
                top_k=5000
            )

            self.recognizer = cv2.FaceRecognizerSF.create(
                model=self.sface_path,
                config=""
            )
            self.enabled = True
            print("[FACE-ENGINE] YuNet and SFace Neural Models Loaded Successfully.")
        except Exception as e:
            print(f"[FACE-ENGINE] Initialization error: {e}")
            self.enabled = False

    def reload_known_faces(self):
        """Scans the known_faces/ folder and builds 128D deep feature embeddings."""
        if not self.enabled:
            return

        self.known_names.clear()
        self.known_features.clear()
        self.known_meta.clear()
        
        os.makedirs(self.known_faces_dir, exist_ok=True)
        image_extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp")
        files = []
        for ext in image_extensions:
            files.extend(glob.glob(os.path.join(self.known_faces_dir, ext)))

        print(f"[FACE-ENGINE] Enrolling faces from '{self.known_faces_dir}' ({len(files)} files found)...")
        
        for fpath in files:
            name = os.path.splitext(os.path.basename(fpath))[0].replace("_", " ").title()
            img = cv2.imread(fpath)
            if img is None:
                continue
            
            # Detect face in enrolled photo
            h, w = img.shape[:2]
            self.detector.setInputSize((w, h))
            ret, faces = self.detector.detect(img)
            
            if ret and faces is not None and len(faces) > 0:
                face = faces[0]  # Take the most prominent face
                aligned = self.recognizer.alignCrop(img, face)
                feat = self.recognizer.feature(aligned)
                
                self.known_names.append(name.upper())
                self.known_features.append(feat)
                meta = self.hvt_watchlists.get(name.upper(), {
                    "risk": "ENROLLED SUBJECT",
                    "clearance": "PERSONNEL IDENTIFIED"
                })
                self.known_meta.append(meta)
                print(f"[FACE-ENGINE] Enrolled: '{name.upper()}' from {os.path.basename(fpath)}")
            else:
                print(f"[FACE-ENGINE] Warning: No face detected in {os.path.basename(fpath)}")

        print(f"[FACE-ENGINE] Enrollment complete. Total enrolled identities: {len(self.known_names)}")

    def enroll_face(self, image: np.ndarray, name: str, save_to_disk: bool = True) -> Dict:
        """Dynamically enrolls a new face from a live camera frame or uploaded image."""
        if not self.enabled:
            return {"status": "error", "message": "Face recognition engine not initialized"}
        if image is None or image.size == 0:
            return {"status": "error", "message": "Invalid image data"}

        clean_name = name.strip().replace("_", " ").upper()
        h, w = image.shape[:2]
        self.detector.setInputSize((w, h))
        ret, faces = self.detector.detect(image)

        if not ret or faces is None or len(faces) == 0:
            return {"status": "error", "message": "No face detected in captured frame. Ensure adequate lighting and front-facing angle."}

        # Take largest face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        aligned = self.recognizer.alignCrop(image, largest_face)
        feat = self.recognizer.feature(aligned)

        # Update in-memory database
        self.known_names.append(clean_name)
        self.known_features.append(feat)
        self.known_meta.append({
            "risk": "OPERATOR ENROLLED SUBJECT",
            "clearance": "LIVE FIELD ENROLLED"
        })

        if save_to_disk:
            filename = clean_name.replace(" ", "_").lower() + ".jpg"
            out_path = os.path.join(self.known_faces_dir, filename)
            cv2.imwrite(out_path, image)
            print(f"[FACE-ENGINE] Saved new face portrait: {out_path}")

        return {
            "status": "success",
            "name": clean_name,
            "message": f"Successfully enrolled '{clean_name}' into God's Eye Biometric Grid."
        }

    def recognize_faces(self, frame: np.ndarray) -> List[Dict]:
        """
        Executes real-time face detection, alignment, feature extraction, and cosine matching.
        Returns list of detected face dictionaries.
        """
        if not self.enabled or frame is None or frame.size == 0:
            return []

        orig_h, orig_w = frame.shape[:2]
        
        # Optimize inference: scale down to 320px for sub-8ms deep face detection
        target_w = min(orig_w, 320)
        scale = target_w / float(orig_w)
        target_h = int(orig_h * scale)

        if scale < 1.0:
            det_img = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        else:
            det_img = frame

        self.detector.setInputSize((target_w, target_h))
        ret, faces = self.detector.detect(det_img)

        results = []
        if not ret or faces is None:
            return results

        # Process top 3 most prominent faces to keep CPU fast and responsive
        if len(faces) > 3:
            faces = sorted(faces, key=lambda f: f[14], reverse=True)[:3]

        inv_scale = 1.0 / scale if scale > 0 else 1.0

        for face_data in faces:
            # face_data: [x, y, w, h, x_re, y_re, x_le, y_le, x_nt, y_nt, x_rcm, y_rcm, x_lcm, y_lcm, score]
            box_x = int(face_data[0] * inv_scale)
            box_y = int(face_data[1] * inv_scale)
            box_w = int(face_data[2] * inv_scale)
            box_h = int(face_data[3] * inv_scale)
            det_score = float(face_data[14])

            # Scale face landmarks
            landmarks = []
            for i in range(4, 14, 2):
                lx = int(face_data[i] * inv_scale)
                ly = int(face_data[i + 1] * inv_scale)
                landmarks.append((lx, ly))

            # Scaled face vector for full-resolution alignment
            full_res_face = face_data.copy()
            full_res_face[0:4] *= inv_scale
            full_res_face[4:14] *= inv_scale

            # Align face & extract 128D feature embedding
            aligned_face = self.recognizer.alignCrop(frame, full_res_face)
            feat = self.recognizer.feature(aligned_face)

            # Match against known enrolled faces
            best_match_name = "UNKNOWN"
            best_score = 0.0
            best_meta = {"risk": "UNIDENTIFIED SUBJECT", "clearance": "RESTRICTED ACCESS"}
            is_matched = False

            if len(self.known_features) > 0:
                for idx, known_feat in enumerate(self.known_features):
                    score = self.recognizer.match(feat, known_feat, cv2.FaceRecognizerSF_FR_COSINE)
                    if score > best_score:
                        best_score = score
                        if score >= self.cosine_threshold:
                            best_match_name = self.known_names[idx]
                            best_meta = self.known_meta[idx]
                            is_matched = True

            # Calibrate confidence percentage for display
            if is_matched:
                pct = min(99.4, 70.0 + (best_score - self.cosine_threshold) * 60.0)
            else:
                pct = max(15.0, min(65.0, det_score * 70.0))

            results.append({
                "name": best_match_name,
                "is_known": is_matched,
                "similarity_score": round(float(best_score), 4),
                "confidence_pct": round(float(pct), 1),
                "bbox": (box_x, box_y, box_w, box_h),
                "landmarks": landmarks,
                "meta": best_meta
            })

        return results
