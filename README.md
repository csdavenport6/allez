# What Is This?

# AI Use
Claude Code was used for the following:
- visualizer.{css,html} 
- GPX file parsing in `export_viz_data.py`, as well as the moving time calculation. 

# Ride Visualization with Climb Detection
First, run `uv run export_viz_data.py` to identify climbs from the gpx files in `data/`.

Start the http server with `python3 -m http.server 8771 -d .` in the root directory of the repo.
Then, navigate [here](localhost:8771/visualizer.html) to see a basic visualization (route map plus climb profile).

## Basic approach
Four-step breakdown:
1. Geospatial pre-processing to turn data of the form [(lat, long, elev, time)] into [(cumulative_distance_traveled, elev)]. 
2. 

## More advanced techniques (TODO)
- Better smoothing of GPS elevation data. Simplest approach uses a basic moving average, but something like a Gaussian kernel or a Savitzky-Golay filter would preserve shape better. The simple moving average flattens everything towards the mean, whereas SG fits a polynomial to each window and takes its center value, thus preserving the peaks and valleys.
- Two-pass segmentation instead of a one-pass approach that commits greedily to being in a climb or not. 
- 

## Misc

### Haversine Formula

Longitude and latitude are angles, not flat x/y coordinates. The shortest path on Earth's surface is along a great circle, not a straight line on a flat map.

If the two points are (lat1, lon1) and (lat2, lon2) in radians:
 • dlat = lat2 - lat1
 • dlon = lon2 - lon1

Then:
 • a = sin²(dlat/2) + cos(lat1) *cos(lat2)* sin²(dlon/2)
 • c = 2 *atan2(sqrt(a), sqrt(1-a))
 • distance = R* c

Where R is Earth’s radius (commonly ~6,371,000 meters).

"Haversine" is an old trig function:
 • hav(theta) = sin²(theta/2)

The formula written this way has the convenient property of numerical stability for small distances, useful to GPS point-to-point calculations.

```python
import math

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

```



