import cv2
from core.detector import TacticalDetector

det = TacticalDetector()
cap = cv2.VideoCapture('sample_footage/furious7_god_eye.mp4')
cap.set(cv2.CAP_PROP_POS_FRAMES, int(24 * 67))
ret, frame = cap.read()
if ret:
    proc, dets, lat = det.detect(frame)
    print(f'Detections at 67s: {len(dets)} targets found!')
    for d in dets:
        print(f"  - {d['class_name']} ({d['confidence']*100:.1f}%) at {d['bbox']}")
cap.release()
