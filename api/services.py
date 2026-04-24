import logging
import googlemaps

from decimal import Decimal

from django.conf import settings

logger = logging.getLogger(__name__)


class GoogleMapsService:
    """
    Thin wrapper around the googlemaps python client.
    Docs: https://googlemaps.github.io/google-maps-services-python/docs/index.html
    """

    def __init__(self):
        self.client = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

    def geocode_address(self, address):
        """
        Geocode a free-text address to lat/lng + formatted address.
        Returns a dict on success or empty dict if nothing found / on error.

        Response structure from Google:
        https://developers.google.com/maps/documentation/geocoding/requests-geocoding
        """
        try:
            if not address:
                return {}

            results = self.client.geocode(address)

            if results:
                loc = results[0]["geometry"]["location"]
                formatted = results[0]["formatted_address"]
                logger.info(f"Geocode success: {formatted}")
                return {
                    "latitude": Decimal(str(loc["lat"])),
                    "longitude": Decimal(str(loc["lng"])),
                    "formatted_address": formatted,
                    "place_id": results[0].get("place_id"),
                }
            else:
                logger.info(f"No geocode results for: {address}")
                return {}

        except Exception as e:
            logger.error(f"Geocoding failed for '{address}': {e}")
            return {}

    def reverse_geocode(self, latitude, longitude):
        """
        Convert lat/lng coordinates to a human-readable address.
        Returns a dict on success or empty dict on failure.

        Response structure:
        https://developers.google.com/maps/documentation/geocoding/requests-reverse-geocoding
        """
        try:
            results = self.client.reverse_geocode((float(latitude), float(longitude)))

            if results:
                formatted = results[0]["formatted_address"]
                logger.info(f"Reverse geocode success: {formatted}")
                return {
                    "latitude": Decimal(str(latitude)),
                    "longitude": Decimal(str(longitude)),
                    "formatted_address": formatted,
                    "place_id": results[0].get("place_id"),
                }
            else:
                logger.info(f"No reverse geocode results for ({latitude}, {longitude})")
                return {}

        except Exception as e:
            logger.error(f"Reverse geocoding failed for ({latitude}, {longitude}): {e}")
            return {}
