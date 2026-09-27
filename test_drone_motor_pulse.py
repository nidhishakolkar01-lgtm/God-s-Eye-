"""
DRONE MOTOR & CONTROL PROTOCOL PROBE TOOL
Tests all standard WiFi Drone protocols (WiFi-UFO, KY-FPV, VS-FPV, RC-CAM)
with proper Gyro Calibration, Arming sequences, and Motor Spin pulses.
"""

import time
import socket

DRONE_IP = "192.168.1.1"
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("=========================================================")
print("     E88 PLUS MOTOR & FLIGHT PROTOCOL DIAGNOSTIC TOOL    ")
print("=========================================================")
print("IMPORTANT: Make sure the PHYSICAL 2.4GHz HANDSET IS OFF")
print("so the drone is listening to the WiFi controller channel!\n")

def test_protocol_1_wifi_ufo():
    print("[TEST 1] Testing Protocol 1: Standard WiFi-UFO (8-Byte XOR)...")
    # 1. Gyro Calibration Packet (Hold for 0.5s)
    # [0x66, Roll, Pitch, Throttle, Yaw, Flags, Checksum, 0x99]
    cal_packet = bytes([0x66, 128, 128, 0, 128, 0x01, (128^128^0^128^0x01)&0xFF, 0x99])
    for _ in range(15):
        for port in [50000, 7070, 8080, 8888]:
            sock.sendto(cal_packet, (DRONE_IP, port))
        time.sleep(0.04)
    print("  -> Gyro Calibration pulse sent.")
    time.sleep(0.5)

    # 2. Unlock Motors / Takeoff Pulse (0.5s)
    takeoff_packet = bytes([0x66, 128, 128, 128, 128, 0x01, (128^128^128^128^0x01)&0xFF, 0x99])
    for _ in range(25):
        for port in [50000, 7070, 8080, 8888]:
            sock.sendto(takeoff_packet, (DRONE_IP, port))
        time.sleep(0.04)
    print("  -> Takeoff pulse sent.")

def test_protocol_2_ky_fpv():
    print("\n[TEST 2] Testing Protocol 2: KY-FPV / 4-Axis (11-Byte SUM)...")
    # [0xFF, 0x08, Roll, Pitch, Throttle, Yaw, Flags, Aux, Checksum, 0xAA]
    # Header 0xFF 0x08, Footer 0xAA
    r, p, t, y, f, aux = 128, 128, 128, 128, 0x01, 0x00
    chk = (r + p + t + y + f + aux) & 0xFF
    pkt = bytes([0xFF, 0x08, r, p, t, y, f, aux, chk, 0xAA])
    for _ in range(25):
        for port in [7070, 8080, 50000, 8888, 60000]:
            sock.sendto(pkt, (DRONE_IP, port))
        time.sleep(0.04)
    print("  -> KY-FPV Takeoff pulse sent.")

def test_protocol_3_rc_fpv():
    print("\n[TEST 3] Testing Protocol 3: RC-FPV / WiFi-CAM (6-Byte)...")
    # [0xCC, Roll, Pitch, Throttle, Yaw, Flags, 0x33]
    pkt = bytes([0xCC, 128, 128, 128, 128, 0x01, 0x33])
    for _ in range(25):
        for port in [50000, 7070, 8080, 8888, 20000]:
            sock.sendto(pkt, (DRONE_IP, port))
        time.sleep(0.04)
    print("  -> RC-FPV pulse sent.")

def test_protocol_4_lf_drone():
    print("\n[TEST 4] Testing Protocol 4: LF-Drone / VS-FPV (Heartbeat Handshake)...")
    handshakes = [
        b'\x20\x00',
        b'CONNECT',
        bytes([0x66, 0x01, 0x01, 0x99]),
        bytes([0xFF, 0x01, 0x01, 0xFF])
    ]
    for h in handshakes:
        for port in [50000, 7070, 8080, 8888]:
            sock.sendto(h, (DRONE_IP, port))
        time.sleep(0.05)
    print("  -> Handshakes completed.")

if __name__ == "__main__":
    print("Select test action:")
    print(" 1. Test Protocol 1 (WiFi-UFO)")
    print(" 2. Test Protocol 2 (KY-FPV)")
    print(" 3. Test Protocol 3 (RC-FPV)")
    print(" 4. Test Protocol 4 (LF-Drone Handshake)")
    print(" 5. Run ALL protocols sequentially (Watch for motor spin)")
    
    choice = input("\nEnter choice [1-5]: ").strip()
    if choice == "1":
        test_protocol_1_wifi_ufo()
    elif choice == "2":
        test_protocol_2_ky_fpv()
    elif choice == "3":
        test_protocol_3_rc_fpv()
    elif choice == "4":
        test_protocol_4_lf_drone()
    else:
        test_protocol_4_lf_drone()
        test_protocol_1_wifi_ufo()
        test_protocol_2_ky_fpv()
        test_protocol_3_rc_fpv()

    print("\nTest completed.")
