from django.urls import path

from .views import TripPlanView, trip_map

urlpatterns = [
    path("map/", trip_map, name="trip-map"),
    path("plan/", TripPlanView.as_view(), name="plan-trip"),
]
