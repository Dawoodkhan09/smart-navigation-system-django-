"""
Great-circle distance between two GPS coordinates using the Haversine
formula. Used for: geofence checks, finding the nearest graph node to a
GPS point, the A* heuristic, and distance display.
"""

import math

EARTH_RADIUS_METERS = 6371000


def distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Returns the distance between two points in meters."""
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_METERS * c
