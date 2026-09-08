"""
Point-in-polygon test for the campus boundary check. Pure function, no
Django imports - same style as haversine.py/astar.py. Mirrors the
ray-casting algorithm already used client-side in
static/campus/js/point-in-polygon.js, so the server and the browser
always agree on the answer.
"""


def point_in_polygon(lat: float, lng: float, polygon: list) -> bool:
    """
    polygon: ordered list of (lat, lng) tuples, or objects/dicts with
    latitude/longitude - does not need to repeat the first point at the
    end, the closing edge is assumed automatically.

    Casts an imaginary ray from the point out to increasing longitude and
    counts how many polygon edges it crosses. An odd number of crossings
    means the point is inside; even (including zero) means outside.
    """
    if not polygon or len(polygon) < 3:
        return False

    points = [_coords(p) for p in polygon]
    inside = False
    j = len(points) - 1

    for i in range(len(points)):
        yi, xi = points[i]
        yj, xj = points[j]

        intersects = ((yi > lat) != (yj > lat)) and (
            lng < (xj - xi) * (lat - yi) / (yj - yi) + xi
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def _coords(point):
    if isinstance(point, (tuple, list)):
        return point[0], point[1]
    if isinstance(point, dict):
        return point['latitude'], point['longitude']
    return point.latitude, point.longitude
