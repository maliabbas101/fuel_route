from functools import lru_cache

import numpy as np
import shapely

from stations.models import Station

from .constants import (
    CITY_CORRIDOR_METERS,
    EXACT_CORRIDOR_METERS,
    ROUTE_SIMPLIFY_METERS,
)
from .geo import meters_projection


@lru_cache(maxsize=1)
def load_stations():
    """All priced stations with coordinates, loaded once per process."""
    stations = [
        {
            "id": station.opis_id,
            "name": station.name,
            "latitude": float(station.latitude),
            "longitude": float(station.longitude),
            "location_precision": "exact" if station.has_exact_location else "city",
            "price": float(station.average_price),
        }
        for station in Station.objects.priced_with_coordinates()
    ]
    coordinates = np.array([[s["longitude"], s["latitude"]] for s in stations])
    return stations, coordinates


def find_route_stations(geometry, distance_miles):
    """Stations near the route, each with its mile along the route."""
    route = np.array(geometry["coordinates"])[:, :2]
    to_meters = meters_projection(*route[len(route) // 2])

    line = shapely.LineString(np.column_stack(to_meters(*route.T))).simplify(
        ROUTE_SIMPLIFY_METERS, preserve_topology=False
    )
    if line.length == 0:
        return []
    corridor = line.buffer(CITY_CORRIDOR_METERS)
    shapely.prepare(corridor)

    stations, coordinates = load_stations()
    points = shapely.points(np.column_stack(to_meters(*coordinates.T)))

    inside = np.flatnonzero(shapely.contains(corridor, points))
    distances = shapely.distance(line, points[inside])
    miles = (
        shapely.line_locate_point(line, points[inside]) / line.length * distance_miles
    )

    candidates = []
    for i, distance, mile in zip(inside, distances, miles):
        station = stations[i]
        if (
            station["location_precision"] == "exact"
            and distance > EXACT_CORRIDOR_METERS
        ):
            continue
        if mile < distance_miles:
            candidates.append({**station, "mile": float(mile)})
    return candidates
