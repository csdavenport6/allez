from dataclasses import dataclass
from typing import List


@dataclass
class Point:
    d: float
    e: float


@dataclass
class Climb:
    start: int
    end: int
    dist_m: float
    gain_m: float
    avg_grade: float
    category: str  # "HC", "1", "2", "3", "4", or ""


def smooth_elevation_basic(points: List[Point], window: int = 5) -> List[Point]:
    """Moving average on elevation only"""
    if window <= 1 or len(points) < 3:
        return points[:]
    if window % 2 == 0:
        window += 1

    n = len(points)
    half = window // 2
    out = []

    prefix = [0.0]
    for p in points:
        prefix.append(prefix[-1] + p.e)

    for i in range(n):
        lo = max(0, i - half)
        hi = min(n - 1, i + half)
        avg_e = (prefix[hi + 1] - prefix[lo]) / (hi - lo + 1)
        out.append(Point(points[i].d, avg_e))
    return out


def smooth_elevation_savgol(
    points: List[Point], window: int = 11, poly_order: int = 2
) -> List[Point]:
    if len(points) < window:
        return points[:]
    import numpy as np

    elevs = np.array([p.e for p in points])

    # Ensure window is odd
    if window % 2 == 0:
        window += 1

    half = window // 2
    # Build Vandermonde matrix centered at 0
    x = np.arange(-half, half + 1, dtype=float)
    A = np.vander(x, N=poly_order + 1, increasing=True)
    # Coefficients: row 0 of (A^T A)^{-1} A^T gives the smoothing weights
    coeffs = np.linalg.pinv(A)[0]

    # Pad edges by reflection
    padded = np.concatenate([elevs[half:0:-1], elevs, elevs[-2:-half - 2:-1]])
    smoothed = np.convolve(padded, coeffs[::-1], mode='valid')

    return [Point(p.d, float(s)) for p, s in zip(points, smoothed)]


# Categorization based on Fiets index (cotacol) with standard TdF thresholds
def categorize_climb(gain_m: float, dist_m: float) -> str:
    difficulty = (gain_m**2) / (dist_m / 10)
    if difficulty >= 250:
        return "HC"
    elif 150 <= difficulty <= 249:
        return "1"
    elif 100 <= difficulty <= 149:
        return "2"
    elif 50 <= difficulty <= 99:
        return "3"
    elif 20 <= difficulty <= 49:
        return "4"
    else:
        return ""


def total_elevation_gain(points: List[Point]) -> float:
    """Compute total elevation gain over smoothed points."""
    smoothed = smooth_elevation_savgol(points)
    gain = 0.0
    for i in range(1, len(smoothed)):
        de = smoothed[i].e - smoothed[i - 1].e
        if de > 0:
            gain += de
    return gain


def summarize(points: List[Point], s: int, t: int) -> Climb:
    gain = 0.0
    for i in range(s + 1, t + 1):
        de = points[i].e - points[i - 1].e
        if de > 0:
            gain += de
    dist = points[t].d - points[s].d
    avg_grade = gain / dist if dist > 0 else 0.0
    difficulty = categorize_climb(gain, dist)
    return Climb(s, t, dist, gain, avg_grade, difficulty)


def detect_climbs(points: List[Point]) -> List[Climb]:
    """
    Detect climbs using:
    - smoothing
    - hysteresis
    - threshold filtering
    - simple merge of nearby climbs
    """
    if len(points) < 2:
        return []

    _points = smooth_elevation_savgol(points, window=11, poly_order=2)

    # Thresholds
    MIN_DIST = 400.0  # meters
    MIN_GAIN = 30.0  # meters
    MIN_AVG_GRADE = 0.03
    MAX_DROP_INSIDE = 6.0  # small dips inside climbs
    MAX_FLAT_DOWN_GAP = 150.0  # meters before ending a climb

    climbs = []
    in_climb = False
    start = 0
    downhill_budget = 0.0
    gap_start = None

    for i in range(1, len(_points)):
        delta_d = _points[i].d - _points[i - 1].d
        delta_e = _points[i].e - _points[i - 1].e
        if delta_d <= 0:
            continue

        if not in_climb:
            # Start when an uphill step is seen
            if delta_e > 0:
                in_climb = True
                start = i - 1
                downhill_budget = 0.0
                gap_start = None
            continue

        # In a climb. Allez!
        if delta_e > 0:
            downhill_budget = max(0.0, downhill_budget - delta_e)
            gap_start = None
        else:
            # Spend downhill budget and track gap distance
            downhill_budget += max(0.0, -delta_e)
            if gap_start is None:
                gap_start = i - 1

            gap_dist = _points[i].d - _points[gap_start].d

            # End climb if too much downhill or flat/down section goes too long
            if downhill_budget > MAX_DROP_INSIDE or gap_dist > MAX_FLAT_DOWN_GAP:
                end = max(start + 1, gap_start)
                c = summarize(_points, start, end)

                if (
                    c.dist_m >= MIN_DIST
                    and c.gain_m >= MIN_GAIN
                    and c.avg_grade >= MIN_AVG_GRADE
                ):
                    climbs.append(c)

                in_climb = False
                downhill_budget = 0.0
                gap_start = None

    if in_climb:
        c = summarize(_points, start, len(_points) - 1)
        if (
            c.dist_m >= MIN_DIST
            and c.gain_m >= MIN_GAIN
            and c.avg_grade >= MIN_AVG_GRADE
        ):
            climbs.append(c)

    # Simple merge pass: merge climbs separated by a short gap
    merged: List[Climb] = []
    MERGE_GAP_DIST = 250.0
    for c in climbs:
        if not merged:
            merged.append(c)
            continue

        prev = merged[-1]
        gap = _points[c.start].d - _points[prev.end].d
        if gap <= MERGE_GAP_DIST:
            merged[-1] = summarize(_points, prev.start, c.end)
        else:
            merged.append(c)

    # Re-filter after merge
    final = [
        c
        for c in merged
        if c.dist_m >= MIN_DIST
        and c.gain_m >= MIN_GAIN
        and c.avg_grade >= MIN_AVG_GRADE
    ]
    return final
