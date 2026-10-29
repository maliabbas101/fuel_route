from unittest import mock

from django.urls import reverse
from rest_framework.test import APITestCase

from stations.models import FuelPrice, Station
from trips.exceptions import RoutingError
from trips.stations import load_stations

ROUTE = {
    "geometry": {
        "type": "LineString",
        "coordinates": [[-97.0, 30.0 + i / 100] for i in range(501)],
    },
    "distance_miles": 345.0,
    "duration_seconds": 18000,
}


def add_station(opis_id, latitude, price, longitude=-97.0):
    station = Station.objects.create(
        opis_id=opis_id,
        name=f"Station {opis_id}",
        address="I-35",
        city="Test",
        state="TX",
        latitude=latitude,
        longitude=longitude,
        coordinate_source=Station.CoordinateSource.CENSUS_PLACE,
    )
    FuelPrice.objects.create(
        station=station,
        source_row=opis_id,
        source_name=station.name,
        rack_id=1,
        price_per_gallon=price,
    )


@mock.patch("trips.planner.get_route", return_value=(ROUTE, False))
class TripPlanApiTests(APITestCase):
    url = reverse("plan-trip")
    body = {
        "start": {"latitude": 30.0, "longitude": -97.0},
        "finish": {"latitude": 35.0, "longitude": -97.0},
        "initial_fuel_gallons": 0,
    }

    def setUp(self):
        load_stations.cache_clear()
        add_station(1, 30.0, "3.50")
        add_station(2, 32.0, "3.00")
        add_station(3, 34.0, "3.20")
        add_station(4, 32.0, "1.00", longitude=-90.0)

    def tearDown(self):
        load_stations.cache_clear()

    def test_plans_fuel_stops_along_the_route(self, get_route):
        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["candidate_station_count"], 3)
        self.assertEqual([s["id"] for s in data["fuel_stops"]], [1, 2])
        self.assertAlmostEqual(
            sum(s["cost_usd"] for s in data["fuel_stops"]),
            data["fuel_purchase_cost_usd"],
        )
        self.assertIn("route_geojson", data)

    def test_defaults_to_a_full_tank(self, get_route):
        body = {**self.body}
        del body["initial_fuel_gallons"]

        response = self.client.post(self.url, body, format="json")

        self.assertEqual(response.json()["fuel_stops"], [])

    def test_rejects_locations_outside_the_usa(self, get_route):
        body = {**self.body, "start": {"latitude": 51.5, "longitude": -0.12}}

        response = self.client.post(self.url, body, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("start", response.json())
        get_route.assert_not_called()

    def test_rejects_invalid_input(self, get_route):
        for body in (
            {**self.body, "initial_fuel_gallons": 60},
            {**self.body, "finish": {"latitude": "north"}},
            {"start": self.body["start"]},
        ):
            with self.subTest(body=body):
                response = self.client.post(self.url, body, format="json")
                self.assertEqual(response.status_code, 400)

    def test_rejects_malformed_json(self, get_route):
        response = self.client.post(
            self.url, "not json", content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)

    def test_reports_routing_errors(self, get_route):
        get_route.side_effect = RoutingError("Routing service is unavailable.", 503)

        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Routing service is unavailable.")

    def test_reports_when_no_plan_is_possible(self, get_route):
        Station.objects.filter(opis_id=1).delete()

        response = self.client.post(self.url, self.body, format="json")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"], "NO_FEASIBLE_FUEL_PLAN")
        self.assertIn("route_geojson", response.json())

    def test_only_accepts_post(self, get_route):
        self.assertEqual(self.client.get(self.url).status_code, 405)
