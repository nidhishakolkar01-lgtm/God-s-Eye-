"""
PROJECT TRINETRA-C2 // GROUND STATION SERIAL RF TRANSMITTER BRIDGE
Communicates with Arduino Nano + NRF24L01 over USB COM Port at 115200 Baud.
Dispatches Real-Time Closed-Loop PID Visual Servoing Setpoints to the 2.4GHz RF Link.
"""

import time
import threading
from typing import Optional, Dict, Any, Tuple

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    serial = None
    SERIAL_AVAILABLE = False


class GroundStationRFBridge:
    """
    High-Speed USB Serial Bridge to Arduino Nano 2.4GHz RF Transmitter.
    Transmits binary telemetry packets at 50Hz:
    [0xAA, Roll, Pitch, Throttle, Yaw, Flags, Checksum, 0x55]
    """
    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.baudrate = baudrate
        self.port_name = port
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        self.lock = threading.Lock()

        # Flight Setpoints [0-255], 128 = Neutral
        self.roll = 128
        self.pitch = 128
        self.throttle = 0
        self.yaw = 128
        self.flags = 0  # Bit 0: Takeoff, Bit 1: Land, Bit 3: Emergency Kill

        self.running = True
        self._auto_connect()

        self.thread = threading.Thread(target=self._tx_worker, daemon=True)
        self.thread.start()

    def _auto_connect(self):
        """Auto-discovers Arduino Nano CH340 / FTDI / CP2102 COM Port."""
        if not SERIAL_AVAILABLE or serial is None:
            return
        if self.port_name:
            ports = [self.port_name]
        else:
            available = list(serial.tools.list_ports.comports())
            ports = [p.device for p in available if "CH340" in p.description or "Arduino" in p.description or "USB" in p.description or "Serial" in p.description]
            if not ports and available:
                ports = [available[0].device]

        for p in ports:
            try:
                self.ser = serial.Serial(p, self.baudrate, timeout=0.1)
                time.sleep(1.5)  # Wait for Arduino bootloader reset
                self.is_connected = True
                self.port_name = p
                print(f"[RF-BRIDGE] Connected to Arduino Ground Station on: {p} @ {self.baudrate} Baud.")
                return
            except Exception as e:
                print(f"[RF-BRIDGE] Could not connect to {p}: {e}")

        print("[RF-BRIDGE] Notice: Arduino Ground Station not detected. Running in Virtual Telemetry Mode.")
        self.is_connected = False

    def _build_packet(self) -> bytes:
        with self.lock:
            r = int(max(0, min(255, self.roll)))
            p = int(max(0, min(255, self.pitch)))
            t = int(max(0, min(255, self.throttle)))
            y = int(max(0, min(255, self.yaw)))
            f = int(self.flags)
            chk = (r ^ p ^ t ^ y ^ f) & 0xFF
            return bytes([0xAA, r, p, t, y, f, chk, 0x55])

    def _tx_worker(self):
        """50Hz High-Speed Serial Transmission Loop."""
        while self.running:
            if self.is_connected and self.ser and self.ser.is_open:
                try:
                    pkt = self._build_packet()
                    self.ser.write(pkt)
                except Exception as e:
                    print(f"[RF-BRIDGE] Serial write error: {e}")
                    self.is_connected = False
            time.sleep(0.02)  # 50Hz transmission cadence

    def set_flight_setpoints(self, roll: int, pitch: int, throttle: int, yaw: int, flags: int = 0):
        with self.lock:
            self.roll = roll
            self.pitch = pitch
            self.throttle = throttle
            self.yaw = yaw
            self.flags = flags

    def trigger_takeoff(self):
        """Commands drone to auto-takeoff to 1.2m hover."""
        with self.lock:
            self.throttle = 140
            self.pitch = 128
            self.roll = 128
            self.yaw = 128
            self.flags = 0x01
        print("[RF-BRIDGE] 2.4GHz Auto-Takeoff RF Command Transmitted!")
        threading.Timer(0.8, self._clear_flags).start()

    def trigger_land(self):
        """Commands drone to auto-land."""
        with self.lock:
            self.throttle = 60
            self.flags = 0x02
        print("[RF-BRIDGE] 2.4GHz Auto-Landing RF Command Transmitted.")
        threading.Timer(1.5, self._stop_throttle).start()

    def trigger_emergency_stop(self):
        """EMERGENCY MOTOR CUT: 0 Throttle immediately."""
        with self.lock:
            self.throttle = 0
            self.flags = 0x08
        print("[RF-BRIDGE] EMERGENCY KILL SWITCH: 2.4GHz Motor Power CUT.")

    def _clear_flags(self):
        with self.lock:
            self.flags = 0x00

    def _stop_throttle(self):
        with self.lock:
            self.throttle = 0
            self.flags = 0x00

    def close(self):
        self.running = False
        self.trigger_emergency_stop()
        if self.ser and self.ser.is_open:
            self.ser.close()
