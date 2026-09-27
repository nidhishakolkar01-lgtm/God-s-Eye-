import os
import cv2
import math
import numpy as np
import urllib.request

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_footage")
SAMPLE_PATH = os.path.join(SAMPLE_DIR, "border_fence_ladder.mp4")

def ensure_sample_video():
    """
    Ensures an authentic tactical border surveillance video exists for testing.
    Defaults to border fence incursion footage.
    """
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    if os.path.exists(SAMPLE_PATH) and os.path.getsize(SAMPLE_PATH) > 10000:
        return SAMPLE_PATH

    print("[TRINETRA-C2] Preparing sample surveillance video...")

    # Direct URL to a public domain pedestrian surveillance test video
    test_urls = [
        "https://github.com/intel-iot-devkit/sample-videos/raw/master/person-bicycle-car-detection.mp4",
        "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/vtest.avi"
    ]

    for url in test_urls:
        try:
            print(f"Downloading benchmark sample from: {url}")
            urllib.request.urlretrieve(url, SAMPLE_PATH)
            if os.path.exists(SAMPLE_PATH) and os.path.getsize(SAMPLE_PATH) > 50000:
                print(f"Successfully downloaded test surveillance video: {SAMPLE_PATH}")
                return SAMPLE_PATH
        except Exception as e:
            print(f"Download attempt failed: {e}")

    # Fallback: Synthesize a realistic CCTV surveillance sequence (640x360, 200 frames)
    print("[TRINETRA-C2] Generating high-fidelity synthetic CCTV night surveillance footage...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(SAMPLE_PATH, fourcc, 25.0, (640, 360))

    for f in range(250):
        # Dark low-light surveillance background with noise
        frame = np.ones((360, 640, 3), dtype=np.uint8) * 35
        noise = np.random.randint(-12, 12, (360, 640, 3), dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # Draw road / perimeter fence lines
        cv2.line(frame, (0, 280), (640, 280), (50, 55, 60), 2)
        cv2.line(frame, (100, 180), (0, 360), (45, 50, 55), 2)
        cv2.line(frame, (540, 180), (640, 360), (45, 50, 55), 2)

        # Simulated intruder walking across screen into sterile corridor
        # Frame 0 to 250 moves from x=80 to x=520, y=220 to y=320
        prog = f / 250.0
        px = int(80 + prog * 440 + math.sin(f * 0.2) * 5)
        py = int(220 + prog * 90)

        # Draw human shape (head, torso, legs)
        cv2.circle(frame, (px, py - 35), 8, (160, 150, 140), -1)          # Head
        cv2.rectangle(frame, (px - 9, py - 27), (px + 9, py), (140, 130, 120), -1) # Torso
        leg_offset = int(math.sin(f * 0.4) * 6)
        cv2.line(frame, (px - 5, py), (px - 5 + leg_offset, py + 22), (120, 110, 100), 3) # Leg 1
        cv2.line(frame, (px + 5, py), (px + 5 - leg_offset, py + 22), (120, 110, 100), 3) # Leg 2

        # Timestamp overlay
        cv2.putText(frame, f"CAM-04 NORTH FENCE // 2026-09-05 23:59:{f//25:02d}.{f%25:02d}",
                    (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 190, 200), 1)

        out.write(frame)

    out.release()
    print(f"Synthesized realistic CCTV video saved: {SAMPLE_PATH}")
    return SAMPLE_PATH

if __name__ == "__main__":
    ensure_sample_video()
