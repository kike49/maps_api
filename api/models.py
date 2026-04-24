import hashlib
from django.db import models


# DB-as-cache for geocode results, we store everything here to avoid repeat API calls. dedup key is sha256 of the normalized input
class Location(models.Model):
    address_input = models.CharField(max_length=500)
    address_hash = models.CharField(max_length=64, unique=True, db_index=True)
    formatted_address = models.CharField(max_length=500)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)   # DecimalField not float — floats accumulate rounding error on geo coords
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    place_id = models.CharField(max_length=300, null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # composite lat/lng index needed for the proximity lookup in reverse geocode
            models.Index(fields=["latitude", "longitude"], name="idx_location_latlng"),
        ]

    def __str__(self):
        return self.formatted_address

    @staticmethod
    def normalize(address):
        return address.strip().lower()

    @classmethod
    def make_hash(cls, address):
        return hashlib.sha256(cls.normalize(address).encode()).hexdigest()


# cached haversine result between two locations
class RouteQuery(models.Model):
    origin = models.ForeignKey(Location, related_name="outbound_routes", on_delete=models.CASCADE)
    destination = models.ForeignKey(Location, related_name="inbound_routes", on_delete=models.CASCADE)
    distance_km = models.DecimalField(max_digits=12, decimal_places=4)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("origin", "destination")]
        indexes = [
            models.Index(fields=["origin", "destination"], name="idx_route_origin_dest"),
        ]

    def __str__(self):
        return f"{self.origin} -> {self.destination} ({self.distance_km} km)"

    @classmethod
    def find(cls, origin, dest):
        # haversine is symmetric so A->B and B->A are the same distance — check both orderings before computing
        return (
            cls.objects
            .select_related("origin", "destination")
            .filter(
                models.Q(origin=origin, destination=dest) |
                models.Q(origin=dest, destination=origin)
            )
            .first()
        )
