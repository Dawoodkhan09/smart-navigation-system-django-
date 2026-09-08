import json

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import BoundaryPoint, Campus, GraphEdge, GraphNode, Location, ScanEvent, Tour, TourStop
from .services import haversine, qr

# Fallback map center only used when NO campus exists yet at all (so an
# admin adding the very first Campus still gets a sane starting point on
# its own picker map) - this campus's real approximate center.
FALLBACK_CENTER_LAT = 24.8844
FALLBACK_CENTER_LNG = 67.1720
FALLBACK_ZOOM = 17


@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    """
    The tenant model everything else (Location, GraphNode, GraphEdge via
    its nodes, BoundaryPoint) belongs to. Add a campus here first, then
    its Locations/Graph Nodes/Campus Boundary via the other admin pages
    (each of those forms has a Campus dropdown to pick this one).
    """

    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug', 'center_latitude', 'center_longitude', 'default_zoom')
    search_fields = ('name', 'slug')


class MapPickerAdminMixin:
    """Embeds a small Leaflet map on the add/change form so an admin can
    click a point instead of typing coordinates by hand (mirrors the
    original Laravel admin's create/edit forms)."""

    class Media:
        css = {'all': ('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',)}
        js = (
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            'campus/js/basemaps.js',
            'campus/js/admin-map-picker.js',
        )

    def _with_campus_config(self, extra_context=None, obj=None):
        extra_context = dict(extra_context or {})

        # Center the picker map on the OBJECT'S OWN campus when editing an
        # existing row; otherwise fall back to whichever campus is first
        # (covers the common single-campus case) or, if none exist yet at
        # all, this app's original hardcoded default.
        campus = getattr(obj, 'campus', None) or Campus.objects.first()
        if campus:
            extra_context.update({
                'campus_map_center_lat': campus.center_latitude,
                'campus_map_center_lng': campus.center_longitude,
                'campus_default_zoom': campus.default_zoom,
            })
        else:
            extra_context.update({
                'campus_map_center_lat': FALLBACK_CENTER_LAT,
                'campus_map_center_lng': FALLBACK_CENTER_LNG,
                'campus_default_zoom': FALLBACK_ZOOM,
            })
        return extra_context

    def add_view(self, request, form_url='', extra_context=None):
        return super().add_view(request, form_url, self._with_campus_config(extra_context))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        return super().change_view(request, object_id, form_url, self._with_campus_config(extra_context, obj=obj))


@admin.register(Location)
class LocationAdmin(MapPickerAdminMixin, admin.ModelAdmin):
    change_form_template = 'admin/campus/location/change_form.html'
    list_display = ('name', 'campus', 'category', 'code', 'is_published', 'is_scannable', 'latitude', 'longitude', 'geofence_radius')
    list_filter = ('campus', 'category', 'is_published', 'is_scannable')
    search_fields = ('name', 'description', 'category', 'code')
    readonly_fields = ('qr_preview',)
    actions = ['print_qr_sheet']

    @admin.display(description='QR code')
    def qr_preview(self, obj):
        if not obj.pk:
            return 'Save the location first to generate its QR code.'

        png_url = reverse('admin:campus_location_qr_png', args=[obj.pk])
        return format_html(
            '<img src="{0}" alt="QR code for {1}" '
            'style="width:160px;height:160px;border:1px solid #ddd;padding:8px;background:#fff;" />'
            '<div style="margin-top:6px;"><a href="{0}?download=1">Download PNG</a></div>',
            png_url, obj.name,
        )

    @admin.action(description='Print QR sheet for selected locations')
    def print_qr_sheet(self, request, queryset):
        ids = ','.join(str(pk) for pk in queryset.values_list('pk', flat=True))
        return HttpResponseRedirect(
            reverse('admin:campus_location_print_qr_sheet') + f'?ids={ids}'
        )

    def get_urls(self):
        custom = [
            path('<int:object_id>/qr.png', self.admin_site.admin_view(self.qr_png_view), name='campus_location_qr_png'),
            path('print-qr-sheet/', self.admin_site.admin_view(self.print_qr_sheet_view), name='campus_location_print_qr_sheet'),
        ]
        return custom + super().get_urls()

    # GET .../<location_id>/qr.png[?download=1]
    def qr_png_view(self, request, object_id):
        location = get_object_or_404(Location, pk=object_id)
        url = qr.build_location_url(request, location)
        png_bytes = qr.qr_png_bytes(url)

        response = HttpResponse(png_bytes, content_type='image/png')
        if request.GET.get('download'):
            response['Content-Disposition'] = f'attachment; filename="{location.code}-qr.png"'
        return response

    # GET .../print-qr-sheet/?ids=1,2,3 - an A4, print-optimised sheet of
    # QR codes for the selected locations (see the "Print QR sheet for
    # selected locations" action above).
    def print_qr_sheet_view(self, request):
        raw_ids = request.GET.get('ids', '')
        ids = [int(v) for v in raw_ids.split(',') if v.strip().isdigit()]
        locations = Location.objects.filter(pk__in=ids).order_by('campus', 'name')

        context = {
            **self.admin_site.each_context(request),
            'title': 'Print QR sheet',
            'cells': [
                {'location': loc, 'qr_url': reverse('admin:campus_location_qr_png', args=[loc.pk])}
                for loc in locations
            ],
        }
        return render(request, 'campus/admin/qr_sheet.html', context)


@admin.register(GraphNode)
class GraphNodeAdmin(MapPickerAdminMixin, admin.ModelAdmin):
    change_form_template = 'admin/campus/graphnode/change_form.html'
    list_display = ('name', 'campus', 'latitude', 'longitude')
    list_filter = ('campus',)
    search_fields = ('name',)


@admin.register(GraphEdge)
class GraphEdgeAdmin(admin.ModelAdmin):
    change_form_template = 'admin/campus/graphedge/change_form.html'
    list_display = ('from_node', 'to_node', 'distance', 'campus')
    list_select_related = ('from_node', 'to_node', 'from_node__campus')
    list_filter = ('from_node__campus',)

    @admin.display(description='Campus')
    def campus(self, obj):
        return obj.from_node.campus

    def get_urls(self):
        custom = [
            path(
                'suggest-distance/',
                self.admin_site.admin_view(self.suggest_distance_view),
                name='campus_graphedge_suggest_distance',
            ),
        ]
        return custom + super().get_urls()

    # GET .../suggest-distance/?from_node_id=&to_node_id=
    # Suggests the straight-line (Haversine) distance between two nodes so
    # the admin doesn't have to measure by hand.
    def suggest_distance_view(self, request):
        try:
            from_node = GraphNode.objects.get(pk=request.GET.get('from_node_id'))
            to_node = GraphNode.objects.get(pk=request.GET.get('to_node_id'))
        except (GraphNode.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'message': 'Node not found.'}, status=404)

        meters = haversine.distance_meters(
            from_node.latitude, from_node.longitude, to_node.latitude, to_node.longitude
        )
        return JsonResponse({'distance': round(meters, 1)})


@admin.register(BoundaryPoint)
class BoundaryPointAdmin(admin.ModelAdmin):
    """
    Lets the admin define a campus's real outer boundary as a polygon (as
    opposed to Locations, which are single circular geofences). This
    isn't really row-by-row data, so the ordinary changelist is replaced
    with a dedicated click-to-add-vertex map editor per campus (mirrors
    the original Laravel admin/campus-boundary page - now one per campus
    instead of one global boundary).
    """

    list_display = ('campus', 'sequence_order', 'latitude', 'longitude')
    list_filter = ('campus',)
    ordering = ('campus', 'sequence_order')

    def get_urls(self):
        custom = [
            path('editor/<int:campus_id>/', self.admin_site.admin_view(self.editor_view), name='campus_boundarypoint_editor'),
            path('add-point/<int:campus_id>/', self.admin_site.admin_view(self.add_point_view), name='campus_boundarypoint_add_point'),
            path('remove-last-point/<int:campus_id>/', self.admin_site.admin_view(self.remove_last_point_view), name='campus_boundarypoint_remove_last_point'),
            path('clear-all/<int:campus_id>/', self.admin_site.admin_view(self.clear_all_view), name='campus_boundarypoint_clear_all'),
            path('import-points/<int:campus_id>/', self.admin_site.admin_view(self.import_points_view), name='campus_boundarypoint_import_points'),
        ]
        return custom + super().get_urls()

    # With one campus (the common case) this drops straight into that
    # campus's editor, same convenience as the public site's campus
    # picker. With several, it shows a "pick a campus" list instead of
    # the ordinary Django changelist - a flat list of boundary points
    # across every campus isn't useful to look at directly.
    def changelist_view(self, request, extra_context=None):
        campuses = list(Campus.objects.all())

        if len(campuses) == 1:
            return HttpResponseRedirect(
                reverse('admin:campus_boundarypoint_editor', args=[campuses[0].id])
            )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Campus Boundary',
            'campuses': campuses,
        }
        return render(request, 'campus/admin/boundary_campus_picker.html', context)

    def editor_view(self, request, campus_id):
        campus = get_object_or_404(Campus, pk=campus_id)
        points = list(BoundaryPoint.objects.filter(campus=campus).order_by('sequence_order'))

        context = {
            **self.admin_site.each_context(request),
            'title': f'Campus Boundary — {campus.name}',
            'campus': campus,
            'points': points,
            'campus_map_center_lat': campus.center_latitude,
            'campus_map_center_lng': campus.center_longitude,
            'initial_points_json': mark_safe(json.dumps(
                [{'lat': p.latitude, 'lng': p.longitude} for p in points]
            )),
        }
        return render(request, 'campus/admin/boundary_editor.html', context)

    # POST .../add-point/<campus_id>/ (body: { latitude, longitude })
    def add_point_view(self, request, campus_id):
        campus = get_object_or_404(Campus, pk=campus_id)
        data = json.loads(request.body or '{}')
        next_order = (
            BoundaryPoint.objects.filter(campus=campus).aggregate(Max('sequence_order'))['sequence_order__max']
            or -1
        ) + 1
        point = BoundaryPoint(
            campus=campus,
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            sequence_order=next_order,
        )
        try:
            point.full_clean()
        except (ValidationError, TypeError):
            return JsonResponse({'success': False, 'message': 'Invalid point.'}, status=422)

        point.save()
        return JsonResponse({'success': True, 'id': point.id, 'sequenceOrder': point.sequence_order})

    # POST .../remove-last-point/<campus_id>/
    def remove_last_point_view(self, request, campus_id):
        last = BoundaryPoint.objects.filter(campus_id=campus_id).order_by('-sequence_order').first()
        if last:
            last.delete()
        return JsonResponse({'success': True})

    # POST .../clear-all/<campus_id>/
    def clear_all_view(self, request, campus_id):
        BoundaryPoint.objects.filter(campus_id=campus_id).delete()
        return JsonResponse({'success': True})

    # POST .../import-points/<campus_id>/
    # body: { points: [{ latitude, longitude }, ...] } already in the
    # right order (the GeoJSON [lng,lat] -> {lat,lng} swap and
    # Polygon/LineString sniffing happens client-side in
    # static/campus/js/admin-boundary-editor.js). This REPLACES the whole
    # existing boundary of THIS campus with the imported points.
    def import_points_view(self, request, campus_id):
        campus = get_object_or_404(Campus, pk=campus_id)
        data = json.loads(request.body or '{}')
        raw_points = data.get('points')

        if not isinstance(raw_points, list) or len(raw_points) < 3:
            return JsonResponse({'message': 'At least 3 points are required.'}, status=422)

        new_points = []
        for p in raw_points:
            point = BoundaryPoint(campus=campus, latitude=p.get('latitude'), longitude=p.get('longitude'), sequence_order=0)
            try:
                point.full_clean(exclude=['sequence_order'])
            except (ValidationError, TypeError):
                return JsonResponse({'message': 'Invalid point data.'}, status=422)
            new_points.append(point)

        BoundaryPoint.objects.filter(campus=campus).delete()
        for i, point in enumerate(new_points):
            point.sequence_order = i
            point.save()

        return JsonResponse({'success': True, 'count': len(new_points)})


@admin.register(ScanEvent)
class ScanEventAdmin(admin.ModelAdmin):
    """Read-only analytics of QR-sticker scans - nothing here is ever
    created or edited by hand, only by /l/<code>/ and the in-app scanner."""

    list_display = ('code_raw', 'location', 'scanned_at')
    list_filter = ('location',)
    date_hierarchy = 'scanned_at'
    search_fields = ('code_raw', 'session_key')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class TourStopInline(admin.TabularInline):
    model = TourStop
    extra = 1
    autocomplete_fields = ['location']
    ordering = ['order']


@admin.register(Tour)
class TourAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    list_display = ('title', 'slug', 'duration_minutes', 'is_published', 'order', 'stop_count')
    list_filter = ('is_published',)
    search_fields = ('title', 'summary')
    inlines = [TourStopInline]

    @admin.display(description='Stops')
    def stop_count(self, obj):
        return obj.stops.count()


@admin.register(TourStop)
class TourStopAdmin(admin.ModelAdmin):
    """Flat list of every stop across every tour - editing a stop's order/
    note/location day-to-day is more natural from the Tour's own inline
    (see TourStopInline above); this is here for the odd bulk look-up."""

    list_display = ('tour', 'order', 'location')
    list_filter = ('tour',)
    autocomplete_fields = ['location']
    ordering = ['tour', 'order']
