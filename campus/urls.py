from django.contrib.auth import views as auth_views
from django.urls import path

from . import api_views, views

urlpatterns = [
    # Web app login - this whole browser-based surface ('/' and
    # everything under c/<slug>/... except the visitor app below) is now
    # the admin's own tool, same account as /admin/.
    path('login/', auth_views.LoginView.as_view(template_name='campus/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

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

    # --- Visitor app (QR scan -> live map guide). Public, no login -
    # this is what QR-scanning visitors use, on their own phones. Not
    # campus-scoped by <campus_slug> in the URL the way the v1 routes
    # above are: `Location.code` is globally unique, and a visitor's
    # session is instead locked to one campus by whichever QR they
    # scanned (see views._lock_session_to_campus / resolve_default_campus
    # in api_views.py), which is what actually keeps them from browsing
    # another campus's data. ---
    path('app/', views.app_shell, name='app-shell'),
    path('app/scan/', views.app_scan, name='app-scan'),
    path('app/tour/<slug:slug>/', views.app_tour, name='app-tour'),
    path('app/c/<slug:campus_slug>/', views.campus_qr_landing, name='campus-qr-landing'),
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
