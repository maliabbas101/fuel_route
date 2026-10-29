from rest_framework import serializers

from .constants import TANK_GALLONS
from .geo import is_in_usa


class PointSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)

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
