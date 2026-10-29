from django.db import models


class StationQuerySet(models.QuerySet):
    def priced_with_coordinates(self):
        return self.filter(
            latitude__isnull=False, longitude__isnull=False, prices__isnull=False
        ).annotate(average_price=models.Avg("prices__price_per_gallon"))


class Station(models.Model):
    class CoordinateSource(models.TextChoices):
        STATION = "station", "Exact station (OpenStreetMap)"
        CENSUS_PLACE = "census_place", "City center (Census place)"
        CENSUS_COUSUB = "census_cousub", "Town center (Census county subdivision)"
        GEONAMES = "geonames", "Community center (GeoNames)"

    opis_id = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, db_index=True)
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=11, decimal_places=7, null=True, blank=True
    )
    coordinate_source = models.CharField(
        max_length=20, choices=CoordinateSource.choices, blank=True
    )

    objects = StationQuerySet.as_manager()

    @property
    def has_exact_location(self):
        return self.coordinate_source == self.CoordinateSource.STATION

    def __str__(self):
        return f"{self.name} ({self.city}, {self.state})"


class FuelPrice(models.Model):
    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="prices"
    )
    source_row = models.PositiveIntegerField(unique=True)
    source_name = models.CharField(max_length=255)
    rack_id = models.PositiveIntegerField()
    price_per_gallon = models.DecimalField(max_digits=12, decimal_places=8)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price_per_gallon__gt=0), name="fuel_price_positive"
            )
        ]
