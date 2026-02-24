from dataclasses import dataclass
from typing import List
import math

from climbs import Point


@dataclass
class RawPoint:
    # GPS point from activity tracking
    t: float  # seconds since activity start/epoch (doesn't matter, just has to be monotonic)
    lat: float  # degrees
    lon: float  # degrees
    elev_m: float  # meters


def haversine_m(lat1_deg, lon1_deg, lat2_deg, lon2_deg):
    R = 6_371_000.0  # Earth radius in meters

    lat1 = math.radians(lat1_deg)
    lon1 = math.radians(lon1_deg)
    lat2 = math.radians(lat2_deg)
    lon2 = math.radians(lon2_deg)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def preprocess_raw_points(raw_points: List[RawPoint]) -> List[Point]:
    if not raw_points:
        return []

    raw = sorted(raw_points, key=lambda p: p.t)

    out: List[Point] = []
    cumulative_distance = 0.0

    prev = raw[0]
    out.append(Point(d=0.0, e=prev.elev_m))

    for cur in raw[1:]:
        if cur.t <= prev.t:
            continue

        dd = haversine_m(prev.lat, prev.lon, cur.lat, cur.lon)

        cumulative_distance += dd
        out.append(Point(d=cumulative_distance, e=cur.elev_m))
        prev = cur

    return out
