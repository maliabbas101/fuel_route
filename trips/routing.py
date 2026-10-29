import requests
from django.conf import settings
from django.core.cache import cache

from .constants import (
    METERS_PER_MILE,
    ORS_DIRECTIONS_URL,
    ROUTE_CACHE_SECONDS,
    ROUTING_TIMEOUT_SECONDS,
)
from .exceptions import RoutingError


def get_route(start, finish):
    """Return (route, cache_hit) for {"latitude", "longitude"} points."""
    coordinates = [[p["longitude"], p["latitude"]] for p in (start, finish)]
    cache_key = "route:" + ";".join(f"{lon},{lat}" for lon, lat in coordinates)
    route = cache.get(cache_key)
    if route is not None:
        return route, True

    route = fetch_route(coordinates)
    cache.set(cache_key, route, timeout=ROUTE_CACHE_SECONDS)
    return route, False


def fetch_route(coordinates):
    if not settings.ORS_API_KEY:
        raise RoutingError("Routing API key is not configured.", 503)

    try:
        response = requests.post(
            ORS_DIRECTIONS_URL,
            json={"coordinates": coordinates, "instructions": False},
            headers={"Authorization": settings.ORS_API_KEY},
            timeout=ROUTING_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        feature = response.json()["features"][0]
        summary = feature["properties"]["summary"]
        return {
            "geometry": feature["geometry"],
            "distance_miles": summary["distance"] / METERS_PER_MILE,
            "duration_seconds": summary["duration"],
        }
    except requests.HTTPError as exc:
        if exc.response.status_code == 429:
            raise RoutingError("Routing quota reached. Try again later.", 503)
        raise RoutingError("Routing service could not plan this route.")
    except (ValueError, KeyError, IndexError, TypeError):
        raise RoutingError("Routing service returned an invalid response.")
    except requests.RequestException:
        raise RoutingError("Routing service is unavailable.", 503)
