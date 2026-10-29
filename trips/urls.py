from django.urls import path

from .views import plan_trip, trip_map

urlpatterns = [
    path("map/", trip_map, name="trip-map"),
    path("plan/", plan_trip, name="plan-trip"),
]