"""
Turn-by-turn instruction generation from an ordered walking path. Pure
functions, no Django imports - same style as haversine.py/astar.py.
Consumed by the /api/v2/route/ endpoint to turn the raw A* node path
into human directions ("Head north", "Turn slight left", ...).
"""

import math

from . import haversine

# Turn classification thresholds (degrees of bearing change).
_STRAIGHT_MAX = 20
_SLIGHT_MAX = 55
_SHARP_MIN = 125

_COMPASS_WORDS = ['north', 'northeast', 'east', 'southeast', 'south', 'southwest', 'west', 'northwest']


def bearing(a, b) -> float:
    """
    Initial compass bearing in degrees (0-360, 0 = north, clockwise) from
    point `a` to point `b`. Each point can be a (lat, lng) tuple, a dict
    with latitude/longitude keys, or an object with those attributes
    (e.g. a GraphNode).
    """
    lat1, lon1 = _coords(a)
    lat2, lon2 = _coords(b)

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lon = math.radians(lon2 - lon1)

    x = math.sin(delta_lon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lon)

    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def turn_word(prev_bearing: float, next_bearing: float) -> str:
    """
    Classifies the change from prev_bearing to next_bearing into a human
    instruction: "Continue straight", "Turn slight left/right",
    "Turn left/right", or "Turn sharp left/right".

    Thresholds: < 20 degrees straight, 20-55 slight, 55-125 turn,
    > 125 sharp.
    """
    # Signed difference in (-180, 180], positive = turning right (clockwise).
    diff = (next_bearing - prev_bearing + 540) % 360 - 180
    magnitude = abs(diff)

    if magnitude < _STRAIGHT_MAX:
        return 'Continue straight'

    side = 'right' if diff > 0 else 'left'

    if magnitude < _SLIGHT_MAX:
        return f'Turn slight {side}'
    if magnitude <= _SHARP_MIN:
        return f'Turn {side}'
    return f'Turn sharp {side}'


def steps_from_path(path) -> list:
    """
    path: ordered list of walkable points (GraphNode objects, or dicts
    with latitude/longitude/name - e.g. the `path` a
    campus.services.navigation route result already carries).

    Returns a list of {instruction, distance_m, bearing, from, to} dicts.
    The first step always starts with "Head <compass direction>"; the
    last is always "Arrive at {name}". Returns [] for a path shorter than
    2 points (nothing to walk).
    """
    if len(path) < 2:
        return []

    steps = []
    prev_bearing = None

    for i in range(len(path) - 1):
        a, b = path[i], path[i + 1]
        seg_bearing = bearing(a, b)
        seg_distance = haversine.distance_meters(*_coords(a), *_coords(b))

        instruction = f'Head {_compass_word(seg_bearing)}' if i == 0 else turn_word(prev_bearing, seg_bearing)

        steps.append({
            'instruction': instruction,
            'distance_m': round(seg_distance, 1),
            'bearing': round(seg_bearing, 1),
            'from': _name(a),
            'to': _name(b),
        })
        prev_bearing = seg_bearing

    destination_name = _name(path[-1])
    steps.append({
        'instruction': f'Arrive at {destination_name}',
        'distance_m': 0.0,
        'bearing': round(prev_bearing, 1) if prev_bearing is not None else 0.0,
        'from': destination_name,
        'to': destination_name,
    })

    return steps


def _compass_word(deg: float) -> str:
    index = round(deg / 45) % 8
    return _COMPASS_WORDS[index]


def _coords(point):
    if isinstance(point, (tuple, list)):
        return point[0], point[1]
    if isinstance(point, dict):
        return point['latitude'], point['longitude']
    return point.latitude, point.longitude


def _name(point):
    if isinstance(point, dict):
        return point.get('name')
    return getattr(point, 'name', None)
