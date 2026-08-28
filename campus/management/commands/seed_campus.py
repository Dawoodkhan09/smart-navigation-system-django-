"""
Seeds this command with the REAL locations, boundary and (best-guess)
walkway graph from the original campus survey - not placeholder data.
Ported verbatim from the Laravel app's database/seeders/CampusSeeder.php.

Two things still need attention after this runs:

1. "Building 3" (admin room 106-8 + C-lab 03) and "Building 5" (ground
   floor AC 109 + first floor C-lab 4) are NOT seeded - their GPS
   coordinates were never provided. Add them via the admin panel (and a
   matching graph node) once you've walked out there with a phone and
   noted their lat/lng.

2. The GraphEdges below (the walkway connections) are an EDUCATED GUESS
   based on the relative positions of the buildings - not a real measured
   path network. Distances are computed from real GPS coordinates via
   Haversine, so they're accurate straight-line distances, but the actual
   walkway might curve, or connect buildings differently than guessed
   here. Walk the campus and correct/add edges via the admin panel -
   that's what actually determines the routes A* will suggest.
"""

from django.core.management.base import BaseCommand

from campus.models import BoundaryPoint, GraphEdge, GraphNode, Location
from campus.services import haversine

LOCATIONS = [
    {'name': 'Main Gate', 'description': 'Main entrance of the campus.', 'latitude': 24.88534020573535, 'longitude': 67.17154097985589, 'category': 'Entrance', 'geofence_radius': 30},
    {'name': 'Garden Area', 'description': 'Campus garden.', 'latitude': 24.88547268503638, 'longitude': 67.1717913321266, 'category': 'Facility', 'geofence_radius': 30},
    {'name': 'Masjid', 'description': 'Campus mosque.', 'latitude': 24.88583533822713, 'longitude': 67.17164741544522, 'category': 'Facility', 'geofence_radius': 30},
    {'name': 'Building A', 'description': "Ground floor: CS HOD office, Faculty room 2, Faculty room 3, Faculty room 4, Faculty room 5, Media HOD room, Director room, Admission office.\n1st floor: IT room, Examination department, C-Lab 1, C-Lab 2, Classroom 202, Classroom 203, Medio studio, Music room.", 'latitude': 24.885819462357194, 'longitude': 67.17196461865626, 'category': 'Academic', 'geofence_radius': 45},
    {'name': 'CCTV Room', 'description': 'Campus CCTV monitoring room.', 'latitude': 24.88595153736792, 'longitude': 67.17188378699797, 'category': 'Admin', 'geofence_radius': 20},
    {'name': 'Old Cafeteria', 'description': 'Old cafeteria.', 'latitude': 24.88596128871092, 'longitude': 67.17172559423251, 'category': 'Food', 'geofence_radius': 30},
    {'name': 'Student Council', 'description': 'Student council office.', 'latitude': 24.885652243199527, 'longitude': 67.17222156465198, 'category': 'Admin', 'geofence_radius': 25},
    {'name': 'Fees Affairs', 'description': 'Fees affairs office.', 'latitude': 24.88578186369185, 'longitude': 67.17206226904662, 'category': 'Admin', 'geofence_radius': 20},
    {'name': 'Finance Room', 'description': 'Finance room.', 'latitude': 24.88582237315094, 'longitude': 67.17206545874853, 'category': 'Admin', 'geofence_radius': 20},
    {'name': 'Building 2', 'description': 'Rooms 102-105, Sports room, male washroom, staff male washroom.', 'latitude': 24.886108832521774, 'longitude': 67.17211489912728, 'category': 'Academic', 'geofence_radius': 35},
    # Building 3 (admin room 106-8 + C-lab 03) - coordinates not provided, add manually.
    {'name': 'Futsal Ground', 'description': 'Futsal ground.', 'latitude': 24.886344212633542, 'longitude': 67.17214232184021, 'category': 'Facility', 'geofence_radius': 30},
    {'name': 'Building 4', 'description': 'Classrooms 301-306.', 'latitude': 24.88659175919714, 'longitude': 67.17202037359395, 'category': 'Academic', 'geofence_radius': 40},
    # Building 5 (ground floor AC 109 + first floor C-lab 4) - coordinates not provided, add manually.
    {'name': 'Cafeteria', 'description': 'Cafeteria.', 'latitude': 24.886885450548654, 'longitude': 67.17207938307956, 'category': 'Food', 'geofence_radius': 35},
    {'name': 'Car Parking', 'description': 'Car parking.', 'latitude': 24.88671618024905, 'longitude': 67.17221813511325, 'category': 'Facility', 'geofence_radius': 40},
    {'name': 'Library', 'description': 'Library.', 'latitude': 24.8865201, 'longitude': 67.1722113, 'category': 'Academic', 'geofence_radius': 40},
]

# Best-guess walkway connections (see module doc comment above).
EDGES = [
    ('Main Gate', 'Garden Area'),
    ('Main Gate', 'Masjid'),
    ('Garden Area', 'Masjid'),
    ('Masjid', 'Old Cafeteria'),
    ('Old Cafeteria', 'CCTV Room'),
    ('CCTV Room', 'Building A'),
    ('Old Cafeteria', 'Building A'),
    ('Building A', 'Fees Affairs'),
    ('Fees Affairs', 'Finance Room'),
    ('Finance Room', 'Student Council'),
    ('Building A', 'Building 2'),
    ('Building 2', 'Futsal Ground'),
    ('Futsal Ground', 'Building 4'),
    ('Building 4', 'Cafeteria'),
    ('Cafeteria', 'Car Parking'),
    ('Cafeteria', 'Library'),
    ('Car Parking', 'Library'),
]

# Campus boundary polygon - from the GeoJSON traced on geojson.io.
# (17 points were given as a closed LineString; the duplicate closing
# point, identical to the first, is dropped here.)
BOUNDARY = [
    (24.8853513, 67.1715439),
    (24.8858876, 67.1716049),
    (24.8860094, 67.1716871),
    (24.8866723, 67.1718109),
    (24.8868893, 67.1718597),
    (24.886976, 67.1719938),
    (24.8869471, 67.1723377),
    (24.8868989, 67.1725576),
    (24.8867599, 67.1726263),
    (24.8866264, 67.1726489),
    (24.8865126, 67.1723919),
    (24.8861651, 67.1723808),
    (24.8859702, 67.1723523),
    (24.8856535, 67.1723021),
    (24.8854493, 67.172284),
    (24.8852201, 67.1722657),
]


class Command(BaseCommand):
    help = 'Seeds the real campus locations, walkway graph and boundary polygon (no-op if already seeded).'

    def handle(self, *args, **options):
        if Location.objects.exists() or GraphNode.objects.exists():
            self.stdout.write(self.style.WARNING('Already seeded - skipping.'))
            return

        nodes_by_name = {}

        for loc in LOCATIONS:
            Location.objects.create(**loc)
            node = GraphNode.objects.create(
                name=loc['name'], latitude=loc['latitude'], longitude=loc['longitude']
            )
            nodes_by_name[loc['name']] = node

        for from_name, to_name in EDGES:
            from_node = nodes_by_name[from_name]
            to_node = nodes_by_name[to_name]
            GraphEdge.objects.create(
                from_node=from_node,
                to_node=to_node,
                distance=round(
                    haversine.distance_meters(
                        from_node.latitude, from_node.longitude,
                        to_node.latitude, to_node.longitude,
                    ),
                    1,
                ),
            )

        for i, (lat, lng) in enumerate(BOUNDARY):
            BoundaryPoint.objects.create(latitude=lat, longitude=lng, sequence_order=i)

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {len(LOCATIONS)} locations, {len(EDGES)} edges, {len(BOUNDARY)} boundary points.'
        ))
