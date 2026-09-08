from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

LAT_VALIDATORS = [MinValueValidator(-90), MaxValueValidator(90)]
LNG_VALIDATORS = [MinValueValidator(-180), MaxValueValidator(180)]


class Campus(models.Model):
    """
    One physical campus. Everything else (Location, GraphNode, GraphEdge,
    BoundaryPoint) belongs to exactly one Campus - this is what makes
    multi-campus support possible: each campus gets its own map center/
    zoom, its own set of locations/walkways, and its own boundary
    polygon, all scoped by this row instead of the old single set of
    CAMPUS_* Django settings.
    """

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True, help_text='Used in the campus URL, e.g. /c/main-campus/.')
    center_latitude = models.FloatField(validators=LAT_VALIDATORS)
    center_longitude = models.FloatField(validators=LNG_VALIDATORS)
    default_zoom = models.PositiveSmallIntegerField(default=17)
    walking_speed_m_per_min = models.FloatField(default=80, validators=[MinValueValidator(1)])
    default_geofence_radius = models.FloatField(default=50, validators=[MinValueValidator(1), MaxValueValidator(2000)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'campuses'

    def __str__(self):
        return self.name


class Location(models.Model):
    """
    A named campus place (building, gate, department, etc.) shown on the
    map, searchable as a destination, with a geofence circle around it.

    Several real buildings on this campus contain multiple rooms (faculty
    offices, labs, etc.). Rather than one pointer per room, each BUILDING
    is a single Location, and the individual rooms/floors are just listed
    inside its `description` text. Searching for a room name matches
    against `description` too (see campus.api_views.location_search), and
    takes the user to that building's pointer.
    """

    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    latitude = models.FloatField(validators=LAT_VALIDATORS)
    longitude = models.FloatField(validators=LNG_VALIDATORS)
    category = models.CharField(max_length=50, default='General', blank=True)
    geofence_radius = models.FloatField(
        default=50, validators=[MinValueValidator(1), MaxValueValidator(2000)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['campus', 'name']

    def __str__(self):
        return self.name


class GraphNode(models.Model):
    """A walkable point in the path network (intersection, building entrance, etc.)."""

    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='graph_nodes')
    name = models.CharField(max_length=150)
    latitude = models.FloatField(validators=LAT_VALIDATORS)
    longitude = models.FloatField(validators=LNG_VALIDATORS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['campus', 'name']

    def __str__(self):
        return self.name


class GraphEdge(models.Model):
    """
    A walkway connection between two graph nodes. Treated as undirected by
    the routing algorithm - one row represents a bidirectional walkway.
    """

    from_node = models.ForeignKey(
        GraphNode, on_delete=models.PROTECT, related_name='edges_from'
    )
    to_node = models.ForeignKey(
        GraphNode, on_delete=models.PROTECT, related_name='edges_to'
    )
    distance = models.FloatField(
        validators=[MinValueValidator(0.1), MaxValueValidator(100000)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.from_node_id and self.to_node_id and self.from_node_id == self.to_node_id:
            raise ValidationError('From Node and To Node must be different.')
        # No campus FK on GraphEdge itself - it's implicitly scoped through
        # its two nodes, so the one thing that must hold is that they agree.
        # Without this check it's easy to accidentally wire one campus's
        # walkway into another's graph via the from/to node dropdowns.
        if (
            self.from_node_id and self.to_node_id
            and self.from_node.campus_id != self.to_node.campus_id
        ):
            raise ValidationError('From Node and To Node must belong to the same campus.')

    def __str__(self):
        return f'{self.from_node} ↔ {self.to_node} ({self.distance} m)'


class BoundaryPoint(models.Model):
    """An ordered vertex of the closed campus boundary polygon."""

    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name='boundary_points')
    latitude = models.FloatField(validators=LAT_VALIDATORS)
    longitude = models.FloatField(validators=LNG_VALIDATORS)
    sequence_order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['campus', 'sequence_order']

    def __str__(self):
        return f'#{self.sequence_order}: {self.latitude:.6f}, {self.longitude:.6f}'
