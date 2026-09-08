from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

LAT_VALIDATORS = [MinValueValidator(-90), MaxValueValidator(90)]
LNG_VALIDATORS = [MinValueValidator(-180), MaxValueValidator(180)]

# Kept as the existing Title-Case strings already stored in the DB (see
# management/commands/seed_campus.py) rather than switching to lowercase
# machine values, so existing rows and the current map/admin keep
# displaying/filtering exactly as they do today. `General` is the
# pre-existing default; the rest are the categories the visitor app
# needs (academic/admin/facility/food/sports/parking/entrance/hostel/
# medical/other from the visitor-app spec).
LOCATION_CATEGORY_CHOICES = [
    ('Academic', 'Academic'),
    ('Admin', 'Admin'),
    ('Entrance', 'Entrance'),
    ('Facility', 'Facility'),
    ('Food', 'Food'),
    ('Sports', 'Sports'),
    ('Parking', 'Parking'),
    ('Hostel', 'Hostel'),
    ('Medical', 'Medical'),
    ('General', 'General'),
    ('Other', 'Other'),
]


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
    category = models.CharField(
        max_length=50, default='General', blank=True, choices=LOCATION_CATEGORY_CHOICES
    )
    geofence_radius = models.FloatField(
        default=50, validators=[MinValueValidator(1), MaxValueValidator(2000)]
    )

    # --- Visitor app (QR scan -> live map guide) fields below. Existing
    # fields above are untouched. ---

    # Short public ID used in QR URLs, e.g. /l/main-gate/. Globally unique
    # (not just per-campus) so a single /l/<code>/ route can resolve a
    # scan without needing the campus slug in the URL. Auto-generated
    # from `name` in save() below when left blank.
    code = models.SlugField(max_length=160, unique=True, blank=True, db_index=True)
    short_description = models.CharField(max_length=160, blank=True, default='')
    photo = models.ImageField(upload_to='locations/', blank=True, null=True)
    floor_count = models.PositiveSmallIntegerField(null=True, blank=True)
    open_time = models.TimeField(null=True, blank=True)
    close_time = models.TimeField(null=True, blank=True)
    is_scannable = models.BooleanField(default=True, help_text='Whether a QR sticker exists for this location.')
    is_published = models.BooleanField(default=True, help_text='Hide draft locations from the visitor app.')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['campus', 'name']
        indexes = [models.Index(fields=['category'])]
        # `code` isn't listed here too: unique=True above already gives it
        # its own DB index, so a second one would just be a duplicate.

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_unique_code()
        super().save(*args, **kwargs)

    def _generate_unique_code(self) -> str:
        base = slugify(self.name)[:140] or 'location'
        candidate = base
        suffix = 2
        queryset = Location.objects.all()
        if self.pk:
            queryset = queryset.exclude(pk=self.pk)
        while queryset.filter(code=candidate).exists():
            candidate = f'{base}-{suffix}'
            suffix += 1
        return candidate

    @property
    def is_open_now(self):
        """True/False once hours are set, None when they aren't (so the UI
        can show an "Open/Closed" pill only when it actually knows)."""
        if not self.open_time or not self.close_time:
            return None

        now = timezone.localtime().time()
        if self.open_time <= self.close_time:
            return self.open_time <= now <= self.close_time
        # Overnight range, e.g. open_time=22:00, close_time=06:00.
        return now >= self.open_time or now <= self.close_time


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


class ScanEvent(models.Model):
    """
    One QR-sticker scan (from /l/<code>/ or the in-app scanner). Kept
    even if the Location is later deleted (SET_NULL) since the raw code
    and timestamp are still useful analytics on their own.
    """

    location = models.ForeignKey(
        Location, on_delete=models.SET_NULL, null=True, blank=True, related_name='scan_events'
    )
    code_raw = models.CharField(max_length=120, help_text='What was actually scanned/submitted.')
    scanned_at = models.DateTimeField(auto_now_add=True, db_index=True)
    user_agent = models.CharField(max_length=300, blank=True)
    session_key = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ['-scanned_at']

    def __str__(self):
        return f'{self.code_raw} @ {self.scanned_at:%Y-%m-%d %H:%M}'


class Tour(models.Model):
    """A curated, ordered walk through several Locations (guided-tour mode)."""

    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    summary = models.TextField(blank=True, default='')
    cover_image = models.ImageField(upload_to='tours/', blank=True, null=True)
    duration_minutes = models.PositiveSmallIntegerField(default=15)
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']

    def __str__(self):
        return self.title


class TourStop(models.Model):
    """One stop (in order) on a Tour."""

    tour = models.ForeignKey(Tour, on_delete=models.CASCADE, related_name='stops')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='tour_stops')
    order = models.PositiveSmallIntegerField()
    note = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['tour', 'order'], name='unique_tour_stop_order'),
        ]

    def __str__(self):
        return f'{self.tour.title} #{self.order}: {self.location.name}'
