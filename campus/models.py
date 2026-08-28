from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

LAT_VALIDATORS = [MinValueValidator(-90), MaxValueValidator(90)]
LNG_VALIDATORS = [MinValueValidator(-180), MaxValueValidator(180)]


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
        ordering = ['name']

    def __str__(self):
        return self.name


class GraphNode(models.Model):
    """A walkable point in the path network (intersection, building entrance, etc.)."""

    name = models.CharField(max_length=150)
    latitude = models.FloatField(validators=LAT_VALIDATORS)
    longitude = models.FloatField(validators=LNG_VALIDATORS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

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

    def __str__(self):
        return f'{self.from_node} ↔ {self.to_node} ({self.distance} m)'


class BoundaryPoint(models.Model):
    """An ordered vertex of the closed campus boundary polygon."""

    latitude = models.FloatField(validators=LAT_VALIDATORS)
    longitude = models.FloatField(validators=LNG_VALIDATORS)
    sequence_order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sequence_order']

    def __str__(self):
        return f'#{self.sequence_order}: {self.latitude:.6f}, {self.longitude:.6f}'
