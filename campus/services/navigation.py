"""
Full flow: GPS location -> nearest graph node -> A* to the destination
location's nearest graph node -> ordered path with distance and estimated
walking time. Returns a plain dict (not a model) so the API view can shape
it into camelCase JSON directly.
"""

import sys

from django.conf import settings

from campus.models import GraphEdge, GraphNode, Location

from . import astar, haversine


def calculate_route(start_lat: float, start_lon: float, destination_location_id: int) -> dict:
    try:
        destination = Location.objects.get(pk=destination_location_id)
    except Location.DoesNotExist:
        return {'success': False, 'message': 'Destination not found.'}

    all_nodes = list(GraphNode.objects.all())
    all_edges = list(GraphEdge.objects.all())

    if not all_nodes:
        return {
            'success': False,
            'message': 'Campus graph has no nodes yet. Add graph nodes/edges from the Admin panel.',
        }

    start_node = _find_nearest_node(all_nodes, start_lat, start_lon)
    destination_node = _find_nearest_node(all_nodes, destination.latitude, destination.longitude)

    if not start_node or not destination_node:
        return {'success': False, 'message': 'Could not find a nearby graph node.'}

    path = astar.find_path(all_nodes, all_edges, start_node.id, destination_node.id)

    if len(path) == 0:
        return {
            'success': False,
            'message': 'No walkable path found between your location and the destination. Check that the graph is fully connected.',
        }

    total_distance = 0.0
    for i in range(len(path) - 1):
        total_distance += haversine.distance_meters(
            path[i].latitude, path[i].longitude,
            path[i + 1].latitude, path[i + 1].longitude,
        )

    walking_speed = settings.CAMPUS_WALKING_SPEED_M_PER_MIN

    return {
        'success': True,
        'message': None,
        'path': [
            {
                'nodeId': n.id,
                'name': n.name,
                'latitude': n.latitude,
                'longitude': n.longitude,
            }
            for n in path
        ],
        'totalDistanceMeters': round(total_distance, 1),
        'estimatedWalkingMinutes': round(total_distance / walking_speed, 1),
    }


def _find_nearest_node(nodes, lat: float, lon: float):
    """
    Step "GPS Location -> Nearest Campus Node": picks the graph node with
    the smallest Haversine distance to the given point.
    """
    nearest = None
    best_distance = sys.float_info.max

    for node in nodes:
        distance = haversine.distance_meters(lat, lon, node.latitude, node.longitude)
        if distance < best_distance:
            best_distance = distance
            nearest = node

    return nearest
