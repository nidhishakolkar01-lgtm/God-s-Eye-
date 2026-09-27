import urllib.request
import json
import time

base = 'http://localhost:8080'
for attempt in range(12):
    try:
        req = urllib.request.urlopen(f'{base}/api/telemetry', timeout=2)
        print(f'[TEST] Server responded on attempt {attempt+1}')
        break
    except Exception as e:
        time.sleep(1)
else:
    print('[TEST] Could not connect to server')
    exit(1)

# 1. Telemetry
res = urllib.request.urlopen(f'{base}/api/telemetry').read().decode('utf-8')
telem = json.loads(res)
print(f"[TEST 1] Telemetry OK | Global Cams: {telem.get('global_cams_count')} | STSI: {telem.get('stsi')}")

# 2. Global Cameras List
res = urllib.request.urlopen(f'{base}/api/cameras/global/list').read().decode('utf-8')
gcams = json.loads(res)
print(f"[TEST 2] Global Cameras List OK | Total: {gcams.get('total')} cameras across strategic nodes")
for c in gcams.get('cameras', [])[:4]:
    print(f"  - {c['id']}: {c['name']} ({c['region']}) @ {c['lat']}, {c['lng']} [MGRS: {c['mgrs']}]")

# 3. Interdiction Status
res = urllib.request.urlopen(f'{base}/api/interdiction/status').read().decode('utf-8')
istatus = json.loads(res)
print(f"[TEST 3] Interdiction Status OK | QRT Units: {len(istatus.get('qrt_units', []))}")
for q in istatus.get('qrt_units', [])[:3]:
    print(f"  - {q['callsign']}: {q['unit_name']} ({q['vehicle']})")

# 4. Dispatch QRT Order
req_data = json.dumps({'operator_callsign': 'COMMANDER-ALPHA'}).encode('utf-8')
req = urllib.request.Request(f'{base}/api/interdiction/dispatch', data=req_data, headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req).read().decode('utf-8')
order_resp = json.loads(res)
order = order_resp.get('order', {})
print(f"[TEST 4] Dispatch Order OK | UUID: {order.get('order_uuid')} | Unit: {order.get('assigned_unit', {}).get('callsign')} | SHA256: {order.get('sec65b_hash')[:16]}...")

# 5. Orders Ledger
res = urllib.request.urlopen(f'{base}/api/interdiction/orders').read().decode('utf-8')
orders = json.loads(res)
print(f"[TEST 5] Orders Ledger OK | Total Orders: {orders.get('count')}")

# 6. Global Camera Assign to Slot 2
req_data = json.dumps({'slot_id': 2, 'camera_id': 'CAM-IND-04'}).encode('utf-8')
req = urllib.request.Request(f'{base}/api/cameras/global/assign', data=req_data, headers={'Content-Type': 'application/json'})
res = urllib.request.urlopen(req).read().decode('utf-8')
assign_resp = json.loads(res)
print(f"[TEST 6] Camera Assign OK | Slot #{assign_resp.get('slot_id')} -> {assign_resp.get('assigned', {}).get('name')}")

# 7. Warrant Certificate HTML
warrant_html = urllib.request.urlopen(f"{base}/api/interdiction/ticket/{order.get('order_uuid')}").read().decode('utf-8')
print(f"[TEST 7] Warrant Certificate HTML OK | Length: {len(warrant_html)} bytes")

print('\n*** ALL 7 TACTICAL VERIFICATION TESTS PASSED WITH 100% SUCCESS ***')
