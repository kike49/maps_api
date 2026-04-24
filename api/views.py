import logging
from decimal import Decimal

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiExample

from .models import Location, RouteQuery
from .serializers import (
    GeocodeRequestSerializer,
    ReverseGeocodeRequestSerializer,
    DistanceRequestSerializer,
    CoordinateDistanceRequestSerializer,
    LocationSerializer,
)
from .services import GoogleMapsService
from .utils import get_or_create_location, haversine_km, km_to_miles

logger = logging.getLogger(__name__)


class GeocodeView(APIView):
    # POST /api/geocode/ — free-text address -> lat/lng + formatted address

    @extend_schema(
        request=GeocodeRequestSerializer,
        responses={200: LocationSerializer},
        examples=[
            OpenApiExample(
                "Beverly Center",
                value={"address": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA"},
                request_only=True,
            ),
            OpenApiExample(
                "LAX",
                value={"address": "Los Angeles International Airport, CA"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = GeocodeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        address = serializer.validated_data["address"]
        location, cached = get_or_create_location(address)

        if not location:
            return Response(
                {"error": "Address not found. Please try a more specific address."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = LocationSerializer(location).data
        data["cached"] = cached
        return Response(data, status=status.HTTP_200_OK)


class ReverseGeocodeView(APIView):
    # POST /api/reverse-geocode/ — lat/lng -> formatted address

    @extend_schema(
        request=ReverseGeocodeRequestSerializer,
        responses={200: LocationSerializer},
        examples=[
            OpenApiExample(
                "Beverly Center coords",
                value={"latitude": 34.075930, "longitude": -118.376090},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = ReverseGeocodeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lat = serializer.validated_data["latitude"]
        lng = serializer.validated_data["longitude"]

        # 4 decimal places = ~11m tolerance for cached DB lookup to avoid constants API calls
        tolerance = Decimal("0.0001")
        cached = Location.objects.filter(
            latitude__gte=lat - tolerance,
            latitude__lte=lat + tolerance,
            longitude__gte=lng - tolerance,
            longitude__lte=lng + tolerance,
        ).first()

        if cached:
            data = LocationSerializer(cached).data
            data["cached"] = True
            return Response(data, status=status.HTTP_200_OK)

        # No DB result, call API
        maps = GoogleMapsService()
        result = maps.reverse_geocode(lat, lng)
        if not result:
            return Response({"error": "No address found for these coordinates."}, status=status.HTTP_404_NOT_FOUND)

        # Save result
        address_hash = Location.make_hash(result["formatted_address"])
        location, _ = Location.objects.get_or_create(
            address_hash=address_hash,
            defaults={
                "address_input": result["formatted_address"],
                "formatted_address": result["formatted_address"],
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "place_id": result.get("place_id"),
            },
        )

        data = LocationSerializer(location).data
        data["cached"] = False
        return Response(data, status=status.HTTP_200_OK)


class DistanceView(APIView):
    # POST /api/distance/ — two free-text addresses -> straight-line haversine distance

    @extend_schema(
        request=DistanceRequestSerializer,
        responses={200: LocationSerializer},
        examples=[
            OpenApiExample(
                "Beverly Center to LAX",
                value={"origin": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA", "destination": "Los Angeles International Airport, CA"},
                request_only=True,
            ),
            OpenApiExample(
                "New York to Los Angeles",
                value={"origin": "New York, NY", "destination": "Los Angeles, CA"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = DistanceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        origin_input = serializer.validated_data["origin"]
        dest_input = serializer.validated_data["destination"]

        origin_loc, _ = get_or_create_location(origin_input)
        if not origin_loc:
            return Response({"error": f"Could not geocode origin: '{origin_input}'"}, status=status.HTTP_404_NOT_FOUND)

        dest_loc, _ = get_or_create_location(dest_input)
        if not dest_loc:
            return Response({"error": f"Could not geocode destination: '{dest_input}'"}, status=status.HTTP_404_NOT_FOUND)

        # checks both A->B and B->A — same distance, no reason to store or compute twice
        route = RouteQuery.find(origin_loc, dest_loc)

        # Does not exist, compute and save
        if not route:
            dist_km = haversine_km(
                origin_loc.latitude,
                origin_loc.longitude,
                dest_loc.latitude,
                dest_loc.longitude,
            )
            route, _ = RouteQuery.objects.get_or_create(
                origin=origin_loc,
                destination=dest_loc,
                defaults={"distance_km": Decimal(str(dist_km))},
            )

        return Response(
            {
                "origin": LocationSerializer(origin_loc).data,
                "destination": LocationSerializer(dest_loc).data,
                "distance_km": route.distance_km,
                "distance_miles": km_to_miles(route.distance_km),
            },
            status=status.HTTP_200_OK,
        )


class CoordinateDistanceView(APIView):
    # POST /api/distance/coordinates/ — raw lat/lng pairs -> haversine distance, no geocoding

    @extend_schema(
        request=CoordinateDistanceRequestSerializer,
        responses={200: CoordinateDistanceRequestSerializer},
        examples=[
            OpenApiExample(
                "Beverly Center to LAX",
                value={"lat1": 34.075930, "lon1": -118.376090, "lat2": 33.942501, "lon2": -118.408056},
                request_only=True,
            ),
            OpenApiExample(
                "LA to New York",
                value={"lat1": 34.0522, "lon1": -118.2437, "lat2": 40.7128, "lon2": -74.0060},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = CoordinateDistanceRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        d = serializer.validated_data
        dist_km = haversine_km(d["lat1"], d["lon1"], d["lat2"], d["lon2"])

        return Response({"distance_km": dist_km, "distance_miles": km_to_miles(dist_km)}, status=status.HTTP_200_OK)
