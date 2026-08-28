import json

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Max
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import path, reverse
from django.utils.safestring import mark_safe

from .models import BoundaryPoint, GraphEdge, GraphNode, Location
from .services import haversine


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

    def _with_campus_config(self, extra_context=None):
        extra_context = dict(extra_context or {})
        extra_context.update({
            'campus_map_center_lat': settings.CAMPUS_MAP_CENTER_LAT,
            'campus_map_center_lng': settings.CAMPUS_MAP_CENTER_LNG,
            'campus_default_zoom': settings.CAMPUS_DEFAULT_ZOOM,
        })
        return extra_context

    def add_view(self, request, form_url='', extra_context=None):
        return super().add_view(request, form_url, self._with_campus_config(extra_context))

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return super().change_view(request, object_id, form_url, self._with_campus_config(extra_context))


@admin.register(Location)
class LocationAdmin(MapPickerAdminMixin, admin.ModelAdmin):
    change_form_template = 'admin/campus/location/change_form.html'
    list_display = ('name', 'category', 'latitude', 'longitude', 'geofence_radius')
    list_filter = ('category',)
    search_fields = ('name', 'description', 'category')
    ordering = ('name',)


@admin.register(GraphNode)
class GraphNodeAdmin(MapPickerAdminMixin, admin.ModelAdmin):
    change_form_template = 'admin/campus/graphnode/change_form.html'
    list_display = ('name', 'latitude', 'longitude')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(GraphEdge)
class GraphEdgeAdmin(admin.ModelAdmin):
    change_form_template = 'admin/campus/graphedge/change_form.html'
    list_display = ('from_node', 'to_node', 'distance')
    list_select_related = ('from_node', 'to_node')

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
    Lets the admin define the campus's real outer boundary as a polygon
    (as opposed to Locations, which are single circular geofences). This
    isn't really row-by-row data, so the ordinary changelist is replaced
    with a dedicated click-to-add-vertex map editor (mirrors the original
    Laravel admin/campus-boundary page).
    """

    list_display = ('sequence_order', 'latitude', 'longitude')
    ordering = ('sequence_order',)

    def get_urls(self):
        custom = [
            path('editor/', self.admin_site.admin_view(self.editor_view), name='campus_boundarypoint_editor'),
            path('add-point/', self.admin_site.admin_view(self.add_point_view), name='campus_boundarypoint_add_point'),
            path('remove-last-point/', self.admin_site.admin_view(self.remove_last_point_view), name='campus_boundarypoint_remove_last_point'),
            path('clear-all/', self.admin_site.admin_view(self.clear_all_view), name='campus_boundarypoint_clear_all'),
            path('import-points/', self.admin_site.admin_view(self.import_points_view), name='campus_boundarypoint_import_points'),
        ]
        return custom + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('admin:campus_boundarypoint_editor'))

    def editor_view(self, request):
        points = list(BoundaryPoint.objects.order_by('sequence_order'))

        if points:
            center_lat = sum(p.latitude for p in points) / len(points)
            center_lng = sum(p.longitude for p in points) / len(points)
        else:
            center_lat = settings.CAMPUS_MAP_CENTER_LAT
            center_lng = settings.CAMPUS_MAP_CENTER_LNG

        context = {
            **self.admin_site.each_context(request),
            'title': 'Campus Boundary',
            'points': points,
            'campus_map_center_lat': center_lat,
            'campus_map_center_lng': center_lng,
            'initial_points_json': mark_safe(json.dumps(
                [{'lat': p.latitude, 'lng': p.longitude} for p in points]
            )),
        }
        return render(request, 'campus/admin/boundary_editor.html', context)

    # POST .../add-point/ (body: { latitude, longitude })
    def add_point_view(self, request):
        data = json.loads(request.body or '{}')
        next_order = (BoundaryPoint.objects.aggregate(Max('sequence_order'))['sequence_order__max'] or -1) + 1
        point = BoundaryPoint(
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

    # POST .../remove-last-point/
    def remove_last_point_view(self, request):
        last = BoundaryPoint.objects.order_by('-sequence_order').first()
        if last:
            last.delete()
        return JsonResponse({'success': True})

    # POST .../clear-all/
    def clear_all_view(self, request):
        BoundaryPoint.objects.all().delete()
        return JsonResponse({'success': True})

    # POST .../import-points/
    # body: { points: [{ latitude, longitude }, ...] } already in the
    # right order (the GeoJSON [lng,lat] -> {lat,lng} swap and
    # Polygon/LineString sniffing happens client-side in
    # static/campus/js/admin-boundary-editor.js). This REPLACES the whole
    # existing boundary with the imported points.
    def import_points_view(self, request):
        data = json.loads(request.body or '{}')
        raw_points = data.get('points')

        if not isinstance(raw_points, list) or len(raw_points) < 3:
            return JsonResponse({'message': 'At least 3 points are required.'}, status=422)

        new_points = []
        for p in raw_points:
            point = BoundaryPoint(latitude=p.get('latitude'), longitude=p.get('longitude'), sequence_order=0)
            try:
                point.full_clean(exclude=['sequence_order'])
            except (ValidationError, TypeError):
                return JsonResponse({'message': 'Invalid point data.'}, status=422)
            new_points.append(point)

        BoundaryPoint.objects.all().delete()
        for i, point in enumerate(new_points):
            point.sequence_order = i
            point.save()

        return JsonResponse({'success': True, 'count': len(new_points)})
