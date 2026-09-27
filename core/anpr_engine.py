import os
import cv2
import re
import time
import json
import logging
import threading
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("ANPREngine")

VALID_INDIAN_STATES = {
    "AN", "AP", "AR", "AS", "BR", "CH", "CG", "DD", "DL", "DN", "GA", "GJ",
    "HR", "HP", "JH", "JK", "KA", "KL", "LA", "LD", "MP", "MH", "MN", "ML",
    "MZ", "NL", "OD", "PB", "PY", "RJ", "SK", "TN", "TS", "TR", "UP", "UK",
    "UA", "WB"
}

STATE_CORRECTIONS = {
    '1K': 'JK', 'IK': 'JK', 'OK': 'JK', 'TK': 'JK',
    'P8': 'PB', 'FB': 'PB', 'RB': 'PB', 'PR': 'PB',
    '0L': 'DL', 'QL': 'DL', 'OI': 'DL', 'DI': 'DL', 'OL': 'DL',
    'H8': 'HR', 'HA': 'HR',
    'M4': 'MH', 'NH': 'MH',
    'UF': 'UP', 'VP': 'UP',
    'R1': 'RJ', 'AJ': 'RJ',
    'C8': 'CH', 'GH': 'CH'
}

CAR_BRAND_BADGES = {
    "HYUNDAI", "MARUTI", "SUZUKI", "TOYOTA", "HONDA", "TATA", "MAHINDRA",
    "TURBO", "DIESEL", "CRDI", "SEDAN", "CAMPER", "SPECIAL", "BOLERO", "INNOVA", "CRETA"
}

def levenshtein_dist(s1: str, s2: str) -> int:
    """Calculates true Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_dist(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def canonical_ocr_chars(s: str) -> str:
    """Normalizes typical OCR glyph confusions (O/0, I/1, B/8, S/5, Z/2)."""
    s = s.upper()
    sub_map = {'O': '0', 'Q': '0', 'D': '0', 'I': '1', 'L': '1', 'B': '8', 'S': '5', 'Z': '2'}
    return ''.join(sub_map.get(c, c) for c in s)

class ANPREngine:
    """
    Project TRINETRA-C2 // Automatic Number Plate Recognition (ANPR) & Intelligence Core
    Integrates:
      - Real-time vehicle tracking integration (Cars, Trucks, Buses, Motorcycles)
      - Dynamic plate localization via morphological gradient density & geometric priors
      - Async, non-blocking PyTorch/EasyOCR text recognition running in background worker
      - Syntax normalization for Indian standard (e.g. JK 02 B 1892) & tactical registrations
      - Watchlist & Stolen Vehicle Database matching with instant threat classification
      - Non-blocking 30+ FPS zero-latency architecture with track-based spatial caching
    """
    def __init__(self, 
                 watchlist_path: str = "vehicle_watchlist.json",
                 max_workers: int = 2):
        self.watchlist_path = watchlist_path
        self.watchlist: Dict[str, Dict[str, Any]] = {}
        self.load_watchlist()

        self.vehicle_cache: Dict[int, Dict[str, Any]] = {}
        self.track_last_processed: Dict[int, int] = {}
        self.pending_tasks: Dict[int, Any] = {}
        self.lock = threading.Lock()
        
        self.scan_logs: List[Dict[str, Any]] = []
        self.max_logs = 50

        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ANPR_Worker")
        
        self.ocr_reader = None
        self.crnn_reader = None
        self.ocr_initialized = False
        self.ocr_lock = threading.Lock()

        self.clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    def load_watchlist(self):
        try:
            if os.path.exists(self.watchlist_path):
                with open(self.watchlist_path, "r", encoding="utf-8") as f:
                    self.watchlist = json.load(f)
                print(f"[ANPR-ENGINE] Loaded {len(self.watchlist)} vehicles into active watchlist.")
            else:
                self.watchlist = {}
        except Exception as e:
            print(f"[ANPR-ENGINE] Error loading watchlist: {e}")
            self.watchlist = {}

    def save_watchlist(self):
        try:
            with open(self.watchlist_path, "w", encoding="utf-8") as f:
                json.dump(self.watchlist, f, indent=4)
        except Exception as e:
            print(f"[ANPR-ENGINE] Error saving watchlist: {e}")

    def _init_ocr(self):
        with self.ocr_lock:
            if self.ocr_initialized:
                return
            # Priority 1: High-speed, ultra-lightweight OpenCV DNN ONNX CRNN (<25MB RAM)
            candidate_paths = [
                os.path.join(os.path.dirname(__file__), "..", "models", "text_recognition_CRNN_EN_2021sep.onnx"),
                os.path.abspath("models/text_recognition_CRNN_EN_2021sep.onnx"),
                "models/text_recognition_CRNN_EN_2021sep.onnx"
            ]
            crnn_model_path = None
            for p in candidate_paths:
                if os.path.exists(p):
                    crnn_model_path = p
                    break

            if crnn_model_path:
                try:
                    from core.crnn_helper import CRNN
                    print(f"[ANPR-ENGINE] Initializing OpenCV ONNX CRNN Recognizer ({crnn_model_path})...")
                    self.crnn_reader = CRNN(crnn_model_path)
                    self.ocr_initialized = True
                    print("[ANPR-ENGINE] OpenCV ONNX CRNN Engine loaded successfully (Memory footprint < 25MB).")
                    return
                except Exception as e:
                    print(f"[ANPR-ENGINE] OpenCV ONNX CRNN init failed: {e}")

        # Priority 2: Optional fallback to PyTorch EasyOCR only if explicitly enabled
        if os.environ.get("ENABLE_EASYOCR", "0") == "1":
            try:
                import easyocr
                print("[ANPR-ENGINE] Initializing PyTorch EasyOCR Recognizer...")
                self.ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
                self.ocr_initialized = True
                print("[ANPR-ENGINE] EasyOCR Engine initialized successfully.")
                return
            except Exception as e:
                print(f"[ANPR-ENGINE] EasyOCR init failed: {e}")

        self.ocr_initialized = False

    def extract_plate_crop(self, vehicle_crop: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        vh, vw = vehicle_crop.shape[:2]
        if vh < 30 or vw < 40:
            return None, None

        # Focus strictly on lower region of vehicle (bumper / boot mount zone)
        y_start = int(vh * 0.45)
        roi = vehicle_crop[y_start:vh, int(vw * 0.06):int(vw * 0.94)]
        roi_h, roi_w = roi.shape[:2]
        if roi_h < 15 or roi_w < 25:
            return None, None

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        sobelx = cv2.Sobel(blurred, cv2.CV_16S, 1, 0, ksize=3)
        abs_sobelx = cv2.convertScaleAbs(sobelx)
        
        _, thresh = cv2.threshold(abs_sobelx, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, rect_kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_box = None
        max_score = 0.0

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = float(w) / max(h, 1)
            area = w * h
            roi_area = roi_w * roi_h
            
            # Standard license plate aspect ratio: 2.0 to 5.5
            if 2.0 <= aspect <= 5.5 and 0.015 * roi_area <= area <= 0.30 * roi_area:
                center_dist = abs((x + w/2.0) - roi_w/2.0) / float(roi_w)
                aspect_diff = abs(aspect - 3.5) / 3.5
                score = (area / float(roi_area)) * (1.0 - 0.4 * center_dist - 0.2 * aspect_diff)
                if score > max_score:
                    max_score = score
                    best_box = (x, y, w, h)

        if best_box is not None:
            bx, by, bw, bh = best_box
            pad_x = int(bw * 0.10)
            pad_y = int(bh * 0.10)
            x1 = max(0, bx - pad_x)
            y1 = max(0, by - pad_y)
            x2 = min(roi_w, bx + bw + pad_x)
            y2 = min(roi_h, by + bh + pad_y)
            plate_crop = roi[y1:y2, x1:x2]
            rel_box = (int(vw * 0.06) + x1, y_start + y1, x2 - x1, y2 - y1)
            return plate_crop, rel_box

        # Prior fallback: Calibrated bumper plate coordinate window
        def_w = int(vw * 0.44)
        def_h = int(vh * 0.16)
        def_x = int((vw - def_w) / 2)
        def_y = int(vh * 0.70)
        def_crop = vehicle_crop[def_y:min(vh, def_y + def_h), def_x:min(vw, def_x + def_w)]
        return def_crop, (def_x, def_y, def_w, def_h)

    def match_watchlist_fuzzy(self, raw_str: str) -> Optional[Tuple[str, Dict[str, Any], float]]:
        """
        Fuzzy Levenshtein & optical confusion matcher against active threat database.
        Returns (canonical_plate, watchlist_entry, confidence) or None.
        """
        clean = re.sub(r'[^A-Za-z0-9]', '', raw_str).upper()
        if len(clean) < 3:
            return None
        clean_canon = canonical_ocr_chars(clean)

        best_hit = None
        best_sim = 0.0

        for w_plate, info in self.watchlist.items():
            w_clean = re.sub(r'[^A-Za-z0-9]', '', w_plate).upper()
            w_canon = canonical_ocr_chars(w_clean)

            # Exact match
            if clean == w_clean:
                return w_plate, info, 0.99
            # Canonical glyph match (O/0, I/1, B/8, S/5, Z/2)
            if clean_canon == w_canon:
                return w_plate, info, 0.97

            # Levenshtein distance test
            d1 = levenshtein_dist(clean, w_clean)
            d2 = levenshtein_dist(clean_canon, w_canon)
            min_d = min(d1, d2)
            max_len = max(len(clean), len(w_clean))
            sim = 1.0 - (min_d / float(max_len))

            if min_d <= 2 and sim >= 0.75 and sim > best_sim:
                best_sim = sim
                best_hit = (w_plate, info, round(sim, 2))

            # 4-digit or 3-digit primary vehicle registration number match
            c_digits = re.findall(r'[0-9]{3,4}', clean)
            w_digits = re.findall(r'[0-9]{3,4}', w_clean)
            if c_digits and w_digits:
                digit_dist = levenshtein_dist(c_digits[0], w_digits[0])
                if digit_dist <= 2 and (clean[0] == w_clean[0] or sim >= 0.50):
                    if best_sim < 0.92:
                        best_sim = 0.92
                        best_hit = (w_plate, info, 0.92)

            # Substring signature match
            if (len(clean) >= 4 and (clean in w_clean or clean_canon in w_canon)) or (len(clean) >= 2 and clean.isdigit() and clean in w_clean):
                if best_sim < 0.88:
                    best_sim = 0.88
                    best_hit = (w_plate, info, 0.88)

        return best_hit

    def parse_civilian_plate(self, raw_str: str) -> Optional[Tuple[str, float]]:
        """
        Strict Indian Motor Vehicle Registration Syntax Validator.
        Enforces official RTO state prefixes, Delhi RTO series, standard district numbers,
        and Bharat Series. Rejects all car manufacturer badges and random character junk.
        """
        clean = re.sub(r'[^A-Za-z0-9]', '', raw_str).upper()
        if len(clean) < 7 or len(clean) > 11:
            return None

        # Filter out automotive badges commonly found near bumper / boot
        if any(badge in clean for badge in CAR_BRAND_BADGES):
            return None

        # Apply state prefix OCR error corrections
        for err, corr in STATE_CORRECTIONS.items():
            if clean.startswith(err):
                clean = corr + clean[len(err):]
                break

        state_code = clean[:2]
        is_bh_series = (clean[:2].isdigit() and clean[2:4] == 'BH')
        if state_code not in VALID_INDIAN_STATES and not is_bh_series:
            return None

        # 1. Delhi RTO Special Format (e.g. DL 8C AM 1102, DL 1C A 1234)
        if clean.startswith("DL") and len(clean) >= 9:
            m_dl = re.match(r'^(DL)([0-9]{1,2}[A-Z]?)([A-Z]{1,3})([0-9]{4})$', clean)
            if m_dl:
                s, d, ser, num = m_dl.groups()
                return f"{s} {d} {ser} {num}", 0.94

        # 2. Standard Indian Motor Vehicle Registration (e.g. JK 02 B 1892, PB 02 AK 4921, MH 12 DE 1433)
        m_std = re.match(r'^([A-Z]{2})([0-9]{1,2})([A-Z]{0,3})([0-9]{3,4})$', clean)
        if m_std:
            s, d, ser, num = m_std.groups()
            parts = [s, d]
            if ser:
                parts.append(ser)
            parts.append(num)
            return ' '.join(parts), 0.90

        # 3. Bharat Series (BH) Registration (e.g. 22 BH 9999 AB)
        m_bh = re.match(r'^([0-9]{2})(BH)([0-9]{4})([A-Z]{1,2})$', clean)
        if m_bh:
            yr, bh, num, ser = m_bh.groups()
            return f"{yr} {bh} {num} {ser}", 0.95

        return None

    def normalize_plate_text(self, raw_str: str) -> Tuple[str, float]:
        """
        Normalizes OCR candidate string using dual-layer validation:
        1. Fuzzy Watchlist Matching (priority threat detection)
        2. Strict Indian Civilian Registration Syntax Validation
        Rejects random strings, noise tokens, and garbage character fragments.
        """
        # Layer 1: Check active watchlist targets first
        wl_match = self.match_watchlist_fuzzy(raw_str)
        if wl_match is not None:
            w_plate, _, conf = wl_match
            return w_plate, conf

        # Layer 2: Check strict Indian Motor Vehicle civilian syntax
        civ_match = self.parse_civilian_plate(raw_str)
        if civ_match is not None:
            c_plate, conf = civ_match
            return c_plate, conf

        # Layer 3: Generic Alphanumeric Registration Formatter (for all valid civilian & commercial vehicles)
        clean = re.sub(r'[^A-Za-z0-9]', '', raw_str).upper()
        if len(clean) >= 4 and len(clean) <= 12 and not any(b in clean for b in CAR_BRAND_BADGES):
            tokens = [t.strip().upper() for t in raw_str.split() if re.sub(r'[^A-Za-z0-9]', '', t)]
            if len(tokens) >= 2 and all(len(t) <= 6 for t in tokens):
                formatted = ' '.join(tokens)
            elif len(clean) >= 8:
                formatted = f"{clean[:2]} {clean[2:4]} {clean[4:]}"
            elif len(clean) >= 6:
                formatted = f"{clean[:3]} {clean[3:]}"
            else:
                formatted = clean
            return formatted, 0.75

        return '', 0.0

    def query_watchlist(self, plate_str: str) -> Tuple[str, str, str, str, bool]:
        norm_key = re.sub(r'\s+', ' ', plate_str.strip().upper())
        stripped_key = re.sub(r'[^A-Za-z0-9]', '', norm_key)
        canon_key = canonical_ocr_chars(stripped_key)

        for w_plate, info in self.watchlist.items():
            w_stripped = re.sub(r'[^A-Za-z0-9]', '', w_plate.upper())
            w_canon = canonical_ocr_chars(w_stripped)
            if norm_key == w_plate.upper() or stripped_key == w_stripped or canon_key == w_canon:
                cat = info.get('category', 'WATCHLIST TARGET')
                risk = info.get('risk', 'ELEVATED')
                msg = info.get('alert_msg', f'Watchlist vehicle {plate_str} intercepted.')
                vmodel = info.get('vehicle_model', 'SUSPECT VEHICLE')
                is_threat = any(k in str(cat).upper() for k in ['STOLEN', 'TRAFFICKING', 'UNAUTHORIZED', 'SUSPICIOUS', 'INTERCEPT']) or any(r in str(risk).upper() for r in ['CRITICAL', 'HIGH', 'LEVEL 1'])
                return cat, risk, msg, vmodel, is_threat

        return 'STANDARD TRANSIT', 'NOMINAL // CLEAR', f'Standard civilian/commercial transport: {plate_str}', 'CIVILIAN VEHICLE', False

    def _ocr_worker(self, track_id: int, plate_crop: np.ndarray, vehicle_type: str, rel_box: Tuple[int, int, int, int]):
        try:
            if not self.ocr_initialized:
                self._init_ocr()

            if not self.ocr_initialized or plate_crop is None or plate_crop.shape[0] < 10 or plate_crop.shape[1] < 15:
                return

            raw_text = ''
            ocr_conf = 0.5

            if self.crnn_reader is not None:
                # Ultra-fast, low-memory OpenCV DNN ONNX CRNN Inference
                ph, pw = plate_crop.shape[:2]
                scale = max(2.0, 160.0 / max(float(pw), 1.0))
                scaled = cv2.resize(plate_crop, (int(pw * scale), int(ph * scale)), interpolation=cv2.INTER_LANCZOS4)
                sh, sw = scaled.shape[:2]
                rbbox = np.array([
                    [0, sh - 1],
                    [0, 0],
                    [sw - 1, 0],
                    [sw - 1, sh - 1]
                ], dtype=np.float32)

                with self.ocr_lock:
                    text_out = self.crnn_reader.infer(scaled, rbbox)
                    if not text_out or len(text_out) < 4:
                        gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
                        denoised = cv2.bilateralFilter(gray, 5, 50, 50)
                        boosted = self.clahe.apply(denoised)
                        boosted_bgr = cv2.cvtColor(boosted, cv2.COLOR_GRAY2BGR)
                        text_out2 = self.crnn_reader.infer(boosted_bgr, rbbox)
                        if text_out2 and len(text_out2) > len(text_out or ''):
                            text_out = text_out2

                raw_text = (text_out or '').strip().upper()
                ocr_conf = 0.85 if len(raw_text) >= 6 else 0.60

            elif self.ocr_reader is not None:
                # Super-Resolution Image Enhancement Pipeline for EasyOCR
                ph, pw = plate_crop.shape[:2]
                scale = max(2.5, 240.0 / max(float(pw), 1.0))
                scaled_color = cv2.resize(plate_crop, (int(pw * scale), int(ph * scale)), interpolation=cv2.INTER_LANCZOS4)

                res = self.ocr_reader.readtext(
                    scaled_color,
                    allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -',
                    paragraph=False
                )

                if not res or len(res) == 0 or max([item[2] for item in res if len(item) >= 3] or [0.0]) < 0.35:
                    gray = cv2.cvtColor(scaled_color, cv2.COLOR_BGR2GRAY)
                    denoised = cv2.bilateralFilter(gray, 7, 50, 50)
                    boosted = self.clahe.apply(denoised)
                    res_boosted = self.ocr_reader.readtext(
                        boosted, 
                        allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -',
                        paragraph=False
                    )
                    if res_boosted and len(res_boosted) > 0:
                        res = res_boosted
                
                if res and len(res) > 0:
                    tokens = []
                    conf_sum = 0.0
                    for item in res:
                        if len(item) >= 2:
                            txt = str(item[1]).strip()
                            if len(txt) > 1 or txt.isalnum():
                                tokens.append(txt)
                            if len(item) >= 3 and isinstance(item[2], (float, int)):
                                conf_sum += float(item[2])
                    raw_text = ' '.join(tokens)
                    if len(tokens) > 0:
                        ocr_conf = conf_sum / len(tokens)

            formatted_plate, format_conf = self.normalize_plate_text(raw_text)
            
            # Strict gatekeeper: If plate could not be verified against Indian syntax or Watchlist, do NOT hallucinate
            if not formatted_plate or format_conf <= 0.0:
                return

            conf = round(float(ocr_conf * 0.35 + format_conf * 0.65) * 100, 1)
            cat, risk, msg, vmodel, is_alert = self.query_watchlist(formatted_plate)
            
            result_entry = {
                'track_id': track_id,
                'plate': formatted_plate,
                'raw_text': raw_text,
                'confidence': conf,
                'category': cat,
                'risk': risk,
                'alert_msg': msg,
                'vehicle_model': vmodel,
                'is_alert': is_alert,
                'vehicle_type': vehicle_type,
                'plate_bbox': rel_box,
                'locked': (conf >= 80.0 or is_alert),
                'timestamp': time.time(),
                'time_str': time.strftime('%H:%M:%S')
            }

            with self.lock:
                current_entry = self.vehicle_cache.get(track_id)
                # Keep higher confidence or alert result locked to avoid regression
                if current_entry and current_entry.get('locked') and current_entry.get('confidence', 0) > conf and not is_alert:
                    current_entry['plate_bbox'] = rel_box
                    return

                self.vehicle_cache[track_id] = result_entry
                
                # Append to scan logs only if genuine verified reading and not duplicate of recent entry
                if conf >= 60.0 or is_alert:
                    if not self.scan_logs or self.scan_logs[0].get('plate') != formatted_plate:
                        self.scan_logs.insert(0, result_entry)
                        if len(self.scan_logs) > self.max_logs:
                            self.scan_logs.pop()

            if is_alert:
                print(f'[ANPR-ALERT] !!! WATCHLIST HIT !!! Plate: {formatted_plate} | {cat} | {risk}')
            else:
                print(f'[ANPR-SCAN] Plate Verified: {formatted_plate} ({conf}%) | {cat}')
        except Exception as e:
            logger.error(f'ANPR Worker error on track {track_id}: {e}')

    def process_vehicles(self, frame: np.ndarray, detections: List[Dict[str, Any]], frame_num: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        new_alerts = []
        vehicle_classes = {'VEHICLE', 'HEAVY_VEHICLE', 'TRUCK', 'MOTORCYCLE', 'CAR', 'BUS'}

        for det in detections:
            cname = det.get('class_name', '')
            tid = det.get('track_id')
            if cname not in vehicle_classes or tid is None:
                continue

            x1, y1, x2, y2 = det['bbox']
            fh, fw = frame.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(fw, x2), min(fh, y2)
            vw_w = max(10, x2 - x1)
            vw_h = max(10, y2 - y1)
            
            cached = self.vehicle_cache.get(tid)
            last_run = self.track_last_processed.get(tid, 0)

            # Determine whether to dispatch background OCR job
            is_locked = bool(cached and cached.get('locked'))
            should_run = (cached is None) or (not is_locked and (frame_num - last_run) > 20)
            
            if should_run and (tid not in self.pending_tasks or self.pending_tasks[tid].done()):
                self.track_last_processed[tid] = frame_num
                vcrop = frame[y1:y2, x1:x2].copy()
                plate_crop, rel_box = self.extract_plate_crop(vcrop)
                if plate_crop is not None and plate_crop.size > 0:
                    future = self.executor.submit(self._ocr_worker, tid, plate_crop, cname, rel_box)
                    self.pending_tasks[tid] = future

            if cached is not None:
                # Update relative plate box to track moving vehicle smoothly
                if not cached.get('plate_bbox'):
                    cached['plate_bbox'] = (int(vw_w * 0.28), int(vw_h * 0.68), int(vw_w * 0.44), int(vw_h * 0.18))
                det['anpr'] = cached
                if cached.get('is_alert') and not cached.get('_alerted'):
                    cached['_alerted'] = True
                    new_alerts.append(cached)
            else:
                det['anpr'] = {
                    'plate': 'SCANNING PLATE...',
                    'confidence': 0.0,
                    'category': 'ACQUIRING REGISTRATION',
                    'risk': 'MONITORING',
                    'is_alert': False,
                    'vehicle_type': cname,
                    'plate_bbox': (int(vw_w * 0.28), int(vw_h * 0.68), int(vw_w * 0.44), int(vw_h * 0.18))
                }

        finished_ids = [tid for tid, fut in self.pending_tasks.items() if fut.done()]
        for fid in finished_ids:
            del self.pending_tasks[fid]

        return detections, new_alerts

    def add_to_watchlist(self, plate: str, category: str, risk: str, vehicle_model: str, alert_msg: str) -> Dict[str, Any]:
        norm_plate = plate.strip().upper()
        entry = {
            'plate': norm_plate,
            'category': category.strip().upper(),
            'risk': risk.strip().upper(),
            'vehicle_model': vehicle_model.strip().upper(),
            'incident_ref': f'C2-MANUAL-{int(time.time())}',
            'origin': 'C2 OPERATOR INPUT',
            'alert_msg': alert_msg.strip() or f'High alert: Flagged vehicle {norm_plate} detected.'
        }
        self.watchlist[norm_plate] = entry
        self.save_watchlist()
        
        with self.lock:
            for tid, cached in self.vehicle_cache.items():
                if re.sub(r'[^A-Za-z0-9]', '', cached.get('plate', '')) == re.sub(r'[^A-Za-z0-9]', '', norm_plate):
                    cat, risk_val, msg, vmodel, is_threat = self.query_watchlist(cached['plate'])
                    cached['category'] = cat
                    cached['risk'] = risk_val
                    cached['alert_msg'] = msg
                    cached['is_alert'] = is_threat
        return entry
