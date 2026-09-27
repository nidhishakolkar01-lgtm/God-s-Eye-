"""
PROJECT TRINETRA-C2 // RASPBERRY PI 3 HARDWARE PERIPHERAL NODE
Platform: Raspberry Pi 3 Model B (Raspberry Pi OS)
Hardware:
 - 5MP OV5647 IR-Cut Day/Night Camera (CSI Ribbon cable)
 - Pan Servo: GPIO 17 (Pin 11) - Hardware/Software PWM
 - Tilt Servo: GPIO 18 (Pin 12) - Hardware PWM
 - IR-Cut Filter Solenoid: GPIO 27 (Pin 13)

Usage:
  python3 pi_hardware_node.py --c2-host 192.168.1.100 --c2-port 8080
"""

import time
import argparse
import json

try:
    import RPi.GPIO as GPIO
    HAS_RPI_GPIO = True
except ImportError:
    HAS_RPI_GPIO = False
    print("[PI-NODE WARNING] RPi.GPIO not available. Running in simulated dry-run mode.")

PIN_PAN_SERVO = 17
PIN_TILT_SERVO = 18
PIN_IRCUT = 27

class PiHardwareController:
    def __init__(self):
        self.pan_pwm = None
        self.tilt_pwm = None
        self.setup_gpio()

    def setup_gpio(self):
        if not HAS_RPI_GPIO:
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        # Setup Servos (50Hz PWM)
        GPIO.setup(PIN_PAN_SERVO, GPIO.OUT)
        GPIO.setup(PIN_TILT_SERVO, GPIO.OUT)
        self.pan_pwm = GPIO.PWM(PIN_PAN_SERVO, 50)
        self.tilt_pwm = GPIO.PWM(PIN_TILT_SERVO, 50)
        self.pan_pwm.start(7.5)   # 90 degrees neutral
        self.tilt_pwm.start(7.5)  # 90 degrees neutral

        # Setup IR-Cut Solenoid
        GPIO.setup(PIN_IRCUT, GPIO.OUT)
        GPIO.output(PIN_IRCUT, GPIO.HIGH) # Daylight filter engaged

        print("[PI-NODE] GPIO initialized successfully: Pan=GPIO17, Tilt=GPIO18, IRCut=GPIO27")

    def angle_to_duty(self, angle):
        """Converts 0-180 degree angle to 50Hz PWM duty cycle (2.5% to 12.5%)."""
        return 2.5 + (angle / 18.0)

    def set_servos(self, pan_deg, tilt_deg):
        pan_deg = max(10, min(170, pan_deg))
        tilt_deg = max(15, min(165, tilt_deg))
        if HAS_RPI_GPIO:
            self.pan_pwm.ChangeDutyCycle(self.angle_to_duty(pan_deg))
            self.tilt_pwm.ChangeDutyCycle(self.angle_to_duty(tilt_deg))
        print(f"[PI-ACTUATOR] Pan: {pan_deg}° | Tilt: {tilt_deg}°")

    def set_ircut(self, engage_filter: bool):
        if HAS_RPI_GPIO:
            GPIO.output(PIN_IRCUT, GPIO.HIGH if engage_filter else GPIO.LOW)
        state = "OPTICAL DAYLIGHT ENGAGED" if engage_filter else "NIGHT IR-PASS RETRACTED"
        print(f"[PI-ACTUATOR] IR-Cut Filter State: {state}")

    def cleanup(self):
        if HAS_RPI_GPIO:
            if self.pan_pwm: self.pan_pwm.stop()
            if self.tilt_pwm: self.tilt_pwm.stop()
            GPIO.cleanup()
        print("[PI-NODE] Cleaned up GPIO.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TRINETRA-C2 Pi Hardware Node")
    parser.add_argument("--test", action="store_true", help="Run automated servo sweep test")
    args = parser.parse_args()

    node = PiHardwareController()
    try:
        if args.test:
            print("[PI-NODE] Running Turret Pan-Tilt calibration sweep...")
            for a in [45, 90, 135, 90]:
                node.set_servos(a, a)
                time.sleep(0.8)
            print("[PI-NODE] Testing IR-Cut filter toggle...")
            node.set_ircut(False) # Night
            time.sleep(1.0)
            node.set_ircut(True)  # Day
            time.sleep(0.5)
            print("[PI-NODE] Calibration completed successfully!")
    finally:
        node.cleanup()
