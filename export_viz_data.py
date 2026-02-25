#!/usr/bin/env python3
"""Export all rides as JSON for the visualizer."""

import glob
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from geo import RawPoint, haversine_m, preprocess_raw_points
from climbs import detect_climbs


def export_ride(name, raw_points):
    points = preprocess_raw_points(raw_points)
    climbs = detect_climbs(points)

    # Build point list with lat/lon from raw and d/e from processed.
    # raw may have duplicates filtered by preprocess, so we rebuild
    # the lat/lon mapping by walking raw in timestamp order.
    raw_sorted = sorted(raw_points, key=lambda p: p.t)
    pts = []
    cum_d = 0.0
    prev = raw_sorted[0]
    pts.append(dict(lat=prev.lat, lon=prev.lon, elev=prev.elev_m, d=0.0))

    for cur in raw_sorted[1:]:
        if cur.t <= prev.t:
            continue
        cum_d += haversine_m(prev.lat, prev.lon, cur.lat, cur.lon)
        pts.append(dict(lat=cur.lat, lon=cur.lon, elev=cur.elev_m, d=cum_d))
        prev = cur

    climb_data = [
        dict(
            start_idx=c.start,
            end_idx=c.end,
            dist_m=round(c.dist_m, 1),
            gain_m=round(c.gain_m, 1),
            avg_grade=round(c.avg_grade, 4),
            category=c.category,
        )
        for c in climbs
    ]

    # Compute moving time: sum time intervals where speed > 0.5 m/s
    moving_time_s = None
    has_real_time = any(getattr(p, "_real_t", False) for p in raw_points)
    if has_real_time:
        moving = 0.0
        for i in range(1, len(raw_sorted)):
            dt = raw_sorted[i].t - raw_sorted[i - 1].t
            if dt <= 0:
                continue
            dd = haversine_m(
                raw_sorted[i - 1].lat,
                raw_sorted[i - 1].lon,
                raw_sorted[i].lat,
                raw_sorted[i].lon,
            )
            speed = dd / dt
            if speed > 0.5:
                moving += dt
        moving_time_s = round(moving)

    ride = dict(name=name, points=pts, climbs=climb_data)
    if moving_time_s is not None:
        ride["moving_time_s"] = moving_time_s
    return ride


def parse_gpx(filepath):
    """Parse a GPX file into a list of RawPoints."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    # Handle GPX namespace
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    points = []
    t = 0.0
    epoch = None
    for trkpt in root.iter(f"{ns}trkpt"):
        lat = float(trkpt.get("lat"))
        lon = float(trkpt.get("lon"))
        ele_el = trkpt.find(f"{ns}ele")
        elev = float(ele_el.text) if ele_el is not None else None
        if elev is None:
            continue

        time_el = trkpt.find(f"{ns}time")
        if time_el is not None:
            ts = datetime.fromisoformat(time_el.text.replace("Z", "+00:00"))
            if epoch is None:
                epoch = ts
            t = (ts - epoch).total_seconds()
            p = RawPoint(t=t, lat=lat, lon=lon, elev_m=elev)
            p._real_t = True
        else:
            t += 1.0
            p = RawPoint(t=t, lat=lat, lon=lon, elev_m=elev)
            p._real_t = False
        points.append(p)
    return points


def load_gpx_rides(data_dir="data"):
    """Load all .gpx files from data_dir as rides."""
    rides = {}
    if not os.path.isdir(data_dir):
        return rides
    for path in sorted(glob.glob(os.path.join(data_dir, "*.gpx"))):
        name = os.path.splitext(os.path.basename(path))[0]
        rides[name] = parse_gpx(path)
    return rides


def main():
    all_rides = load_gpx_rides()

    output = [export_ride(name, raw) for name, raw in all_rides.items()]

    with open("viz_data.json", "w") as f:
        json.dump(output, f)

    print(f"Exported {len(output)} rides to viz_data.json")
    for ride in output:
        n_climbs = len(ride["climbs"])
        n_pts = len(ride["points"])
        print(f"  {ride['name']}: {n_pts} points, {n_climbs} climb(s)")


if __name__ == "__main__":
    main()
