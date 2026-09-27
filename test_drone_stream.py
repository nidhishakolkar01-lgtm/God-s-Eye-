import cv2
import socket
import time
import urllib.request
import threading
import numpy as np

DRONE_IP = "192.168.1.1"

print("=========================================================")
print("   GODS EYE: AIRBORNE SENTRY (E88 PLUS WIFI-UFO LINK)   ")
print("=========================================================")
print(f"[INIT] Target Drone IP: {DRONE_IP}")

# 1. Send WIFI-UFO video activation handshake ping over UDP
def send_handshake():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(0.5)
        # Standard activation pings for WIFI-UFO / KY-UFO cameras
        handshake_payloads = [
            b'\x20\x00',
            b'OPEN_STREAM',
            b'\xff\x08\x00\xff\x00\x00\x00\x00',
            b'\x66\x80\x80\x00\x80\x00\x80\x99'
        ]
        for port in [7070, 8080, 8888, 50000, 60000]:
            for payload in handshake_payloads:
                try:
                    sock.sendto(payload, (DRONE_IP, port))
                except Exception:
                    pass
        print("[INIT] Handshake packets sent to Drone camera ports.")
    except Exception as e:
        print(f"[WARN] Handshake exception: {e}")

send_handshake()

# 2. Candidate video stream endpoints for WIFI-UFO
candidate_urls = [
    f"http://{DRONE_IP}:8080/?action=stream",
    f"http://{DRONE_IP}:8080/stream",
    f"http://{DRONE_IP}:8080/videostream.cgi",
    f"http://{DRONE_IP}:8080/",
    f"http://{DRONE_IP}:7070/stream",
    f"http://{DRONE_IP}:8888/",
    f"rtsp://{DRONE_IP}:7070/webcam",
    f"rtsp://{DRONE_IP}:554/live/ch0",
    "udp://@0.0.0.0:8080",
    "udp://@0.0.0.0:7070"
]

stream_found = False
active_cap = None
active_url = ""

for url in candidate_urls:
    print(f"\n[PROBE] Attempting connection to: {url} ...")
    try:
        cap = cv2.VideoCapture(url)
        # Give it a moment to connect
        time.sleep(0.6)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                print(f"\n[LOCKED] SUCCESS! Stream locked onto: {url}")
                print(f"[LOCKED] Frame Resolution: {frame.shape[1]}x{frame.shape[0]}")
                stream_found = True
                active_cap = cap
                active_url = url
                break
            cap.release()
    except Exception as e:
        print(f"[PROBE] Failed: {e}")

if not stream_found:
    print("\n[PROBE] Direct stream URL test pending. Probing raw UDP listener...")
    # Attempt UDP listener mode
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.bind(("0.0.0.0", 8080))
    udp_sock.settimeout(2.0)
    try:
        data, addr = udp_sock.recvfrom(65535)
        print(f"[UDP-LOCK] Received {len(data)} raw bytes from {addr}!")
    except Exception as e:
        print(f"[INFO] UDP direct buffer: {e}")

if active_cap and active_cap.isOpened():
    print("\n[HUD] Launching Gods Eye Tactical HUD window (Press 'Q' to exit)...")
    fps_start = time.time()
    frame_count = 0
    fps = 0.0

    while True:
        ret, frame = active_cap.read()
        if not ret or frame is None:
            continue

        frame_count += 1
        if frame_count % 15 == 0:
            fps = round(15.0 / (time.time() - fps_start), 1)
            fps_start = time.time()

        h, w = frame.shape[:2]

        # Draw Gods Eye Tactical HUD Reticle
        cx, cy = w // 2, h // 2
        # Center targeting box
        cv2.rectangle(frame, (cx - 30, cy - 30), (cx + 30, cy + 30), (0, 255, 0), 1)
        cv2.line(frame, (cx - 45, cy), (cx + 45, cy), (0, 255, 0), 1)
        cv2.line(frame, (cx, cy - 45), (cx, cy + 45), (0, 255, 0), 1)

        # Header ribbon
        cv2.rectangle(frame, (0, 0), (w, 35), (20, 20, 20), -1)
        cv2.putText(frame, "GODS EYE: SECTOR-5 [AIRBORNE DRONE RECON - E88 PLUS]", (15, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2)
        cv2.putText(frame, f"FPS: {fps} | IP: {DRONE_IP}", (w - 200, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imshow("Gods Eye Airborne Sentry Feed", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    active_cap.release()
    cv2.destroyAllWindows()
else:
    print("\n[SUMMARY] Candidate scan finished. Ready to inspect stream response.")
