import cv2
import numpy as np
import time

class MultiSpectralSensor:
    """
    Multi-Spectral Computer Vision Sensor Core.
    Transforms video streams into authentic military surveillance spectra:
      1. NORMAL: Daylight Optical RGB
      2. NVG_P43: PVS-14 Gen-3 Green Phosphor (530nm) IIT Simulation
      3. FLIR_IRONBOW: Forward-Looking Infrared Thermal Heatmap
      4. FLIR_WHOT: White-Hot High-Contrast Military Infrared
      5. FLIR_BHOT: Black-Hot Inverted Infrared Sniper/Perimeter Surveillance
    """
    def __init__(self):
        self.active_mode = "NORMAL"
        self.scope_mask_enabled = False

        # Pre-generate P43 Phosphor Look-Up Table (Peak wavelength 530nm: #2aff38)
        self.lut_nvg = np.zeros((256, 1, 3), dtype=np.uint8)
        for i in range(256):
            norm = i / 255.0
            amp = np.power(norm, 0.72)
            b = int(np.clip(amp * 40, 0, 255))
            g = int(np.clip(amp * 248 + (1.0 - norm) * 8, 0, 255))
            r = int(np.clip(amp * 42, 0, 255))
            self.lut_nvg[i, 0] = [b, g, r]

        # Pre-generate FLIR Ironbow Look-Up Table (FLIR Military Palette)
        # Black -> Dark Navy -> Violet -> Red -> Orange -> Yellow -> White Hot
        self.lut_ironbow = np.zeros((256, 1, 3), dtype=np.uint8)
        for i in range(256):
            t = i / 255.0
            if t < 0.16:
                f = t / 0.16
                b, g, r = int(f * 130), 0, int(f * 25)
            elif t < 0.35:
                f = (t - 0.16) / 0.19
                b, g, r = int(130 + f * 35), 0, int(25 + f * 170)
            elif t < 0.55:
                f = (t - 0.35) / 0.20
                b, g, r = int(165 * (1.0 - f)), int(20 * f), int(195 + f * 60)
            elif t < 0.75:
                f = (t - 0.55) / 0.20
                b, g, r = 0, int(20 + f * 145), 255
            elif t < 0.92:
                f = (t - 0.75) / 0.17
                b, g, r = int(f * 75), int(165 + f * 90), 255
            else:
                f = (t - 0.92) / 0.08
                b, g, r = int(75 + f * 180), 255, 255
            self.lut_ironbow[i, 0] = [b, g, r]

        self.clahe = cv2.createCLAHE(clipLimit=3.2, tileGridSize=(8, 8))

    def set_mode(self, mode: str):
        valid = ["NORMAL", "NVG_P43", "FLIR_IRONBOW", "FLIR_WHOT", "FLIR_BHOT"]
        clean = mode.strip().upper()
        if clean in valid:
            self.active_mode = clean
            return True
        return False

    def toggle_scope_mask(self):
        self.scope_mask_enabled = not self.scope_mask_enabled
        return self.scope_mask_enabled

    def process(self, frame: np.ndarray) -> np.ndarray:
        if frame is None:
            return frame

        mode = self.active_mode
        if mode == "NORMAL":
            out = frame.copy()
        elif mode == "NVG_P43":
            out = self._render_nvg(frame)
        elif mode == "FLIR_IRONBOW":
            out = self._render_ironbow(frame)
        elif mode == "FLIR_WHOT":
            out = self._render_whot(frame)
        elif mode == "FLIR_BHOT":
            out = self._render_bhot(frame)
        else:
            out = frame.copy()

        if self.scope_mask_enabled:
            out = self._apply_scope_mask(out)

        return out

    def _render_nvg(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        boosted = self.clahe.apply(gray)
        boosted_3ch = cv2.cvtColor(boosted, cv2.COLOR_GRAY2BGR)
        nvg = cv2.LUT(boosted_3ch, self.lut_nvg)

        # Light bloom around high-luminance sources
        _, thresh = cv2.threshold(boosted, 215, 255, cv2.THRESH_BINARY)
        if cv2.countNonZero(thresh) > 0:
            bloom = cv2.GaussianBlur(thresh, (25, 25), 0)
            bloom_color = cv2.applyColorMap(bloom, cv2.COLORMAP_SUMMER)
            nvg = cv2.addWeighted(nvg, 1.0, bloom_color, 0.40, 0)

        # High-gain scintillation tube noise
        noise = np.random.normal(0, 8, (h, w)).astype(np.int16)
        nvg_int16 = nvg.astype(np.int16)
        nvg_int16[:, :, 1] = np.clip(nvg_int16[:, :, 1] + noise, 0, 255)
        return nvg_int16.astype(np.uint8)

    def _render_ironbow(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thermal_norm = self.clahe.apply(gray)
        thermal_soft = cv2.GaussianBlur(thermal_norm, (3, 3), 0)
        thermal_soft_3ch = cv2.cvtColor(thermal_soft, cv2.COLOR_GRAY2BGR)
        return cv2.LUT(thermal_soft_3ch, self.lut_ironbow)

    def _render_whot(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        boosted = self.clahe.apply(gray)
        return cv2.cvtColor(boosted, cv2.COLOR_GRAY2BGR)

    def _render_bhot(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        boosted = self.clahe.apply(gray)
        bhot_gray = cv2.bitwise_not(boosted)
        return cv2.cvtColor(bhot_gray, cv2.COLOR_GRAY2BGR)

    def _apply_scope_mask(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        center = (w // 2, h // 2)
        radius = int(min(w, h) * 0.44)

        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, center, radius, 255, -1)
        mask_blur = cv2.GaussianBlur(mask, (31, 31), 0)
        mask_3d = cv2.cvtColor(mask_blur, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0

        bg = np.full_like(frame, (9, 10, 7), dtype=np.uint8)
        composite = (frame.astype(np.float32) * mask_3d + bg.astype(np.float32) * (1.0 - mask_3d)).astype(np.uint8)

        c_reticle = (0, 240, 255) if self.active_mode == "NORMAL" else (40, 255, 60)
        cx, cy = center

        cv2.line(composite, (cx - radius + 25, cy), (cx - 15, cy), c_reticle, 1, cv2.LINE_AA)
        cv2.line(composite, (cx + 15, cy), (cx + radius - 25, cy), c_reticle, 1, cv2.LINE_AA)
        cv2.line(composite, (cx, cy - radius + 25), (cx, cy - 15), c_reticle, 1, cv2.LINE_AA)
        cv2.line(composite, (cx, cy + 15), (cx, cy + radius - 25), c_reticle, 1, cv2.LINE_AA)
        cv2.circle(composite, center, 8, c_reticle, 1, cv2.LINE_AA)

        for d in range(40, radius - 30, 40):
            cv2.circle(composite, (cx + d, cy), 2, c_reticle, -1, cv2.LINE_AA)
            cv2.circle(composite, (cx - d, cy), 2, c_reticle, -1, cv2.LINE_AA)
            cv2.circle(composite, (cx, cy + d), 2, c_reticle, -1, cv2.LINE_AA)
            cv2.circle(composite, (cx, cy - d), 2, c_reticle, -1, cv2.LINE_AA)

        return composite
