from unittest import mock

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from trips.exceptions import RoutingError
from trips.routing import get_route

START = {"latitude": 30.0, "longitude": -97.0}
FINISH = {"latitude": 32.0, "longitude": -97.0}

ORS_RESPONSE = {
    "features": [
        {
            "geometry": {"type": "LineString", "coordinates": [[-97, 30], [-97, 32]]},
            "properties": {"summary": {"distance": 160934.4, "duration": 7200}},
        }
    ]
}


def ors_response(status=200, payload=ORS_RESPONSE):
    response = mock.Mock(status_code=status)
    response.json.return_value = payload
    response.raise_for_status.side_effect = (
        requests.HTTPError(response=response) if status >= 400 else None
    )
    return response


@override_settings(ORS_API_KEY="test-key")
@mock.patch("trips.routing.requests.post")
class GetRouteTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_returns_route_in_miles_and_caches_it(self, post):
        post.return_value = ors_response()

        route, cache_hit = get_route(START, FINISH)
        _, second_hit = get_route(START, FINISH)

        self.assertAlmostEqual(route["distance_miles"], 100)
        self.assertEqual(route["duration_seconds"], 7200)
        self.assertEqual((cache_hit, second_hit), (False, True))
        post.assert_called_once()
        self.assertEqual(
            post.call_args.kwargs["json"]["coordinates"], [[-97.0, 30.0], [-97.0, 32.0]]
        )

    def test_quota_errors_are_reported_as_unavailable(self, post):
        post.return_value = ors_response(status=429)

        with self.assertRaises(RoutingError) as error:
            get_route(START, FINISH)
        self.assertEqual(error.exception.status, 503)

    def test_other_http_errors_are_bad_gateway(self, post):
        post.return_value = ors_response(status=404)

        with self.assertRaises(RoutingError) as error:
            get_route(START, FINISH)
        self.assertEqual(error.exception.status, 502)

    def test_timeouts_are_reported_as_unavailable(self, post):
        post.side_effect = requests.Timeout()

        with self.assertRaises(RoutingError) as error:
            get_route(START, FINISH)
        self.assertEqual(error.exception.status, 503)

    def test_unexpected_payload_is_bad_gateway(self, post):
        post.return_value = ors_response(payload={"features": []})

        with self.assertRaises(RoutingError) as error:
            get_route(START, FINISH)
        self.assertEqual(error.exception.status, 502)

    @override_settings(ORS_API_KEY="")
    def test_missing_api_key_is_reported_without_calling_the_service(self, post):
        with self.assertRaises(RoutingError) as error:
            get_route(START, FINISH)
        self.assertEqual(error.exception.status, 503)
        post.assert_not_called()
