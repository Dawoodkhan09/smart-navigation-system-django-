from django.urls import path

from . import api_views, views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/locations/search', api_views.location_search, name='api-location-search'),
    path('api/locations/<int:pk>', api_views.location_detail, name='api-location-detail'),
    path('api/locations', api_views.location_list, name='api-location-list'),
    path('api/navigation/route', api_views.navigation_route, name='api-navigation-route'),
    path('api/campus-boundary', api_views.campus_boundary, name='api-campus-boundary'),
]
