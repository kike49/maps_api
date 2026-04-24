from django.urls import path
from .views import GeocodeView, ReverseGeocodeView, DistanceView, CoordinateDistanceView


urlpatterns = [
    path("geocode/", GeocodeView.as_view(), name="geocode"),
    path("reverse-geocode/", ReverseGeocodeView.as_view(), name="reverse-geocode"),
    path("distance/", DistanceView.as_view(), name="distance"),
    path("distance/coordinates/", CoordinateDistanceView.as_view(), name="distance-coordinates"),
]
