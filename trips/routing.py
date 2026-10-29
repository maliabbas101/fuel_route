import requests
from django.conf import settings
from django.core.cache import cache
from pyproj import Geod

from .constants import (
    METERS_PER_MILE,
    ORS_DIRECTIONS_URL,
    ORS_DISTANCE_LIMIT,
    ORS_NO_ROAD_NEAR_POINT,
    ORS_ROUTE_NOT_FOUND,
    ORS_SNAP_RADIUS_METERS,
    ROUTE_CACHE_SECONDS,
    ROUTING_TIMEOUT_SECONDS,
)
from .exceptions import RoutingError

GEOD = Geod(ellps="WGS84")


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
            json={
                "coordinates": coordinates,
                "instructions": False,
                "radiuses": [ORS_SNAP_RADIUS_METERS] * len(coordinates),
            },
            headers={"Authorization": settings.ORS_API_KEY},
            timeout=ROUTING_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        feature = response.json()["features"][0]
        summary = feature["properties"]["summary"]
        line = feature["geometry"]["coordinates"]
        return {
            "geometry": feature["geometry"],
            "distance_miles": summary["distance"] / METERS_PER_MILE,
            "duration_seconds": summary["duration"],
            "start_snap_miles": snap_miles(coordinates[0], line[0]),
            "finish_snap_miles": snap_miles(coordinates[-1], line[-1]),
        }
    except requests.HTTPError as exc:
        if exc.response.status_code == 429:
            raise RoutingError("Routing quota reached. Try again later.", 503)
        unroutable = unroutable_reason(exc.response)
        if unroutable:
            raise RoutingError(unroutable, 422)
        raise RoutingError("Routing service could not plan this route.")
    except (ValueError, KeyError, IndexError, TypeError):
        raise RoutingError("Routing service returned an invalid response.")
    except requests.RequestException:
        raise RoutingError("Routing service is unavailable.", 503)


def snap_miles(requested, routed):
    """Straight-line miles from a requested point to where the route begins or ends."""
    _, _, meters = GEOD.inv(*requested[:2], *routed[:2])
    return round(meters / METERS_PER_MILE, 2)


def unroutable_reason(response):
    """Explain an openrouteservice error caused by the trip's points, else None."""
    try:
        error = response.json()["error"]
        code, message = error["code"], error["message"]
    except (ValueError, KeyError, TypeError):
        return None

    if code == ORS_NO_ROAD_NEAR_POINT:
        point = "start" if "coordinate 0" in message else "finish"
        return (
            f"No public road within {ORS_SNAP_RADIUS_METERS:,} meters of the "
            f"{point} point. Move it onto or next to a drivable road."
        )
    if code == ORS_ROUTE_NOT_FOUND:
        return "No drivable route connects the start and finish points."
    if code == ORS_DISTANCE_LIMIT:
        return "The route is longer than the routing service's 6,000 km limit."
    return None
