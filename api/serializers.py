from rest_framework import serializers
from .models import Location


class GeocodeRequestSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=500, allow_blank=False, trim_whitespace=True)


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["formatted_address", "latitude", "longitude", "place_id"]


class ReverseGeocodeRequestSerializer(serializers.Serializer):
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)


class DistanceRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=500, trim_whitespace=True)
    destination = serializers.CharField(max_length=500, trim_whitespace=True)

    def validate(self, data):
        if data["origin"].lower() == data["destination"].lower():
            raise serializers.ValidationError("Origin and destination cannot be the same address.")
        return data


class CoordinateDistanceRequestSerializer(serializers.Serializer):
    lat1 = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    lon1 = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)
    lat2 = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-90, max_value=90)
    lon2 = serializers.DecimalField(max_digits=9, decimal_places=6, min_value=-180, max_value=180)


