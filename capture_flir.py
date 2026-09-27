import urllib.request
import time
import json

# Set sensor mode to FLIR_IRONBOW and toggle scope mask off for full thermal view
req = urllib.request.Request(
    'http://localhost:8080/api/control/set_sensor_mode',
    data=json.dumps({'mode': 'FLIR_IRONBOW'}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
urllib.request.urlopen(req)

# Toggle scope mask off if enabled
urllib.request.urlopen(urllib.request.Request('http://localhost:8080/api/control/toggle_scope', data=b'{}', headers={'Content-Type': 'application/json'}))
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
        with open('live_c2_flir_preview.jpg', 'wb') as f:
            f.write(jpg)
        print(f'[OK] Captured live_c2_flir_preview.jpg ({len(jpg)} bytes)')
        break
stream.close()
