import math

from api.models import Location
from api.services import GoogleMapsService


def haversine_km(lat1, lon1, lat2, lon2):
    """
    Great-circle distance between two points on Earth using the Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371.0  # earth radius in km

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return round(R * c, 4)


def km_to_miles(km):
    return round(float(km) * 0.621371, 4)    # 0.621371 miles in a km


def get_or_create_location(address):
    address_hash = Location.make_hash(address)
    try:
        return Location.objects.get(address_hash=address_hash), True
    except Location.DoesNotExist:
        pass

    maps = GoogleMapsService()
    result = maps.geocode_address(address)
    if not result:
        return None, False

    location, _ = Location.objects.get_or_create(
        address_hash=address_hash,
        defaults={
            "address_input": address,
            "formatted_address": result["formatted_address"],
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            "place_id": result.get("place_id"),
        },
    )
    return location, False
