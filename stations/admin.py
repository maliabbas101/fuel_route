from django.contrib import admin
from .models import FuelPrice, Station


@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ("opis_id", "name", "city", "state")
    search_fields = ("name", "city", "=opis_id")
    list_filter = ("state",)


@admin.register(FuelPrice)
class FuelPriceAdmin(admin.ModelAdmin):
    list_display = ("station", "price_per_gallon", "rack_id", "source_row")
    list_select_related = ("station",)
