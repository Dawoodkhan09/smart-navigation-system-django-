"""
Our own A* implementation over the campus walkway graph.

    f(n) = g(n) + h(n)

    g(n) = actual walking distance (meters) accumulated from the start
           node to node n, following real graph edges.
    h(n) = Haversine straight-line distance (meters) from node n to the
           destination node - an admissible heuristic, since the
           straight-line distance can never be more than the real
           walking distance.
    f(n) = total estimated cost of the best path through n.

No third-party routing library is used - this is a plain implementation
of the textbook algorithm using a min-heap (Python's `heapq` is already a
min-heap, so no custom priority-queue wrapper is needed).
"""

import heapq
import itertools

from . import haversine


def find_path(nodes, edges, start_node_id, destination_node_id):
    """
    nodes: iterable of GraphNode-like objects (id, latitude, longitude)
    edges: iterable of GraphEdge-like objects (from_node_id, to_node_id, distance)

    Returns an ordered list of node objects from start to destination, or
    [] if no path exists.
    """
    nodes_by_id = {n.id: n for n in nodes}

    if start_node_id not in nodes_by_id or destination_node_id not in nodes_by_id:
        return []

    # Build an undirected adjacency list: every edge can be walked in
    # either direction.
    adjacency = {node_id: [] for node_id in nodes_by_id}
    for edge in edges:
        if edge.from_node_id not in adjacency or edge.to_node_id not in adjacency:
            continue  # skip edges pointing at nodes that no longer exist
        adjacency[edge.from_node_id].append((edge.to_node_id, float(edge.distance)))
        adjacency[edge.to_node_id].append((edge.from_node_id, float(edge.distance)))

    destination = nodes_by_id[destination_node_id]

    def heuristic(node_id):
        n = nodes_by_id[node_id]
        return haversine.distance_meters(n.latitude, n.longitude, destination.latitude, destination.longitude)

    # node_id -> {'g': float, 'f': float, 'came_from': int|None}
    records = {start_node_id: {'g': 0.0, 'f': heuristic(start_node_id), 'came_from': None}}

    counter = itertools.count()  # tie-breaker so heap never compares node ids
    open_set = [(records[start_node_id]['f'], next(counter), start_node_id)]
    closed_set = set()

    while open_set:
        _, _, current_id = heapq.heappop(open_set)

        if current_id in closed_set:
            continue  # stale queue entry

        if current_id == destination_node_id:
            return _reconstruct_path(records, current_id, nodes_by_id)

        closed_set.add(current_id)

        for neighbor_id, weight in adjacency[current_id]:
            if neighbor_id in closed_set:
                continue

            tentative_g = records[current_id]['g'] + weight

            if neighbor_id not in records or tentative_g < records[neighbor_id]['g']:
                f = tentative_g + heuristic(neighbor_id)
                records[neighbor_id] = {'g': tentative_g, 'f': f, 'came_from': current_id}
                heapq.heappush(open_set, (f, next(counter), neighbor_id))

    return []  # No path found.


def _reconstruct_path(records, end_node_id, nodes_by_id):
    path = []
    current_id = end_node_id

    while current_id is not None:
        path.append(nodes_by_id[current_id])
        current_id = records[current_id]['came_from']

    path.reverse()
    return path
