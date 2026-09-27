import math
import time
from collections import deque
from typing import Dict, List, Tuple, Optional
import numpy as np

class KinematicTracker:
    """
    Tactical Kinematic Analytics Core.
    Calculates velocity vectors, movement speed, heading direction,
    and projected Time-to-Breach (ETA) for tracked targets relative to the sterile zone perimeter.
    """
    def __init__(self, history_len: int = 12):
        self.history_len = history_len
        self.tracks: Dict[int, deque] = {}
        self.velocities: Dict[int, Tuple[float, float]] = {}

    def update(self, track_id: Optional[int], centroid: Tuple[int, int], fence_coords: Optional[List[Tuple[int, int]]] = None) -> Dict:
        """
        Updates kinematic state for a detection.
        Returns kinematic metrics including velocity vector, speed, heading, and breach ETA.
        """
        now = time.time()
        if track_id is None:
            return {
                "velocity": (0.0, 0.0),
                "speed": 0.0,
                "heading_deg": 0.0,
                "dist_to_fence_px": None,
                "breach_eta_s": None,
                "is_imminent": False
            }

        if track_id not in self.tracks:
            self.tracks[track_id] = deque(maxlen=self.history_len)

        self.tracks[track_id].append((now, centroid))
        hist = self.tracks[track_id]

        # Calculate velocity over temporal baseline (requires at least 2 points)
        vx, vy = 0.0, 0.0
        if len(hist) >= 2:
            t_old, pt_old = hist[0]
            dt = now - t_old
            if dt > 0.02:
                dx = centroid[0] - pt_old[0]
                dy = centroid[1] - pt_old[1]
                raw_vx = dx / dt
                raw_vy = dy / dt
                prev_vx, prev_vy = self.velocities.get(track_id, (raw_vx, raw_vy))
                vx = 0.65 * raw_vx + 0.35 * prev_vx
                vy = 0.65 * raw_vy + 0.35 * prev_vy
                self.velocities[track_id] = (vx, vy)

        speed = math.hypot(vx, vy)
        heading_deg = (math.degrees(math.atan2(vy, vx)) + 360.0) % 360.0 if speed > 2.0 else 0.0

        # Distance to perimeter fence & ETA calculation
        dist_to_fence = None
        breach_eta = None
        is_imminent = False

        if fence_coords and len(fence_coords) >= 2:
            min_dist = float("inf")
            target_segment = None
            cx, cy = centroid

            for i in range(len(fence_coords)):
                p1 = fence_coords[i]
                p2 = fence_coords[(i + 1) % len(fence_coords)]
                d = self._dist_point_to_segment((cx, cy), p1, p2)
                if d < min_dist:
                    min_dist = d
                    target_segment = (p1, p2)

            dist_to_fence = min_dist

            # Projected time to reach fence
            if target_segment and speed > 5.0:
                p1, p2 = target_segment
                seg_dx = p2[0] - p1[0]
                seg_dy = p2[1] - p1[1]
                seg_len = math.hypot(seg_dx, seg_dy)
                if seg_len > 1e-4:
                    nx = -seg_dy / seg_len
                    ny = seg_dx / seg_len

                    v_proj = vx * nx + vy * ny
                    if abs(v_proj) > 2.0:
                        eta_calc = min_dist / abs(v_proj)
                        if 0.1 <= eta_calc <= 45.0:
                            breach_eta = round(eta_calc, 1)
                            if breach_eta < 6.0:
                                is_imminent = True

        return {
            "velocity": (round(vx, 1), round(vy, 1)),
            "speed": round(speed, 1),
            "heading_deg": round(heading_deg, 1),
            "dist_to_fence_px": round(dist_to_fence, 1) if dist_to_fence is not None else None,
            "breach_eta_s": breach_eta,
            "is_imminent": is_imminent
        }

    def prune_old_tracks(self, active_track_ids: List[int]):
        active_set = set(active_track_ids)
        to_del = [tid for tid in self.tracks if tid not in active_set]
        for tid in to_del:
            self.tracks.pop(tid, None)
            self.velocities.pop(tid, None)

    def _dist_point_to_segment(self, p, p1, p2):
        px, py = p
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1
        l2 = dx * dx + dy * dy
        if l2 == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / l2))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(px - proj_x, py - proj_y)
