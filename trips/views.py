import json
import math
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


def validate_location(value):
    if not isinstance(value, dict):
        raise ValueError("Each location must contain latitude and longitude.")

    latitude = value.get("latitude")
    longitude = value.get("longitude")

    for coordinate in (latitude, longitude):
        if (
            isinstance(coordinate, bool)
            or not isinstance(coordinate, (int, float))
            or not math.isfinite(coordinate)
        ):
            raise ValueError("Coordinates must be finite numbers.")

    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")

    return [longitude, latitude]


@csrf_exempt
@require_POST
def plan_trip(request):
    try:
        payload = json.loads(request.body)

        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")

        start = validate_location(payload.get("start"))
        finish = validate_location(payload.get("finish"))

    except (ValueError, UnicodeDecodeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    api_key = os.environ.get("ORS_API_KEY")

    if not api_key:
        return JsonResponse(
            {"error": "Routing API key is not configured."},
            status=503,
        )

    routing_request = Request(
        "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
        data=json.dumps({
            "coordinates": [start, finish],
            "instructions": False,
        }).encode("utf-8"),
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/geo+json",
        },
        method="POST",
    )

    try:
        with urlopen(routing_request, timeout=20) as response:
            route_data = json.load(response)

    except HTTPError as exc:
        if exc.code == 429:
            return JsonResponse(
                {"error": "Routing service quota reached. Try again later."},
                status=503,
            )

        return JsonResponse(
            {"error": "Routing service could not complete the request."},
            status=502,
        )

    except (URLError, TimeoutError):
        return JsonResponse(
            {"error": "Routing service is unavailable or timed out."},
            status=503,
        )

    except (ValueError, UnicodeError):
        return JsonResponse(
            {"error": "Routing service returned an invalid response."},
            status=502,
        )

    try:
        route = route_data["features"][0]
        distance_meters = route["properties"]["summary"]["distance"]
        duration_seconds = route["properties"]["summary"]["duration"]
        geometry = route["geometry"]

        distance_miles = distance_meters / 1609.344
        fuel_consumed = distance_miles / 10

    except (KeyError, IndexError, TypeError):
        return JsonResponse(
            {"error": "Routing service returned an unexpected route format."},
            status=502,
        )

    return JsonResponse({
        "distance_miles": round(distance_miles, 2),
        "duration_seconds": duration_seconds,
        "fuel_consumed_gallons": round(fuel_consumed, 2),
        "route_geojson": geometry,
    })