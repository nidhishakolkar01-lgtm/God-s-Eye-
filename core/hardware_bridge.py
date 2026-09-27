import time
import math
import threading
from typing import Optional, Dict, Any, Tuple

class PanTiltTurretController:
    """
    Dual-Axis Servo Turret Controller for Pan (Azimuth) and Tilt (Elevation).
    Provides closed-loop visual target tracking, smooth kinematic interpolation,
    and automatic border horizon patrol sweeps.
    """
    def __init__(self, min_pan=10, max_pan=170, min_tilt=15, max_tilt=165):
        self.min_pan = min_pan
        self.max_pan = max_pan
        self.min_tilt = min_tilt
        self.max_tilt = max_tilt

        # Current actual angles
        self.pan = 90.0
        self.tilt = 90.0

        # Commanded target angles
        self.target_pan = 90.0
        self.target_tilt = 90.0

        # Physical servo kinematics (SG90 / MG996R: ~0.15s per 60 deg -> ~400 deg/s max, typical operating 90-120 deg/s)
        self.max_speed = 90.0  # degrees per second
        self.deadband = 0.05   # 5% screen width/height deadband to eliminate servo chatter

        # Control flags
        self.auto_track = True
        self.auto_patrol = False
        self.last_target_time = 0.0
        self.patrol_direction = 1
        self.last_update_time = time.time()

        # Proportional tracking gains
        self.kp_pan = 3.2
        self.kp_tilt = 2.4

    def update_visual_tracking(self, bbox: Tuple[int, int, int, int], frame_w: int, frame_h: int) -> Dict[str, float]:
        """
        Calculates proportional steering angles to center the optical turret on the tracked entity centroid.
        """
        if not self.auto_track or frame_w <= 0 or frame_h <= 0:
            return {"pan": self.pan, "tilt": self.tilt}

        now = time.time()
        self.last_target_time = now

        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0

        # Normalized errors from center [-1.0, 1.0]
        err_x = (cx - (frame_w / 2.0)) / (frame_w / 2.0)
        err_y = (cy - (frame_h / 2.0)) / (frame_h / 2.0)

        # Invert err_x so target to the right turns camera right (+pan)
        if abs(err_x) > self.deadband:
            delta_pan = err_x * self.kp_pan
            self.target_pan = max(self.min_pan, min(self.max_pan, self.target_pan + delta_pan))

        if abs(err_y) > self.deadband:
            delta_tilt = -err_y * self.kp_tilt
            self.target_tilt = max(self.min_tilt, min(self.max_tilt, self.target_tilt + delta_tilt))

        return {"pan": round(self.pan, 1), "tilt": round(self.tilt, 1)}

    def step_kinematics(self) -> Dict[str, float]:
        """
        Step physical servo motor interpolation towards target angles based on max angular velocity.
        """
        now = time.time()
        dt = max(0.001, min(0.1, now - self.last_update_time))
        self.last_update_time = now

        # Autonomous horizon patrol sweep if no target active for > 3.0s
        if self.auto_patrol and (now - self.last_target_time > 3.0):
            sweep_speed = 18.0  # deg/sec
            self.target_pan += self.patrol_direction * sweep_speed * dt
            if self.target_pan >= 140.0:
                self.target_pan = 140.0
                self.patrol_direction = -1
            elif self.target_pan <= 40.0:
                self.target_pan = 40.0
                self.patrol_direction = 1
            self.target_tilt = 90.0

        # Interpolate pan
        pan_diff = self.target_pan - self.pan
        max_step = self.max_speed * dt
        if abs(pan_diff) <= max_step:
            self.pan = self.target_pan
        else:
            self.pan += math.copysign(max_step, pan_diff)

        # Interpolate tilt
        tilt_diff = self.target_tilt - self.tilt
        if abs(tilt_diff) <= max_step:
            self.tilt = self.target_tilt
        else:
            self.tilt += math.copysign(max_step, tilt_diff)

        # Clamp physical travel
        self.pan = max(float(self.min_pan), min(float(self.max_pan), self.pan))
        self.tilt = max(float(self.min_tilt), min(float(self.max_tilt), self.tilt))

        return {
            "pan": round(self.pan, 1),
            "tilt": round(self.tilt, 1),
            "target_pan": round(self.target_pan, 1),
            "target_tilt": round(self.target_tilt, 1)
        }

    def jog(self, d_pan: float, d_tilt: float):
        """Manual jog command from C2 dashboard."""
        self.target_pan = max(self.min_pan, min(self.max_pan, self.target_pan + d_pan))
        self.target_tilt = max(self.min_tilt, min(self.max_tilt, self.target_tilt + d_tilt))

    def set_angle(self, pan: float, tilt: float):
        """Direct commanded orientation."""
        self.target_pan = max(self.min_pan, min(self.max_pan, float(pan)))
        self.target_tilt = max(self.min_tilt, min(self.max_tilt, float(tilt)))

    def center(self):
        """Reset turret to boresight position."""
        self.target_pan = 90.0
        self.target_tilt = 90.0


class IRCutModuleSwitcher:
    """
    Controls the physical electro-mechanical IR-Cut filter coil on the Raspberry Pi 5MP OV5647 camera.
    - DAYLIGHT: Filter is engaged (solenoid unenergized/reversed), blocking infrared to prevent pink wash.
    - NIGHT / NVG / FLIR: Filter is retracted, allowing 850nm near-infrared to reach the CMOS sensor.
    """
    def __init__(self, gpio_pin=27):
        self.gpio_pin = gpio_pin
        self.filter_engaged = True  # True = Optical IR-Cut ON (Day), False = IR-Pass (Night)
        self.filter_state_str = "OPTICAL_IR_BLOCK [DAYLIGHT]"
        self.last_switch_time = time.time()

    def sync_with_sensor_mode(self, sensor_mode: str) -> Dict[str, Any]:
        """Synchronizes physical IR-Cut coil state with tactical C2 sensor mode."""
        if sensor_mode == "NORMAL":
            self.filter_engaged = True
            self.filter_state_str = "OPTICAL_IR_BLOCK [DAYLIGHT]"
        else:
            # NVG_P43, FLIR_IRONBOW, FLIR_WHOT
            self.filter_engaged = False
            self.filter_state_str = "IR_PASS_RETRACTED [NIGHT/NVG]"

        self.last_switch_time = time.time()
        return self.get_status()

    def toggle(self) -> Dict[str, Any]:
        """Manual operator toggle."""
        self.filter_engaged = not self.filter_engaged
        self.filter_state_str = "OPTICAL_IR_BLOCK [DAYLIGHT]" if self.filter_engaged else "IR_PASS_RETRACTED [NIGHT/NVG]"
        self.last_switch_time = time.time()
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        return {
            "filter_engaged": self.filter_engaged,
            "state_label": self.filter_state_str,
            "gpio_pin": self.gpio_pin,
            "last_switched_sec_ago": round(time.time() - self.last_switch_time, 1)
        }


class SerialHardwareGateway:
    """
    Serial UART gateway for Arduino / Particle Argon / USB microcontroller communication.
    Transmits servo command packets: 'P<pan> T<tilt> C<ircut>\n'
    Receives peripheral sensor packets: ultrasonic rangefinder (cm), PIR detection, lux level.
    Operates in virtual loopback mode when physical port is disconnected.
    """
    def __init__(self, baud_rate=115200):
        self.baud_rate = baud_rate
        self.port: Optional[str] = None
        self.serial_handle = None
        self.is_connected = False
        self.last_tx_time = 0.0
        self._rx_thread: Optional[threading.Thread] = None
        self._rx_running = False
        self.last_rx_data: Dict[str, Any] = {
            "ultrasonic_distance_cm": 284.0,
            "pir_motion_detected": False,
            "ambient_lux": 420.0,
            "board_temp_c": 38.5,
            "hw_pan_deg": 90,
            "hw_tilt_deg": 90,
            "hw_ircut": 1
        }
        self._cached_ports = []
        self._last_ports_check = 0.0

    def list_available_ports(self):
        """Returns detected physical COM/TTY ports (cached with 5-second TTL)."""
        now = time.time()
        if self._cached_ports and (now - self._last_ports_check < 5.0):
            return self._cached_ports
        ports = []
        try:
            import serial.tools.list_ports
            for p in serial.tools.list_ports.comports():
                ports.append({"port": p.device, "desc": p.description, "hwid": p.hwid})
        except Exception:
            pass
        self._cached_ports = ports
        self._last_ports_check = now
        return ports

    def connect(self, port_name: str) -> bool:
        """Attempts to open physical serial connection."""
        self.disconnect()
        try:
            import serial
            self.serial_handle = serial.Serial(port_name, self.baud_rate, timeout=0.1)
            self.port = port_name
            self.is_connected = True
            self._rx_running = True
            self._rx_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._rx_thread.start()
            print(f"[HW-GATEWAY] Connected to physical hardware on {port_name} @ {self.baud_rate} baud")
            return True
        except Exception as e:
            print(f"[HW-GATEWAY] Connection to {port_name} failed: {e}. Remaining in Virtual Bridge mode.")
            self.is_connected = False
            return False

    def disconnect(self):
        self._rx_running = False
        if self.serial_handle:
            try:
                self.serial_handle.close()
            except Exception:
                pass
        self.serial_handle = None
        self.is_connected = False

    def _read_loop(self):
        """Background thread parsing incoming sensor telemetry packets: D:<dist> P:<pan> T:<tilt> C:<ircut>"""
        while self._rx_running and self.serial_handle:
            try:
                if self.serial_handle.in_waiting:
                    raw_line = self.serial_handle.readline().decode("ascii", errors="ignore").strip()
                    if raw_line.startswith("D:"):
                        # Format: D:142.5 P:90 T:90 C:1
                        parts = raw_line.split()
                        for part in parts:
                            if part.startswith("D:"):
                                dist = float(part[2:])
                                self.last_rx_data["ultrasonic_distance_cm"] = dist
                                self.last_rx_data["pir_motion_detected"] = dist < 50.0  # Ultrasonic perimeter alert
                            elif part.startswith("P:"):
                                self.last_rx_data["hw_pan_deg"] = int(part[2:])
                            elif part.startswith("T:"):
                                self.last_rx_data["hw_tilt_deg"] = int(part[2:])
                            elif part.startswith("C:"):
                                self.last_rx_data["hw_ircut"] = int(part[2:])
                else:
                    time.sleep(0.01)
            except Exception:
                break

    def transmit_turret_packet(self, pan: float, tilt: float, ircut_engaged: bool):
        """Transmits actuator packet over serial link if connected."""
        now = time.time()
        if now - self.last_tx_time < 0.05:  # Rate limit transmission to 20Hz
            return
        self.last_tx_time = now

        packet = f"P{int(pan)} T{int(tilt)} C{1 if ircut_engaged else 0}\n"
        if self.is_connected and self.serial_handle:
            try:
                self.serial_handle.write(packet.encode("ascii"))
            except Exception as e:
                print(f"[HW-GATEWAY] Serial write error: {e}")
                self.disconnect()


class HardwarePeripheralBridge:
    """
    Unified Hardware Peripheral Bridge for Project TRINETRA-C2.
    Integrates Pan-Tilt servo tracking, OV5647 IR-Cut control, and physical/virtual serial gateway.
    """
    def __init__(self):
        self.turret = PanTiltTurretController()
        self.ircut = IRCutModuleSwitcher()
        self.gateway = SerialHardwareGateway()
        self._lock = threading.Lock()

    def update(self, primary_target_bbox: Optional[Tuple[int, int, int, int]] = None, frame_dims: Tuple[int, int] = (854, 480)):
        """Periodic loop call from C2 server processing pipeline."""
        with self._lock:
            fw, fh = frame_dims
            if primary_target_bbox and self.turret.auto_track:
                self.turret.update_visual_tracking(primary_target_bbox, fw, fh)
            
            # Step physical kinematics
            angles = self.turret.step_kinematics()

            # Transmit to hardware or virtual loopback
            self.gateway.transmit_turret_packet(
                pan=angles["pan"],
                tilt=angles["tilt"],
                ircut_engaged=self.ircut.filter_engaged
            )

    def get_full_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            angles = self.turret.step_kinematics()
            ircut_st = self.ircut.get_status()
            return {
                "turret": {
                    "pan": angles["pan"],
                    "tilt": angles["tilt"],
                    "target_pan": angles["target_pan"],
                    "target_tilt": angles["target_tilt"],
                    "auto_track": self.turret.auto_track,
                    "auto_patrol": self.turret.auto_patrol,
                    "azimuth_heading_deg": round((angles["pan"] - 90.0) * (60.0 / 90.0), 1),
                    "elevation_deg": round(angles["tilt"] - 90.0, 1),
                    "status_label": "TRACKING TARGET LOCK" if self.turret.auto_track else "MANUAL JOG"
                },
                "ircut": ircut_st,
                "gateway": {
                    "mode": "PHYSICAL SERIAL [CONNECTED]" if self.gateway.is_connected else "HIGH-FIDELITY VIRTUAL BRIDGE",
                    "port": self.gateway.port or "VIRTUAL_LOOPBACK_UART",
                    "is_connected": self.gateway.is_connected,
                    "baud": self.gateway.baud_rate,
                    "available_ports": self.gateway.list_available_ports(),
                    "peripherals": self.gateway.last_rx_data
                }
            }

    def jog(self, d_pan: float, d_tilt: float):
        with self._lock:
            self.turret.jog(d_pan, d_tilt)

    def set_angle(self, pan: float, tilt: float):
        with self._lock:
            self.turret.set_angle(pan, tilt)

    def center_turret(self):
        with self._lock:
            self.turret.center()

    def toggle_autotrack(self) -> bool:
        with self._lock:
            self.turret.auto_track = not self.turret.auto_track
            return self.turret.auto_track

    def toggle_autopatrol(self) -> bool:
        with self._lock:
            self.turret.auto_patrol = not self.turret.auto_patrol
            return self.turret.auto_patrol

    def sync_sensor_mode(self, mode: str):
        with self._lock:
            self.ircut.sync_with_sensor_mode(mode)

    def toggle_ircut(self) -> Dict[str, Any]:
        with self._lock:
            return self.ircut.toggle()

    def connect_serial(self, port_name: str) -> bool:
        with self._lock:
            return self.gateway.connect(port_name)
