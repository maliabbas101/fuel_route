from django.contrib import admin
from django.urls import include, path

from trips.views import home

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("api/trips/", include("trips.urls")),
]
