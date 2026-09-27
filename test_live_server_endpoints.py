import urllib.request
import json

base_url = "http://localhost:8080"

print("--- 1. Testing Telemetry & FARR ---")
with urllib.request.urlopen(f"{base_url}/api/telemetry") as r:
    telem = json.loads(r.read().decode())
    print(f"FPS: {telem['fps']} | Latency: {telem['latency_ms']}ms | FARR: {telem['farr']['farr_percentage']}% | Telegram Status: {telem['alerts_config']['telegram_bot_token_masked']}")

print("\n--- 2. Testing Alert Test Dispatch ---")
req = urllib.request.Request(f"{base_url}/api/alerts/test", data=b"{}", headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as r:
    res = json.loads(r.read().decode())
    print(f"Alert Dispatch: {res['message']}")

print("\n--- 3. Testing Dynamic Camera Onboarding ---")
cam_payload = {
    "name": "TEST SECTOR 8 NORTH CORRIDOR",
    "source": "rtsp://admin:pass@192.168.1.80:554/ch1",
    "cam_type": "THERMAL RVSS // FORWARD FLIR",
    "mgrs": "43R EQ 8888 2222"
}
req = urllib.request.Request(f"{base_url}/api/cameras/add_custom", data=json.dumps(cam_payload).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as r:
    add_res = json.loads(r.read().decode())
    new_cam_id = add_res["camera"]["id"]
    print(f"Added Camera ID: {new_cam_id} | Name: {add_res['camera']['name']} | Protocol: {add_res['camera']['protocol']}")

print("\n--- 4. Testing Camera List ---")
with urllib.request.urlopen(f"{base_url}/api/cameras/list") as r:
    cams = json.loads(r.read().decode())
    print(f"Total Provisioned Cameras: {len(cams)}")

print("\n--- 5. Testing Camera Deletion ---")
req = urllib.request.Request(f"{base_url}/api/cameras/delete/{new_cam_id}", data=b"{}", headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as r:
    del_res = json.loads(r.read().decode())
    print(f"Delete Result: {del_res['message']}")

print("\n*** ALL LIVE REST INTEGRATION TESTS PASSED WITH 100% SUCCESS! ***")
