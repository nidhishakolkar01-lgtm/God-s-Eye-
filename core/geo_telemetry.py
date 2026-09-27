import math
import time
from typing import Dict, Tuple

class GeoTelemetry:
    """
    Military Geospatial Telemetry & Reconnaissance Math Engine.
    Computes:
      - WGS84 to Military Grid Reference System (MGRS)
      - Ground Sampling Distance (GSD) in cm/pixel
      - National Imagery Interpretability Rating Scale (NIIRS)
      - Sensor Azimuth, Elevation, and Sun Declination angles
    """

    @staticmethod
    def latlon_to_utm(lat: float, lon: float) -> Tuple[int, str, float, float]:
        """Converts WGS84 latitude/longitude to UTM zone, band, easting, northing."""
        zone = int((lon + 180) / 6) + 1
        
        # Latitude band letter
        bands = "CDEFGHJKLMNPQRSTUVWX"
        lat_idx = int((lat + 80) / 8)
        lat_idx = max(0, min(len(bands) - 1, lat_idx))
        band = bands[lat_idx]

        # Standard Transverse Mercator Projection approximation (WGS84 ellipsoid)
        a = 6378137.0          # semi-major axis
        f = 1 / 298.257223563   # flattening
        k0 = 0.9996            # scale factor
        
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        lon0_rad = math.radians((zone - 1) * 6 - 180 + 3)

        e2 = 2 * f - f * f
        e_prime2 = e2 / (1 - e2)

        N = a / math.sqrt(1 - e2 * math.sin(lat_rad)**2)
        T = math.tan(lat_rad)**2
        C = e_prime2 * math.cos(lat_rad)**2
        A = (lon_rad - lon0_rad) * math.cos(lat_rad)

        M = a * ((1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * lat_rad
                 - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * math.sin(2 * lat_rad)
                 + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * math.sin(4 * lat_rad)
                 - (35 * e2**3 / 3072) * math.sin(6 * lat_rad))

        easting = k0 * N * (A + (1 - T + C) * A**3 / 6 + (5 - 18 * T + T**2 + 72 * C - 58 * e_prime2) * A**5 / 120) + 500000.0
        northing = k0 * (M + N * math.tan(lat_rad) * (A**2 / 2 + (5 - T + 9 * C + 4 * C**2) * A**4 / 24 + (61 - 58 * T + T**2 + 600 * C - 330 * e_prime2) * A**6 / 720))
        if lat < 0:
            northing += 10000000.0

        return zone, band, easting, northing

    @staticmethod
    def latlon_to_mgrs(lat: float, lon: float, precision: int = 4) -> str:
        """
        Converts WGS84 GPS coordinate to authentic MGRS (Military Grid Reference System) string.
        Format: [Zone][Band] [100k ID] [Easting] [Northing]
        Example: '43R FN 2891 7412'
        """
        zone, band, easting, northing = GeoTelemetry.latlon_to_utm(lat, lon)
        
        # 100km Column and Row Identification Letters
        col_letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        row_letters = "ABCDEFGHJKLMNPQRSTUV"

        col_idx = int(easting / 100000) % 24
        row_idx = int(northing / 100000) % 20

        sq_col = col_letters[col_idx]
        sq_row = row_letters[row_idx]
        sq_id = f"{sq_col}{sq_row}"

        rem_easting = int(easting % 100000)
        rem_northing = int(northing % 100000)

        # Quantize to specified precision (default 4 digits = 10m precision)
        scale = 10 ** (5 - precision)
        e_str = f"{int(rem_easting / scale):0{precision}d}"
        n_str = f"{int(rem_northing / scale):0{precision}d}"

        return f"{zone}{band} {sq_id} {e_str} {n_str}"

    @staticmethod
    def compute_recon_metrics(mast_height_m: float = 18.0, sensor_hfov_deg: float = 48.0, frame_width_px: int = 1280) -> Dict:
        """
        Computes Ground Sampling Distance (GSD), NIIRS rating, and sensor angles.
        """
        # Ground distance coverage at 50m standoff
        standoff_m = 50.0
        slant_range_m = math.hypot(standoff_m, mast_height_m)
        depression_angle_deg = math.degrees(math.atan2(mast_height_m, standoff_m))

        # Ground FOV
        ground_width_m = 2.0 * standoff_m * math.tan(math.radians(sensor_hfov_deg / 2.0))
        gsd_m = ground_width_m / frame_width_px
        gsd_cm = gsd_m * 100.0

        # NIIRS (National Imagery Interpretability Rating Scale)
        # NIIRS = 10.251 - 3.32 * log10(GSD_inches)
        gsd_inches = gsd_cm / 2.54
        raw_niirs = 10.251 - 3.32 * math.log10(max(gsd_inches, 0.1))
        niirs = max(1.0, min(9.0, round(raw_niirs, 1)))

        # Solar azimuth approximation based on UTC time
        utc_hour = (time.gmtime().tm_hour + time.gmtime().tm_min / 60.0)
        sun_azimuth = round((utc_hour * 15.0 + 90.0) % 360.0, 1)

        return {
            "gsd_cm_px": round(gsd_cm, 2),
            "niirs_rating": f"NIIRS-{int(niirs)}",
            "depression_angle_deg": round(depression_angle_deg, 1),
            "slant_range_m": round(slant_range_m, 1),
            "sun_azimuth_deg": sun_azimuth,
            "security_classification": "RESTRICTED // LAW ENFORCEMENT SENSITIVE // MHA BORDER SENTRY"
        }
