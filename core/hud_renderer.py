import cv2
import time
import math
import numpy as np

class TacticalHUDRenderer:
    """
    Renders defense-grade tactical C2 HUD overlays on video frames.
    Includes:
      - Military classification banner & MGRS grid telemetry
      - Target bracket reticles with velocity trajectory arrows
      - Incursion ETA countdown callouts
      - Sector threat status and breach flashers
      - Sterile Exclusion Zone geometry and polygon tripwire evaluation
    """
    def __init__(self):
        # Tactical HUD Color Palette (BGR)
        self.C_HUD_GREEN = (50, 220, 50)      # High-tech neon green
        self.C_ALERT_RED = (40, 40, 235)      # Intense tactical red
        self.C_WARNING_AMBER = (0, 165, 255)  # Amber
        self.C_CYAN_ACCENT = (230, 200, 0)    # Cyan
        self.C_DARK_BG = (15, 20, 25)         # Semi-transparent HUD dark slate
        self.C_WHITE = (255, 255, 255)

        self.flash_state = False
        self.last_flash_time = time.time()
        self.anim_tick = 0

    def update_flash(self, interval=0.3):
        """Toggles flash state for alarming visuals."""
        if time.time() - self.last_flash_time > interval:
            self.flash_state = not self.flash_state
            self.last_flash_time = time.time()
        self.anim_tick = (self.anim_tick + 1) % 10000
        return self.flash_state

    def draw_corner_brackets(self, frame, bbox, color, length=18, thickness=2):
        """Draws military-style corner brackets instead of cheap box outlines."""
        x1, y1, x2, y2 = bbox
        l = min(length, int((x2 - x1) * 0.35), int((y2 - y1) * 0.35))
        
        # Top-Left
        cv2.line(frame, (x1, y1), (x1 + l, y1), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x1, y1), (x1, y1 + l), color, thickness, cv2.LINE_AA)
        # Top-Right
        cv2.line(frame, (x2, y1), (x2 - l, y1), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x2, y1), (x2, y1 + l), color, thickness, cv2.LINE_AA)
        # Bottom-Left
        cv2.line(frame, (x1, y2), (x1 + l, y2), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x1, y2), (x1, y2 - l), color, thickness, cv2.LINE_AA)
        # Bottom-Right
        cv2.line(frame, (x2, y2), (x2 - l, y2), color, thickness, cv2.LINE_AA)
        cv2.line(frame, (x2, y2), (x2, y2 - l), color, thickness, cv2.LINE_AA)

        # Subtle thin connecting box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1, cv2.LINE_AA)

    def draw_hud(self, frame, detections, active_breaches, fps, latency_ms, clahe_on, sensor_mode="NORMAL",
                 mgrs="43R FN 2891 7412", gsd_text="GSD: 7.8cm | NIIRS-7", muted=False,
                 sector_label="SECTOR-01 // BORDER FENCE", is_godeye_mode=False,
                 satellite_info=None, sec65b_hash=None, **kwargs):
        """Assembles and composites the full tactical defense HUD."""
        h, w = frame.shape[:2]
        self.update_flash()
        has_breach = len(active_breaches) > 0
        breach_ids = {b["track_id"] for b in active_breaches}

        # 1. Optical Coordinate Crosshair Grid (Furious 7 God's Eye aesthetic)
        if is_godeye_mode:
            self._draw_godeye_grid(frame, w, h)

        # 2. Top Intelligence Telemetry Ribbon
        ribbon_h = 50
        bot_h = 32
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, ribbon_h), self.C_DARK_BG, -1)
        cv2.addWeighted(overlay, 0.80, frame, 0.20, 0, frame)
        cv2.line(frame, (0, ribbon_h), (w, ribbon_h), self.C_CYAN_ACCENT, 1, cv2.LINE_AA)

        class_text = "OMNISCIENT BIOMETRIC SURVEILLANCE // FURIOUS 7 GOD'S EYE" if is_godeye_mode else "RESTRICTED // LAW ENFORCEMENT SENSITIVE // MHA BORDER SENTRY"
        cv2.putText(frame, class_text, (14, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (140, 160, 150), 1, cv2.LINE_AA)

        title_text = f"TRINETRA-C2 // {sector_label}"
        cv2.putText(frame, title_text, (14, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.46, self.C_CYAN_ACCENT, 1, cv2.LINE_AA)

        mgrs_text = f"MGRS: {mgrs} | {gsd_text}"
        (mw, _), _ = cv2.getTextSize(mgrs_text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        cv2.putText(frame, mgrs_text, (max(w - mw - 14, 320), 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 240, 255), 1, cv2.LINE_AA)

        sensor_badge = f"[{sensor_mode}]"
        perf_text = f"FPS: {fps:4.1f} | LAT: {latency_ms:4.1f}ms | TRK: {len(detections):02d} | {sensor_badge}"
        (pw, _), _ = cv2.getTextSize(perf_text, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        cv2.putText(frame, perf_text, (max(w - pw - 14, 320), 38), cv2.FONT_HERSHEY_SIMPLEX, 0.38, self.C_WHITE, 1, cv2.LINE_AA)

        # 3. Draw Target Detections with Kinematics & Velocity Vectors
        for det in detections:
            bbox = det["bbox"]
            cls_name = det["class_name"]
            conf = det["confidence"]
            tid = det["track_id"]
            footfall = det["footfall"]
            kin = det.get("kinematics", {})

            is_intruder = tid in breach_ids
            breach_eta = kin.get("breach_eta_s")
            is_imminent = kin.get("is_imminent", False)

            if is_godeye_mode:
                target_col = (0, 140, 255) if is_intruder else (0, 240, 255)
                tag_label = f"TARGET LOCKED: {cls_name} #{tid or 1} [99.4%]"
            elif is_intruder:
                target_col = self.C_ALERT_RED if self.flash_state else (255, 255, 255)
                tag_label = f"!! BREACH: ID#{tid} {cls_name} ({int(conf*100)}%)"
            elif is_imminent and breach_eta is not None:
                target_col = self.C_WARNING_AMBER
                tag_label = f"! IMMINENT ETA {breach_eta}s: ID#{tid} {cls_name}"
            else:
                target_col = self.C_HUD_GREEN
                tag_label = f"TRK-{tid or 'X'}: {cls_name} {int(conf*100)}%"

            # Draw brackets
            self.draw_corner_brackets(frame, bbox, target_col, length=20, thickness=2)

            # Draw footfall ground target dot
            cv2.circle(frame, footfall, 4, target_col, -1, cv2.LINE_AA)
            cv2.circle(frame, footfall, 8, target_col, 1, cv2.LINE_AA)

            # Draw velocity trajectory vector arrow on ground
            vx, vy = kin.get("velocity", (0.0, 0.0))
            if abs(vx) > 3.0 or abs(vy) > 3.0:
                fx, fy = footfall
                target_pt = (int(fx + vx * 1.5), int(fy + vy * 1.5))
                cv2.arrowedLine(frame, footfall, target_pt, target_col, 2, cv2.LINE_AA, tipLength=0.35)
                spd = kin.get("speed", 0.0)
                cv2.putText(frame, f"{spd:.0f}px/s", (target_pt[0] + 4, target_pt[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.32, target_col, 1, cv2.LINE_AA)

            # Draw tactical callout label box
            x1, y1, x2, y2 = bbox
            (tw, th), _ = cv2.getTextSize(tag_label, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)
            tag_y1 = max(y1 - th - 8, ribbon_h + 5)
            cv2.rectangle(frame, (x1, tag_y1), (x1 + tw + 8, tag_y1 + th + 6), self.C_DARK_BG, -1)
            cv2.rectangle(frame, (x1, tag_y1), (x1 + tw + 8, tag_y1 + th + 6), target_col, 1)
            cv2.putText(frame, tag_label, (x1 + 4, tag_y1 + th + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.42, target_col, 1, cv2.LINE_AA)

            # ANPR (Automatic Number Plate Recognition) Vehicle HUD Badge
            anpr = det.get("anpr")
            if anpr:
                is_al = anpr.get("is_alert", False)
                p_plate = anpr.get("plate", "SCANNING PLATE...")
                cat = anpr.get("category", "")
                
                if is_al:
                    plate_txt = f"[PLATE: {p_plate}] // ! {cat} !"
                    p_col = self.C_ALERT_RED if self.flash_state else (255, 255, 255)
                elif "AUTHORIZED" in cat:
                    plate_txt = f"[PLATE: {p_plate}] // AUTHORIZED CLEAR"
                    p_col = (50, 220, 50)
                elif anpr.get("confidence", 0) > 0:
                    plate_txt = f"[PLATE: {p_plate}] // VERIFIED [{int(anpr.get('confidence'))}%]"
                    p_col = (0, 240, 255)
                else:
                    plate_txt = f"[PLATE: {p_plate}] // ACQUIRING..."
                    p_col = (180, 200, 210)

                (ptw, pth), _ = cv2.getTextSize(plate_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
                p_y1 = min(y2 + 4, h - bot_h - pth - 8)
                cv2.rectangle(frame, (x1, p_y1), (x1 + ptw + 8, p_y1 + pth + 6), self.C_DARK_BG, -1)
                cv2.rectangle(frame, (x1, p_y1), (x1 + ptw + 8, p_y1 + pth + 6), p_col, 1)
                cv2.putText(frame, plate_txt, (x1 + 4, p_y1 + pth + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.36, p_col, 1, cv2.LINE_AA)

                # License plate bumper reticle
                if anpr.get("plate_bbox"):
                    rel_px, rel_py, rel_pw, rel_ph = anpr["plate_bbox"]
                    abs_px = max(0, min(w - 1, x1 + rel_px))
                    abs_py = max(0, min(h - 1, y1 + rel_py))
                    abs_pw = min(rel_pw, w - abs_px)
                    abs_ph = min(rel_ph, h - abs_py)
                    if abs_pw > 10 and abs_ph > 6:
                        cv2.rectangle(frame, (abs_px, abs_py), (abs_px + abs_pw, abs_py + abs_ph), p_col, 1)

        # 4. Flashing Tactical Breach Alert Banner
        if has_breach and self.flash_state and not is_godeye_mode:
            alert_bar_h = 38
            alert_y = 56
            alert_overlay = frame.copy()
            cv2.rectangle(alert_overlay, (int(w * 0.10), alert_y), (int(w * 0.90), alert_y + alert_bar_h), self.C_ALERT_RED, -1)
            cv2.addWeighted(alert_overlay, 0.85, frame, 0.15, 0, frame)
            
            alert_str = f"*** TACTICAL PERIMETER BREACH DETECTED ({len(active_breaches)} TARGETS IN STERILE ZONE) ***"
            (atw, ath), _ = cv2.getTextSize(alert_str, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 2)
            ax = int((w - atw) / 2)
            cv2.putText(frame, alert_str, (ax, alert_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2, cv2.LINE_AA)

        # 7. Bottom Tactical Control Ribbon
        bot_h = 32
        bot_overlay = frame.copy()
        cv2.rectangle(bot_overlay, (0, h - bot_h), (w, h), self.C_DARK_BG, -1)
        cv2.addWeighted(bot_overlay, 0.75, frame, 0.25, 0, frame)
        cv2.line(frame, (0, h - bot_h), (w, h - bot_h), (80, 90, 100), 1, cv2.LINE_AA)

        shortcuts = "[1-5] SECTOR | [MODE] SPECTRA | [K] SCOPE MASK | [R] RESET STREAM | [S] SEC-65B EVIDENCE"
        cv2.putText(frame, shortcuts, (15, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 210, 220), 1, cv2.LINE_AA)

        if muted:
            cv2.putText(frame, "[AUDIO MUTED]", (w - 140, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.42, self.C_WARNING_AMBER, 1, cv2.LINE_AA)

        return frame

    def _draw_godeye_grid(self, frame, w, h):
        """Draws movie-authentic crosshair coordinate dot grid."""
        step = 90
        dot_col = (100, 140, 130)
        for x in range(step, w - step, step):
            for y in range(70, h - 50, step):
                cv2.line(frame, (x - 3, y), (x + 3, y), dot_col, 1, cv2.LINE_AA)
                cv2.line(frame, (x, y - 3), (x, y + 3), dot_col, 1, cv2.LINE_AA)

