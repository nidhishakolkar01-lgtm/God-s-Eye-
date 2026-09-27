"""
PROJECT TRINETRA-C2 // AUTONOMOUS AIRBORNE FLIGHT CONTROLLER & PID SERVOING ENGINE
Provides UDP flight command transmission, PID visual tracking, proximity hold,
and failsafe auto-hover for WiFi-UFO / E88 Plus quadcopters.
"""

import time
import socket
import threading
from typing import Tuple, Optional, Dict, Any

class PIDController:
    """Discrete PID controller with anti-windup integrator clamping and derivative filtering."""
    def __init__(self, kp: float, ki: float, kd: float, output_limits: Tuple[float, float] = (-1.0, 1.0)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.min_out, self.max_out = output_limits

        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = time.time()

    def reset(self):
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = time.time()

    def update(self, error: float) -> float:
        now = time.time()
        dt = max(0.001, min(0.1, now - self.last_time))
        self.last_time = now

        # Proportional
        p_term = self.kp * error

        # Integral with anti-windup clamping
        self.integral += error * dt
        self.integral = max(-0.3, min(0.3, self.integral))
        i_term = self.ki * self.integral

        # Derivative
        derivative = (error - self.last_error) / dt
        self.last_error = error
        d_term = self.kd * derivative

        output = p_term + i_term + d_term
        return max(self.min_out, min(self.max_out, output))


class DroneFlightController:
    """
    Autonomous Flight & Visual Servoing Manager for E88 Plus / WiFi-UFO Drone.
    Transmits continuous 25Hz UDP heartbeat packets to Drone Flight MCU.
    """
    def __init__(self, drone_ip: str = "192.168.1.1", command_port: int = 50000):
        self.drone_ip = drone_ip
        self.command_port = command_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.lock = threading.Lock()

        # Current Flight Setpoints [0 - 255], 128 = Neutral Midpoint
        self.roll = 128       # Right/Left Tilt (128 = Level)
        self.pitch = 128      # Forward/Backward (128 = Level)
        self.throttle = 128   # Climb/Descend (128 = Auto-Hover Altitude Hold)
        self.yaw = 128        # Turn Right/Left (128 = Steady Heading)
        self.flags = 0x00     # Special function bits (Takeoff/Land/Stop)

        # Operational States
        self.is_armed = False
        self.is_flying = False
        self.auto_tracking_active = False
        self.emergency_stop_triggered = False
        self.last_target_seen = 0.0
        self.target_lost_timeout = 1.2  # Seconds before auto-hover fallback

        # Visual Servoing PIDs
        # Yaw: Horizontal centering
        self.pid_yaw = PIDController(kp=0.65, ki=0.02, kd=0.18, output_limits=(-0.6, 0.6))
        # Pitch: Distance/Stand-off hold (Target bounding box height ratio ~0.45)
        self.pid_pitch = PIDController(kp=0.55, ki=0.01, kd=0.15, output_limits=(-0.5, 0.5))
        # Throttle: Vertical eye-level centering
        self.pid_throttle = PIDController(kp=0.45, ki=0.01, kd=0.12, output_limits=(-0.4, 0.4))

        # Target setpoint parameters
        self.desired_target_height_ratio = 0.40  # Desired target screen height (standoff distance)
        self.deadband_x = 0.06  # 6% screen width deadband
        self.deadband_y = 0.08  # 8% screen height deadband
        self.deadband_dist = 0.08  # 8% distance deadband

        # Background UDP Heartbeat Loop (25Hz)
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()

    def _build_ufo_packet(self) -> bytes:
        """Standard 8-byte WiFi-UFO / E88 binary packet."""
        with self.lock:
            r = int(max(0, min(255, self.roll)))
            p = int(max(0, min(255, self.pitch)))
            t = int(max(0, min(255, self.throttle)))
            y = int(max(0, min(255, self.yaw)))
            f = int(self.flags)
            chk = (r ^ p ^ t ^ y ^ f) & 0xFF
            return bytes([0x66, r, p, t, y, f, chk, 0x99])

    def _build_ky_packet(self) -> bytes:
        """11-byte KY-FPV / 4-Axis packet."""
        with self.lock:
            r, p, t, y, f = int(self.roll), int(self.pitch), int(self.throttle), int(self.yaw), int(self.flags)
            chk = (r + p + t + y + f) & 0xFF
            return bytes([0xFF, 0x08, r, p, t, y, f, 0x00, chk, 0xAA])

    def _build_rc_packet(self) -> bytes:
        """6-byte RC-FPV packet."""
        with self.lock:
            return bytes([0xCC, int(self.roll), int(self.pitch), int(self.throttle), int(self.yaw), int(self.flags), 0x33])

    def _heartbeat_loop(self):
        """Continuous background transmission loop maintaining radio link across all known drone protocols."""
        ports = [50000, 7070, 8080, 8888, 60000]
        while self.running:
            now = time.time()
            if self.auto_tracking_active:
                if (now - self.last_target_seen) > self.target_lost_timeout:
                    with self.lock:
                        self.roll = 128
                        self.pitch = 128
                        self.yaw = 128
                        self.throttle = 128
                    self.pid_yaw.reset()
                    self.pid_pitch.reset()
                    self.pid_throttle.reset()

            ufo_pkt = self._build_ufo_packet()
            ky_pkt = self._build_ky_packet()
            rc_pkt = self._build_rc_packet()

            for p in ports:
                try:
                    self.sock.sendto(ufo_pkt, (self.drone_ip, p))
                    self.sock.sendto(ky_pkt, (self.drone_ip, p))
                    self.sock.sendto(rc_pkt, (self.drone_ip, p))
                except Exception:
                    pass

            time.sleep(0.04)  # 25 Hz transmission cadence

    def update_visual_servoing(self, bbox: Optional[Tuple[int, int, int, int]], frame_w: int, frame_h: int) -> Dict[str, Any]:
        """
        Calculates real-time PID flight corrections to keep target locked in crosshairs.
        Input:
            bbox: (x1, y1, x2, y2) bounding box of primary target in pixels
        """
        if not self.auto_tracking_active or not self.is_flying:
            return self.get_telemetry()

        if bbox is None or frame_w <= 0 or frame_h <= 0:
            return self.get_telemetry()

        now = time.time()
        self.last_target_seen = now

        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        target_h = max(1.0, float(y2 - y1))

        # Normalized Error Coordinates [-1.0, 1.0]
        # err_x: >0 means target is to the right of center (drone needs to YAW right)
        err_x = (cx - (frame_w / 2.0)) / (frame_w / 2.0)
        # err_y: >0 means target is below center (drone needs to DESCEND or pitch down)
        err_y = (cy - (frame_h / 2.0)) / (frame_h / 2.0)

        # Distance error: Target height ratio compared to desired ratio
        current_h_ratio = target_h / float(frame_h)
        err_dist = self.desired_target_height_ratio - current_h_ratio

        # 1. YAW AXIS CORRECTION (Horizontal Centering)
        if abs(err_x) > self.deadband_x:
            yaw_corr = self.pid_yaw.update(err_x)  # [-0.6, 0.6]
            target_yaw = int(128 + (yaw_corr * 80))
        else:
            self.pid_yaw.reset()
            target_yaw = 128

        # 2. PITCH AXIS CORRECTION (Standoff Distance Hold)
        if abs(err_dist) > self.deadband_dist:
            pitch_corr = self.pid_pitch.update(err_dist)  # >0 = too far (move forward), <0 = too close
            target_pitch = int(128 + (pitch_corr * 70))
        else:
            self.pid_pitch.reset()
            target_pitch = 128

        # 3. THROTTLE AXIS CORRECTION (Altitude Eye-Level Hold)
        if abs(err_y) > self.deadband_y:
            # err_y > 0 (target is lower on screen) -> reduce throttle or descend
            throttle_corr = self.pid_throttle.update(-err_y)
            target_throttle = int(128 + (throttle_corr * 60))
        else:
            self.pid_throttle.reset()
            target_throttle = 128

        with self.lock:
            self.yaw = target_yaw
            self.pitch = target_pitch
            self.throttle = target_throttle
            self.roll = 128  # Keep level bank angle

        return self.get_telemetry()

    def set_manual_controls(self, roll_pct: float, pitch_pct: float, throttle_pct: float, yaw_pct: float):
        """
        Sets manual flight inputs from keyboard or joystick (-1.0 to 1.0).
        """
        with self.lock:
            self.roll = int(128 + max(-1.0, min(1.0, roll_pct)) * 100)
            self.pitch = int(128 + max(-1.0, min(1.0, pitch_pct)) * 100)
            self.throttle = int(128 + max(-1.0, min(1.0, throttle_pct)) * 100)
            self.yaw = int(128 + max(-1.0, min(1.0, yaw_pct)) * 100)

    def trigger_takeoff(self):
        """Commands drone to arm motors and auto-takeoff to 1.2m hover via multi-protocol pulse burst."""
        def _burst():
            ports = [50000, 7070, 8080, 8888, 60000]
            # Step 1: Calibration / Arming Pulse (0.3s)
            cal_pkt = bytes([0x66, 128, 128, 0, 128, 0x01, (128^128^0^128^0x01)&0xFF, 0x99])
            for _ in range(8):
                for p in ports:
                    try:
                        self.sock.sendto(cal_pkt, (self.drone_ip, p))
                    except Exception:
                        pass
                time.sleep(0.04)

            # Step 2: Takeoff Pulse (0.6s)
            with self.lock:
                self.is_armed = True
                self.is_flying = True
                self.emergency_stop_triggered = False
                self.flags = 0x01
                self.throttle = 128
                self.pitch = 128
                self.roll = 128
                self.yaw = 128

            takeoff_ufo = self._build_ufo_packet()
            takeoff_ky = self._build_ky_packet()
            takeoff_rc = self._build_rc_packet()
            for _ in range(15):
                for p in ports:
                    try:
                        self.sock.sendto(takeoff_ufo, (self.drone_ip, p))
                        self.sock.sendto(takeoff_ky, (self.drone_ip, p))
                        self.sock.sendto(takeoff_rc, (self.drone_ip, p))
                    except Exception:
                        pass
                time.sleep(0.04)

            with self.lock:
                self.flags = 0x00

        threading.Thread(target=_burst, daemon=True).start()
        print("[FLIGHT-CORE] Auto-Takeoff multi-protocol burst transmitted.")

    def trigger_land(self):
        """Commands drone to auto-land and disarm motors."""
        def _burst():
            ports = [50000, 7070, 8080, 8888, 60000]
            with self.lock:
                self.auto_tracking_active = False
                self.flags = 0x02  # Auto-land flag
                self.roll = 128
                self.pitch = 128
                self.yaw = 128
                self.throttle = 128

            land_ufo = self._build_ufo_packet()
            land_ky = self._build_ky_packet()
            land_rc = self._build_rc_packet()
            for _ in range(20):
                for p in ports:
                    try:
                        self.sock.sendto(land_ufo, (self.drone_ip, p))
                        self.sock.sendto(land_ky, (self.drone_ip, p))
                        self.sock.sendto(land_rc, (self.drone_ip, p))
                    except Exception:
                        pass
                time.sleep(0.04)

            with self.lock:
                self.is_armed = False
                self.is_flying = False
                self.flags = 0x00

        threading.Thread(target=_burst, daemon=True).start()
        print("[FLIGHT-CORE] Auto-Land command transmitted.")

    def trigger_emergency_stop(self):
        """INSTANT EMERGENCY KILL SWITCH: Cuts all motor power immediately."""
        with self.lock:
            self.is_armed = False
            self.is_flying = False
            self.auto_tracking_active = False
            self.emergency_stop_triggered = True
            self.flags = 0x08  # Emergency kill switch bit
            self.throttle = 0
            self.pitch = 128
            self.roll = 128
            self.yaw = 128
        print("[EMERGENCY] KILL SWITCH ENGAGED! ALL MOTOR POWER CUT.")

    def _clear_transient_flags(self):
        with self.lock:
            self.flags = 0x00

    def _finalize_landing(self):
        with self.lock:
            self.is_armed = False
            self.is_flying = False
            self.flags = 0x00

    def toggle_auto_tracking(self) -> bool:
        return self.toggle_autotrack()

    def toggle_autotrack(self) -> bool:
        """Toggles AI PID Visual Servoing on/off."""
        self.auto_tracking_active = not self.auto_tracking_active
        if not self.auto_tracking_active:
            self.pid_yaw.reset()
            self.pid_pitch.reset()
            self.pid_throttle.reset()
            with self.lock:
                self.roll = 128
                self.pitch = 128
                self.yaw = 128
                self.throttle = 128
        return self.auto_tracking_active

    def get_telemetry(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "roll": self.roll,
                "pitch": self.pitch,
                "throttle": self.throttle,
                "yaw": self.yaw,
                "flags": self.flags,
                "is_flying": self.is_flying,
                "is_armed": self.is_armed,
                "auto_tracking": self.auto_tracking_active,
                "emergency_stop": self.emergency_stop_triggered,
                "pitch_offset_pct": round((self.pitch - 128) / 128.0 * 100, 1),
                "yaw_offset_pct": round((self.yaw - 128) / 128.0 * 100, 1),
                "throttle_offset_pct": round((self.throttle - 128) / 128.0 * 100, 1)
            }

    def stop(self):
        self.close()

    def close(self):
        self.running = False
        self.trigger_emergency_stop()
        if hasattr(self, 'sock'):
            self.sock.close()
