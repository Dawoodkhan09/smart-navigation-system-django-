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
]
