import urllib.request
import time
import json

# Switch to Sector 5 (God's Eye)
req = urllib.request.Request(
    'http://localhost:8080/api/control/switch_sector',
    data=json.dumps({'sector': 5}).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)
urllib.request.urlopen(req)
time.sleep(1.5)

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
        with open('live_furious7_godeye_preview.jpg', 'wb') as f:
            f.write(jpg)
        print(f'[OK] Captured live_furious7_godeye_preview.jpg ({len(jpg)} bytes)')
        break
stream.close()
