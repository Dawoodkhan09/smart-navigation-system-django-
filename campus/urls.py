from django.urls import path

from . import api_views, views

urlpatterns = [
    # '/' picks a campus - auto-redirects straight into it when there's
    # only one (today's case), shows a chooser once there's more than one.
    path('', views.campus_picker, name='campus-picker'),

    path('c/<slug:campus_slug>/', views.locations_tree, name='tree'),
    path('c/<slug:campus_slug>/map/', views.map_view, name='map'),
    path('c/<slug:campus_slug>/api/locations/search', api_views.location_search, name='api-location-search'),
    path('c/<slug:campus_slug>/api/locations/<int:pk>', api_views.location_detail, name='api-location-detail'),
    path('c/<slug:campus_slug>/api/locations', api_views.location_list, name='api-location-list'),
    path('c/<slug:campus_slug>/api/navigation/route', api_views.navigation_route, name='api-navigation-route'),
    path('c/<slug:campus_slug>/api/campus-boundary', api_views.campus_boundary, name='api-campus-boundary'),

    # --- Visitor app (QR scan -> live map guide). No <campus_slug> here:
    # `Location.code` is globally unique, and these pages/endpoints
    # otherwise default to the first Campus (see api_views.resolve_default_campus)
    # until the visitor app grows its own campus picker. ---
    path('app/', views.app_shell, name='app-shell'),
    path('app/scan/', views.app_scan, name='app-scan'),
    path('app/tour/<slug:slug>/', views.app_tour, name='app-tour'),
    path('l/<slug:code>/', views.location_qr_landing, name='location-qr-landing'),

    path('api/v2/locations/', api_views.v2_location_list, name='api-v2-locations'),
    path('api/v2/locations/<slug:code>/', api_views.v2_location_detail, name='api-v2-location-detail'),
    path('api/v2/route/', api_views.v2_route, name='api-v2-route'),
    path('api/v2/nearby/', api_views.v2_nearby, name='api-v2-nearby'),
    path('api/v2/scan/', api_views.v2_scan, name='api-v2-scan'),
    path('api/v2/boundary/', api_views.v2_boundary, name='api-v2-boundary'),
    path('api/v2/tours/', api_views.v2_tour_list, name='api-v2-tours'),
    path('api/v2/tours/<slug:slug>/', api_views.v2_tour_detail, name='api-v2-tour-detail'),
]
