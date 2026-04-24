from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import RouteQuery
from api.utils import haversine_km, km_to_miles


# Haversine unit tests (no DB, no mocking needed)
class HaversineTest(TestCase):
    def test_same_point_returns_zero(self):
        dist = haversine_km(34.0522, -118.2437, 34.0522, -118.2437)
        self.assertEqual(dist, 0.0)

    def test_lax_to_jfk_roughly_correct(self):
        # LAX to JFK is 3970 km straight line
        dist = haversine_km(33.9425, -118.4081, 40.6413, -73.7781)
        self.assertAlmostEqual(dist, 3970.0, delta=50.0)

    def test_km_to_miles(self):
        self.assertAlmostEqual(km_to_miles(1.0), 0.6214, places=3)

    def test_symmetry(self):
        # A->B and B->A should be the same
        d1 = haversine_km(34.05, -118.24, 40.71, -74.00)
        d2 = haversine_km(40.71, -74.00, 34.05, -118.24)
        self.assertEqual(d1, d2)


# shared mock data so tests dont have to repeat themselves
BEVERLY_CENTER = {
    "latitude": Decimal("34.075930"),
    "longitude": Decimal("-118.376090"),
    "formatted_address": "Beverly Center, 8500 Beverly Blvd, Los Angeles, CA 90048, USA",
    "place_id": "ChIJbeverly123",
}

LAX = {
    "latitude": Decimal("33.942501"),
    "longitude": Decimal("-118.408056"),
    "formatted_address": "Los Angeles International Airport (LAX), 1 World Way, Los Angeles, CA 90045, USA",
    "place_id": "ChIJlax456",
}


# Geocode endpoint tests
class GeocodeViewTest(APITestCase):
    @patch("api.utils.GoogleMapsService")
    def test_geocode_success(self, mock_svc):
        mock_svc.return_value.geocode_address.return_value = BEVERLY_CENTER

        resp = self.client.post("/api/geocode/", {"address": "beverly centre"}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["formatted_address"], BEVERLY_CENTER["formatted_address"])
        self.assertFalse(resp.data["cached"])
        self.assertIn("latitude", resp.data)
        self.assertIn("longitude", resp.data)

    @patch("api.utils.GoogleMapsService")
    def test_geocode_result_is_cached_on_second_call(self, mock_svc):
        mock_svc.return_value.geocode_address.return_value = BEVERLY_CENTER

        self.client.post("/api/geocode/", {"address": "beverly centre"}, format="json")
        resp = self.client.post("/api/geocode/", {"address": "beverly centre"}, format="json")

        self.assertTrue(resp.data["cached"])
        # google should only have been called once total
        self.assertEqual(mock_svc.return_value.geocode_address.call_count, 1)

    @patch("api.utils.GoogleMapsService")
    def test_geocode_not_found_returns_404(self, mock_svc):
        mock_svc.return_value.geocode_address.return_value = {}

        resp = self.client.post("/api/geocode/", {"address": "zzznotarealplace99999"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_geocode_empty_address_returns_400(self):
        resp = self.client.post("/api/geocode/", {"address": ""}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_geocode_missing_address_field_returns_400(self):
        resp = self.client.post("/api/geocode/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# Distance endpoint tests
class DistanceViewTest(APITestCase):
    @patch("api.utils.GoogleMapsService")
    def test_distance_returns_correct_fields(self, mock_svc):
        # first call for origin, second for destination
        mock_svc.return_value.geocode_address.side_effect = [BEVERLY_CENTER, LAX]

        resp = self.client.post(
            "/api/distance/",
            {"origin": "beverly centre", "destination": "LAX"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("origin", resp.data)
        self.assertIn("destination", resp.data)
        self.assertIn("distance_km", resp.data)
        self.assertIn("distance_miles", resp.data)

    @patch("api.utils.GoogleMapsService")
    def test_distance_value_is_reasonable(self, mock_svc):
        mock_svc.return_value.geocode_address.side_effect = [BEVERLY_CENTER, LAX]

        resp = self.client.post(
            "/api/distance/",
            {"origin": "beverly centre", "destination": "LAX"},
            format="json",
        )
        # beverly hills to LAX is roughly 15-20 km straight line
        dist = float(resp.data["distance_km"])
        self.assertGreater(dist, 5.0)
        self.assertLess(dist, 50.0)

    def test_same_origin_and_destination_returns_400(self):
        resp = self.client.post(
            "/api/distance/",
            {"origin": "LAX", "destination": "LAX"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("api.utils.GoogleMapsService")
    def test_distance_is_cached_on_second_call(self, mock_svc):
        mock_svc.return_value.geocode_address.side_effect = [BEVERLY_CENTER, LAX]

        self.client.post(
            "/api/distance/",
            {"origin": "beverly centre", "destination": "LAX"},
            format="json",
        )

        # on second call the location records exist so google wont be called again
        mock_svc.return_value.geocode_address.side_effect = [BEVERLY_CENTER, LAX]
        resp = self.client.post(
            "/api/distance/",
            {"origin": "beverly centre", "destination": "LAX"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(RouteQuery.objects.count(), 1)


# Coordinate distance endpoint tests
class CoordinateDistanceViewTest(APITestCase):
    def test_la_to_ny_distance(self):
        resp = self.client.post(
            "/api/distance/coordinates/",
            {"lat1": 34.0522, "lon1": -118.2437, "lat2": 40.7128, "lon2": -74.0060},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        dist = float(resp.data["distance_km"])
        self.assertAlmostEqual(dist, 3940.0, delta=100.0) # LA to NY is roughly 3940 km

    def test_invalid_latitude_returns_400(self):
        resp = self.client.post(
            "/api/distance/coordinates/",
            {"lat1": 999, "lon1": 0, "lat2": 0, "lon2": 0},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
