import os
import time
import threading
from typing import Dict, List, Optional, Any
from core.geo_telemetry import GeoTelemetry

class GlobalCameraCatalog:
    """
    Project TRINETRA // Omniscient Global Camera Directory & Open Feeds Gateway
    Catalog of strategic terrestrial, maritime, border, and urban surveillance feeds.
    Provides geospatial metadata (Lat/Lng/MGRS), stream source resolution, and dynamic ingestion.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self.cameras: Dict[str, Dict[str, Any]] = {}
        self._init_default_catalog()

    def _init_default_catalog(self):
        initial_nodes = [
            {
                "id": "CAM-IND-01",
                "name": "SECTOR-01 // PUNJAB WAGAH BORDER",
                "codename": "TRINETRA-PUNJAB-MAST-01",
                "location": "Amritsar-Wagah Frontier Perimeter Wall",
                "country": "India",
                "region": "INDIA_FRONTIER",
                "lat": 31.604,
                "lng": 74.572,
                "type": "ELEVATED MAST CCTV // OPTICAL 4K",
                "source": "sample_footage/border_fence_ladder.mp4",
                "status": "ONLINE // ACTIVE SENTRY"
            },
            {
                "id": "CAM-IND-02",
                "name": "SECTOR-02 // THAR NIGHT SENTRY",
                "codename": "TRINETRA-RAJASTHAN-FLIR-02",
                "location": "Jaisalmer Frontier Sand Dune Sector",
                "country": "India",
                "region": "INDIA_FRONTIER",
                "lat": 27.023,
                "lng": 70.912,
                "type": "THERMAL RVSS // FORWARD FLIR",
                "source": "sample_footage/previews2/night_vision_1.mp4",
                "status": "ONLINE // STERILE CORRIDOR"
            },
            {
                "id": "CAM-IND-03",
                "name": "SECTOR-03 // HIGHWAY ANPR CORRIDOR",
                "codename": "TRINETRA-HIGHWAY-ANPR-03",
                "location": "Strategic Highway Transit Corridor",
                "country": "India",
                "region": "HIGHWAY_CORRIDOR",
                "lat": 32.610,
                "lng": 74.720,
                "type": "HIGHWAY HIGH-SPEED ANPR / SENTRY",
                "source": "sample_footage/sih_candidate_vids/parth_test.mp4",
                "status": "ONLINE // ANPR INTERDICTION"
            },
            {
                "id": "CAM-IND-04",
                "name": "SECTOR-04 // CHECKPOST SENTINEL",
                "codename": "TRINETRA-JAMMU-CHECKPOST-04",
                "location": "Border Checkpost Barricade Interdiction Axis",
                "country": "India",
                "region": "INDIA_FRONTIER",
                "lat": 32.726,
                "lng": 74.857,
                "type": "CHECKPOST TACTICAL SENTINEL // ANPR",
                "source": "sample_footage/previews2/checkpoint_1.mp4",
                "status": "ONLINE // ACTIVE INSPECTION"
            },
            {
                "id": "CAM-IND-05",
                "name": "MUMBAI NHAVA SHEVA // HARBOR SENTRY",
                "codename": "TRINETRA-MUMBAI-PORT-05",
                "location": "JNPT Maritime Container Terminal Outer Basin",
                "country": "India",
                "region": "COASTAL_PORT",
                "lat": 18.950,
                "lng": 72.950,
                "type": "COASTAL LONG-RANGE OPTICAL/THERMAL",
                "source": "sample_footage/border_patrol_surveillance.mp4",
                "status": "ONLINE // HARBOR DEFENSE"
            },
            {
                "id": "CAM-IND-06",
                "name": "DELHI NCR // OUTER RING ROAD JUNCTION",
                "codename": "TRINETRA-DELHI-HIGHWAY-06",
                "location": "GT Karnal Road High-Speed Commercial Transit",
                "country": "India",
                "region": "HIGHWAY_CORRIDOR",
                "lat": 28.704,
                "lng": 77.102,
                "type": "HIGHWAY MULTI-LANE ANPR",
                "source": "sample_footage/sih_candidate_vids/parth_test.mp4",
                "status": "ONLINE // TRAFFIC SURVEILLANCE"
            },
            {
                "id": "CAM-IND-07",
                "name": "KOLKATA HALDIA // RIVERINE PORT AXIS",
                "codename": "TRINETRA-BENGAL-RIVER-07",
                "location": "Hooghly Estuary Maritime Terminal",
                "country": "India",
                "region": "COASTAL_PORT",
                "lat": 22.025,
                "lng": 88.060,
                "type": "RIVERINE FLIR & OPTICAL SENTRY",
                "source": "sample_footage/previews2/border_patrol_2.mp4",
                "status": "ONLINE // ESTUARY PATROL"
            },
            {
                "id": "CAM-IND-08",
                "name": "SIKKIM NATHU LA // HIGH-ALTITUDE PASS",
                "codename": "TRINETRA-SIKKIM-PASS-08",
                "location": "Himalayan LAC Strategic Transit Ridge (4,310m)",
                "country": "India",
                "region": "INDIA_FRONTIER",
                "lat": 27.386,
                "lng": 88.831,
                "type": "RUGGEDIZED HIGH-ALTITUDE FLIR",
                "source": "sample_footage/previews2/night_vision_1.mp4",
                "status": "ONLINE // LAC SENTRY"
            },
            {
                "id": "CAM-GLO-01",
                "name": "TOKYO SHIBUYA // URBAN GRID SENTRY",
                "codename": "GLOBAL-TOKYO-GRID-01",
                "location": "Shibuya Pedestrian Scramble Intersection",
                "country": "Japan",
                "region": "GLOBAL",
                "lat": 35.659,
                "lng": 139.700,
                "type": "METROPOLITAN BIOMETRIC OPTICAL",
                "source": "sample_footage/vtest.avi",
                "status": "ONLINE // GLOBAL INTEL"
            },
            {
                "id": "CAM-GLO-02",
                "name": "NEW YORK TIMES SQUARE // BROADWAY GRID",
                "codename": "GLOBAL-NYC-TRANSIT-02",
                "location": "Midtown Manhattan Strategic Commercial Hub",
                "country": "United States",
                "region": "GLOBAL",
                "lat": 40.758,
                "lng": -73.985,
                "type": "URBAN PERIMETER MULTI-SPECTRAL",
                "source": "sample_footage/vtest.avi",
                "status": "ONLINE // GLOBAL INTEL"
            },
            {
                "id": "CAM-GLO-03",
                "name": "LONDON PICCADILLY // WESTMINSTER WATCH",
                "codename": "GLOBAL-LONDON-SENTRY-03",
                "location": "Shaftesbury Memorial Public Surveillance",
                "country": "United Kingdom",
                "region": "GLOBAL",
                "lat": 51.510,
                "lng": -0.134,
                "type": "URBAN TRAFFIC SENTRY // OPTICAL",
                "source": "sample_footage/sih_candidate_vids/parth_test.mp4",
                "status": "ONLINE // GLOBAL INTEL"
            },
            {
                "id": "CAM-GLO-04",
                "name": "PARIS CHAMPS-ÉLYSÉES // METRO AXIS",
                "codename": "GLOBAL-PARIS-SENTRY-04",
                "location": "Place Charles de Gaulle Arc Axis",
                "country": "France",
                "region": "GLOBAL",
                "lat": 48.873,
                "lng": 2.295,
                "type": "URBAN ANPR / BIOMETRIC OPTICAL",
                "source": "sample_footage/sih_candidate_vids/parth_test.mp4",
                "status": "ONLINE // INTERPOL SENTINEL"
            },
            {
                "id": "CAM-GLO-05",
                "name": "DUBAI MARINA // HIGHWAY INTERCEPT",
                "codename": "GLOBAL-DUBAI-AXIS-05",
                "location": "Sheikh Zayed Road High-Speed Corridor",
                "country": "United Arab Emirates",
                "region": "GLOBAL",
                "lat": 25.080,
                "lng": 55.140,
                "type": "HIGH-SPEED ANPR / OPTICAL SENTINEL",
                "source": "sample_footage/sih_candidate_vids/parth_test.mp4",
                "status": "ONLINE // TRANSIT WATCH"
            },
            {
                "id": "CAM-GLO-06",
                "name": "SINGAPORE MARINA BAY // PORT SENTRY",
                "codename": "GLOBAL-SINGAPORE-06",
                "location": "Straits Maritime Access & Transit Basin",
                "country": "Singapore",
                "region": "GLOBAL",
                "lat": 1.284,
                "lng": 103.861,
                "type": "PORT MARITIME / COASTAL FLIR",
                "source": "sample_footage/border_patrol_surveillance.mp4",
                "status": "ONLINE // STRAITS DEFENSE"
            }
        ]

        for node in initial_nodes:
            mgrs_str = GeoTelemetry.latlon_to_mgrs(node["lat"], node["lng"])
            node["mgrs"] = mgrs_str
            self.cameras[node["id"]] = node

    def get_all_cameras(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.cameras.values())

    def get_camera(self, cam_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.cameras.get(cam_id)

    def add_custom_camera(self, name: str, source: str, lat: float, lng: float,
                          cam_type: str = "CUSTOM RTSP / IP STREAM",
                          location: str = "Operator Registered Stream",
                          region: str = "CUSTOM") -> Dict[str, Any]:
        """Dynamically registers an operator custom stream URL (RTSP, HLS, phone IP webcam)."""
        with self._lock:
            cid = f"CAM-CUST-{len(self.cameras) + 1:02d}"
            mgrs_str = GeoTelemetry.latlon_to_mgrs(lat, lng)
            entry = {
                "id": cid,
                "name": name.upper(),
                "codename": f"TRINETRA-OPERATOR-{cid}",
                "location": location,
                "country": "India" if (8.0 <= lat <= 37.0 and 68.0 <= lng <= 97.0) else "International",
                "region": region,
                "lat": round(lat, 4),
                "lng": round(lng, 4),
                "mgrs": mgrs_str,
                "type": cam_type,
                "source": source,
                "status": "ONLINE // OPERATOR NODE"
            }
            self.cameras[cid] = entry
            print(f"[GLOBAL-CATALOG] Registered new camera {cid}: {name} ({source}) at {lat}°, {lng}°")
            return entry
