import os
import math
import time
import json
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from core.geo_telemetry import GeoTelemetry

class InterdictionDispatchEngine:
    """
    Project TRINETRA // Autonomous Quick Reaction Team (QRT) Interdiction & Handoff Engine
    Calculates kinematic intercept vectors, projects hostile trajectory onto geospatial grid,
    determines nearest tactical QRT unit, and seals dispatch warrants with Section 65B SHA-256 hashes.
    """
    def __init__(self, orders_file: str = "evidence/interdiction_orders.json"):
        self.orders_file = orders_file
        os.makedirs(os.path.dirname(self.orders_file), exist_ok=True)
        
        # Tactical QRT Patrol Stations across operational sectors
        self.qrt_units: Dict[str, Dict[str, Any]] = {
            "QRT-EAGLE-01": {
                "callsign": "EAGLE-01",
                "unit_name": "17th BSF Frontier Battalion QRT",
                "sector": "PUNJAB WAGAH BORDER",
                "base_lat": 31.6150,
                "base_lng": 74.5850,
                "status": "READY // RAPID RESPONSE",
                "vehicle": "Armored Quick Reaction Light Vehicle (QRF-ALV)",
                "speed_kmh": 65.0,
                "personnel": 6,
                "comms_freq": "142.850 MHz SECURE VHF"
            },
            "QRT-COBRA-02": {
                "callsign": "COBRA-02",
                "unit_name": "Thar Desert Mobile Intercept Unit",
                "sector": "RAJASTHAN THAR SECTOR",
                "base_lat": 27.0400,
                "base_lng": 70.9300,
                "status": "READY // MOBILE PATROL",
                "vehicle": "Sand Strike Dune Interceptor",
                "speed_kmh": 50.0,
                "personnel": 4,
                "comms_freq": "143.125 MHz TACTICAL"
            },
            "QRT-TIGER-03": {
                "callsign": "TIGER-03",
                "unit_name": "Jammu Frontier Strike Sentinel",
                "sector": "JAMMU RS PURA AXIS",
                "base_lat": 32.6200,
                "base_lng": 74.7350,
                "status": "READY // RAPID RESPONSE",
                "vehicle": "Armored Tactical Scout (ATS)",
                "speed_kmh": 60.0,
                "personnel": 6,
                "comms_freq": "141.900 MHz SECURE VHF"
            },
            "QRT-CHETAK-04": {
                "callsign": "CHETAK-04",
                "unit_name": "Mumbai Port Tactical Coastal Defense",
                "sector": "MUMBAI NHAVA SHEVA",
                "base_lat": 18.9400,
                "base_lng": 72.9300,
                "status": "READY // MARITIME STANDBY",
                "vehicle": "Fast Interceptor Craft (FIC-40)",
                "speed_kmh": 74.0,  # ~40 knots
                "personnel": 8,
                "comms_freq": "156.800 MHz MARINE CH16"
            },
            "QRT-FALCON-05": {
                "callsign": "FALCON-05",
                "unit_name": "Delhi NCR Tactical Intercept Squad",
                "sector": "DELHI NCR HIGHWAY",
                "base_lat": 28.7150,
                "base_lng": 77.1200,
                "status": "READY // HIGHWAY INTERCEPT",
                "vehicle": "High-Speed Tactical Pursuit SUV",
                "speed_kmh": 85.0,
                "personnel": 4,
                "comms_freq": "144.200 MHz POLICE NET"
            }
        }
        
        self.active_intercept: Optional[Dict[str, Any]] = None
        self.dispatch_history: List[Dict[str, Any]] = self._load_orders()

    def _load_orders(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.orders_file):
            try:
                with open(self.orders_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[INTERDICTION] Error loading orders ledger: {e}")
                return []
        return []

    def _save_orders(self):
        try:
            with open(self.orders_file, "w", encoding="utf-8") as f:
                json.dump(self.dispatch_history, f, indent=2)
        except Exception as e:
            print(f"[INTERDICTION] Error saving orders ledger: {e}")

    @staticmethod
    def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculates exact great-circle distance between two GPS coordinates in km."""
        r = 6371.0  # Earth radius in km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

    def find_nearest_qrt(self, target_lat: float, target_lng: float) -> Tuple[str, Dict[str, Any], float]:
        """Finds nearest QRT station to target coordinates."""
        nearest_uid = "QRT-EAGLE-01"
        min_dist = float("inf")
        
        for uid, unit in self.qrt_units.items():
            dist = self.haversine_distance_km(target_lat, target_lng, unit["base_lat"], unit["base_lng"])
            if dist < min_dist:
                min_dist = dist
                nearest_uid = uid
                
        return nearest_uid, self.qrt_units[nearest_uid], round(min_dist, 2)

    def calculate_intercept_vector(self, current_lat: float, current_lng: float,
                                   heading_deg: float, speed_mps: float,
                                   eta_seconds: float = 45.0) -> Dict[str, Any]:
        """
        Extrapolates target trajectory vector forward onto geospatial sphere.
        Calculates projected boundary breach coordinates and MGRS grid.
        """
        speed_mps = max(0.5, speed_mps)
        eta_seconds = max(5.0, min(120.0, eta_seconds))
        
        dist_traveled_meters = speed_mps * eta_seconds
        heading_rad = math.radians(heading_deg)
        
        # Projected displacement in meters
        dx_meters = dist_traveled_meters * math.sin(heading_rad)
        dy_meters = dist_traveled_meters * math.cos(heading_rad)
        
        # Approx spherical degrees displacement
        d_lat = dy_meters / 111320.0
        lat_rad = math.radians(current_lat)
        meters_per_lng_deg = max(1000.0, 111320.0 * math.cos(lat_rad))
        d_lng = dx_meters / meters_per_lng_deg
        
        intercept_lat = round(current_lat + d_lat, 5)
        intercept_lng = round(current_lng + d_lng, 5)
        intercept_mgrs = GeoTelemetry.latlon_to_mgrs(intercept_lat, intercept_lng)
        
        return {
            "origin_lat": current_lat,
            "origin_lng": current_lng,
            "heading_deg": round(heading_deg, 1),
            "speed_mps": round(speed_mps, 1),
            "speed_kmh": round(speed_mps * 3.6, 1),
            "time_to_intercept_sec": round(eta_seconds, 1),
            "intercept_lat": intercept_lat,
            "intercept_lng": intercept_lng,
            "intercept_mgrs": intercept_mgrs,
            "distance_m": round(dist_traveled_meters, 1)
        }

    def update_realtime_kinematics(self, sector_info: Dict[str, Any],
                                   primary_target: Optional[Dict[str, Any]] = None,
                                   breach_count: int = 0) -> Optional[Dict[str, Any]]:
        """
        Periodically called during sensor pipeline loop.
        Updates active intercept tracking state with live kinematics.
        """
        if not primary_target and breach_count == 0:
            self.active_intercept = None
            return None
            
        cur_lat = sector_info.get("lat", 31.604)
        cur_lng = sector_info.get("lng", 74.572)
        
        # Extract kinematics from detection
        kin = primary_target.get("kinematics", {}) if primary_target else {}
        vx, vy = kin.get("velocity", (2.5, 1.2))
        speed_px = kin.get("speed", math.hypot(vx, vy))
        heading_deg = kin.get("heading_deg", 45.0)
        
        # Scaling: pixel speed to approximate real-world m/s
        speed_mps = max(1.2, speed_px * 0.08)
        eta_sec = kin.get("breach_eta_s") or 35.0
        
        vector = self.calculate_intercept_vector(cur_lat, cur_lng, heading_deg, speed_mps, eta_sec)
        qrt_id, qrt_info, dist_km = self.find_nearest_qrt(vector["intercept_lat"], vector["intercept_lng"])
        
        qrt_travel_time_sec = (dist_km / qrt_info["speed_kmh"]) * 3600.0
        
        state = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_id": primary_target.get("global_id", "G-01") if primary_target else "UNID-INTRUDER",
            "target_class": primary_target.get("class_name", "PERSON") if primary_target else "INTRUDER",
            "confidence": primary_target.get("confidence", 0.92) if primary_target else 0.90,
            "sector_name": sector_info.get("name", "SECTOR-01"),
            "current_mgrs": sector_info.get("mgrs", GeoTelemetry.latlon_to_mgrs(cur_lat, cur_lng)),
            "vector": vector,
            "assigned_qrt": {
                "id": qrt_id,
                "callsign": qrt_info["callsign"],
                "unit_name": qrt_info["unit_name"],
                "vehicle": qrt_info["vehicle"],
                "comms_freq": qrt_info["comms_freq"],
                "distance_to_intercept_km": dist_km,
                "eta_seconds": round(qrt_travel_time_sec, 1)
            },
            "countdown_seconds": round(vector["time_to_intercept_sec"], 1),
            "threat_level": "CRITICAL INVASION BREACH" if breach_count > 0 else "HOSTILE APPROACH VECTOR"
        }
        self.active_intercept = state
        return state

    def generate_dispatch_order(self, target_intel: Dict[str, Any],
                                sector_info: Dict[str, Any],
                                operator_callsign: str = "C2-COMMANDER") -> Dict[str, Any]:
        """
        Executes formal QRT Dispatch Order.
        Generates Section 65B Indian Evidence Act SHA-256 digital cryptographic hash seal.
        """
        order_uuid = f"QRT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        now_utc = datetime.now(timezone.utc)
        ist_time = now_utc + timedelta(hours=5, minutes=30)
        
        cur_lat = sector_info.get("lat", 31.604)
        cur_lng = sector_info.get("lng", 74.572)
        
        heading_deg = target_intel.get("heading_deg", 45.0)
        speed_mps = target_intel.get("speed_mps", 3.2)
        eta_sec = target_intel.get("eta_sec", 38.0)
        
        vector = self.calculate_intercept_vector(cur_lat, cur_lng, heading_deg, speed_mps, eta_sec)
        qrt_id, qrt_info, dist_km = self.find_nearest_qrt(vector["intercept_lat"], vector["intercept_lng"])
        qrt_travel_sec = (dist_km / qrt_info["speed_kmh"]) * 3600.0
        
        # Build canonical payload for hashing
        payload_to_hash = {
            "order_uuid": order_uuid,
            "timestamp_utc": now_utc.isoformat(),
            "timestamp_ist": ist_time.strftime("%d-%b-%Y %H:%M:%S IST"),
            "sector": sector_info.get("name"),
            "origin_mgrs": sector_info.get("mgrs"),
            "intercept_coordinates": {
                "lat": vector["intercept_lat"],
                "lng": vector["intercept_lng"],
                "mgrs": vector["intercept_mgrs"]
            },
            "target": {
                "id": target_intel.get("id", "G-01"),
                "classification": target_intel.get("class_name", "PERSON"),
                "bearing_deg": vector["heading_deg"],
                "speed_kmh": vector["speed_kmh"],
                "breach_eta_sec": vector["time_to_intercept_sec"]
            },
            "assigned_unit": {
                "unit_id": qrt_id,
                "callsign": qrt_info["callsign"],
                "unit_name": qrt_info["unit_name"],
                "vehicle": qrt_info["vehicle"],
                "comms": qrt_info["comms_freq"],
                "distance_km": dist_km,
                "eta_sec": round(qrt_travel_sec, 1)
            },
            "authorizing_officer": operator_callsign,
            "statute": "SECTION 65B INDIAN EVIDENCE ACT // BORDER DEFENSE ACT 2026"
        }
        
        canonical_bytes = json.dumps(payload_to_hash, sort_keys=True).encode("utf-8")
        sec65b_hash = hashlib.sha256(canonical_bytes).hexdigest().upper()
        
        ticket = dict(payload_to_hash)
        ticket["sec65b_hash"] = sec65b_hash
        ticket["status"] = "DISPATCH ORDER TRANSMITTED // INTERCEPTION IN PROGRESS"
        
        # Record into persistent audit log
        self.dispatch_history.insert(0, ticket)
        if len(self.dispatch_history) > 100:
            self.dispatch_history = self.dispatch_history[:100]
        self._save_orders()
        
        print(f"[INTERDICTION] DISPATCH ORDER ISSUED: {order_uuid} -> {qrt_info['callsign']} (HASH: {sec65b_hash[:16]}...)")
        return ticket

    def generate_ticket_html(self, order_uuid: str) -> str:
        """Renders printable, cryptographic legal warrant for field interdiction."""
        ticket = next((t for t in self.dispatch_history if t.get("order_uuid") == order_uuid), None)
        if not ticket:
            return f"<h3>ERROR: Dispatch Warrant {order_uuid} not found in evidence vault.</h3>"
            
        t = ticket
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QRT TACTICAL INTERDICTION WARRANT // {t['order_uuid']}</title>
<style>
  body {{ background: #070a0e; color: #d0d8e0; font-family: 'Courier New', monospace; margin: 0; padding: 30px; }}
  .warrant-card {{ max-width: 820px; margin: 0 auto; background: #0c1118; border: 2px solid #00f0ff; box-shadow: 0 0 30px rgba(0,240,255,0.2); padding: 30px; position: relative; }}
  .header {{ text-align: center; border-bottom: 2px solid #00f0ff; padding-bottom: 15px; margin-bottom: 20px; }}
  .header h1 {{ margin: 0; color: #00f0ff; font-size: 20px; letter-spacing: 2px; }}
  .header p {{ margin: 5px 0 0 0; color: #8899a6; font-size: 11px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }}
  .section {{ background: #070a0e; border: 1px solid #1a2533; padding: 12px; }}
  .label {{ color: #00f0ff; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
  .val {{ font-size: 13px; font-weight: bold; color: #ffffff; }}
  .val-highlight {{ color: #ff3344; font-size: 15px; }}
  .seal-box {{ border: 2px dashed #00ff77; padding: 15px; text-align: center; margin-top: 20px; background: rgba(0,255,119,0.03); }}
  .hash {{ word-break: break-all; font-size: 11px; color: #00ff77; letter-spacing: 1px; margin-top: 6px; }}
  .footer {{ margin-top: 25px; text-align: center; font-size: 10px; color: #556677; }}
  .print-btn {{ display: block; width: 100%; margin-top: 20px; background: #00f0ff; color: #000; padding: 10px; font-weight: bold; border: none; cursor: pointer; text-transform: uppercase; }}
  @media print {{ .print-btn {{ display: none; }} body {{ background: #fff; color: #000; }} .warrant-card {{ border: 1px solid #000; box-shadow: none; background: #fff; }} }}
</style>
</head>
<body>
<div class="warrant-card">
  <div class="header">
    <h1>PROJECT TRINETRA // BORDER DEFENSE C2</h1>
    <p>AUTONOMOUS QUICK REACTION TEAM (QRT) INTERDICTION DISPATCH ORDER</p>
    <p>Statutory Compliance: Section 65B, Indian Evidence Act, 1872</p>
  </div>
  
  <div class="grid">
    <div class="section">
      <div class="label">DISPATCH ORDER UUID</div>
      <div class="val">{t['order_uuid']}</div>
    </div>
    <div class="section">
      <div class="label">TIME ISSUED (IST)</div>
      <div class="val">{t['timestamp_ist']}</div>
    </div>
    <div class="section">
      <div class="label">ASSIGNED QRT UNIT</div>
      <div class="val" style="color:#00ff77;">{t['assigned_unit']['callsign']} // {t['assigned_unit']['unit_name']}</div>
      <div style="font-size:10px;color:#8899a6;margin-top:2px;">VEHICLE: {t['assigned_unit']['vehicle']} | FREQ: {t['assigned_unit']['comms']}</div>
    </div>
    <div class="section">
      <div class="label">ESTIMATED TIME TO INTERCEPT</div>
      <div class="val val-highlight">{t['target']['breach_eta_sec']} SECONDS ({t['assigned_unit']['distance_km']} km away)</div>
    </div>
  </div>

  <div class="section" style="margin-bottom: 20px;">
    <div class="label">PREDICTED INTERCEPT COORDINATES & KINEMATIC VECTOR</div>
    <div class="val" style="color:#00f0ff; font-size:14px;">
      MGRS: {t['intercept_coordinates']['mgrs']} &nbsp;|&nbsp; LAT: {t['intercept_coordinates']['lat']}° N &nbsp;|&nbsp; LNG: {t['intercept_coordinates']['lng']}° E
    </div>
    <div style="font-size:11px; color:#a0b0c0; margin-top:6px;">
      TARGET BEARING: {t['target']['bearing_deg']}° &nbsp;|&nbsp; VELOCITY: {t['target']['speed_kmh']} km/h &nbsp;|&nbsp; TARGET ID: {t['target']['id']} ({t['target']['classification']})
    </div>
  </div>

  <div class="seal-box">
    <div style="font-size:11px; color:#8899a6; letter-spacing:1px;">SECTION 65B DIGITAL CRYPTOGRAPHIC AUDIT SEAL</div>
    <div class="hash">{t['sec65b_hash']}</div>
    <div style="font-size:10px; color:#556677; margin-top:4px;">ALGORITHM: SHA-256 // TAMPER-EVIDENT FORENSIC SIGNATURE</div>
  </div>

  <button class="print-btn" onclick="window.print()">PRINT / EXPORT OFFICIAL INTERDICTION ORDER</button>
  <div class="footer">CONFIDENTIAL // MINISTRY OF HOME AFFAIRS (MHA) LAW ENFORCEMENT & DEFENSE ONLY</div>
</div>
</body>
</html>
"""
        return html
