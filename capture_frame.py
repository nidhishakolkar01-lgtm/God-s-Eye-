import urllib.request
import time
import json

# Set sensor mode to NVG_P43
req = urllib.request.Request(
    'http://localhost:8080/api/control/set_sensor_mode',
    data=json.dumps({'mode': 'NVG_P43'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
urllib.request.urlopen(req)
time.sleep(1.0)

# Fetch MJPEG stream frame
stream = urllib.request.urlopen('http://localhost:8080/api/stream', timeout=5)
data = b''
for _ in range(60):
    chunk = stream.read(4096)
    data += chunk
    a = data.find(b'\xff\xd8')
    b = data.find(b'\xff\xd9')
    if a != -1 and b != -1 and b > a:
        jpg = data[a:b+2]
        with open('live_c2_upgraded_preview.jpg', 'wb') as f:
            f.write(jpg)
        print(f'[OK] Captured live_c2_upgraded_preview.jpg ({len(jpg)} bytes)')
        break
stream.close()
