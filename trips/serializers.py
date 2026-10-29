from rest_framework import serializers

from .constants import CONTIGUOUS_USA_BOUNDS as BOUNDS
from .constants import TANK_GALLONS
from .geo import is_in_usa

LATITUDE_RANGE = (
    f"Latitude must be between {BOUNDS['min_latitude']} and "
    f"{BOUNDS['max_latitude']} (the contiguous USA)."
)
LONGITUDE_RANGE = (
    f"Longitude must be between {BOUNDS['min_longitude']} and "
    f"{BOUNDS['max_longitude']} (the contiguous USA). "
    "Western longitudes are negative: enter 81.8° W as -81.8."
)


class PointSerializer(serializers.Serializer):
    latitude = serializers.FloatField(
        min_value=BOUNDS["min_latitude"],
        max_value=BOUNDS["max_latitude"],
        error_messages={"min_value": LATITUDE_RANGE, "max_value": LATITUDE_RANGE},
    )
    longitude = serializers.FloatField(
        min_value=BOUNDS["min_longitude"],
        max_value=BOUNDS["max_longitude"],
        error_messages={"min_value": LONGITUDE_RANGE, "max_value": LONGITUDE_RANGE},
    )

    def validate(self, attrs):
        if not is_in_usa(attrs["longitude"], attrs["latitude"]):
            raise serializers.ValidationError("Location must be within the USA.")
        return attrs


class TripRequestSerializer(serializers.Serializer):
    start = PointSerializer()
    finish = PointSerializer()
    initial_fuel_gallons = serializers.FloatField(
        min_value=0, max_value=TANK_GALLONS, default=TANK_GALLONS
    )
