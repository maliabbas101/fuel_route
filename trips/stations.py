import numpy as np
import shapely
from django.db.models import Avg
from pyproj import CRS, Transformer

from stations.models import Station

# Exact station points must sit beside the route. City-center points can be a
# few miles from the highway exit the station is actually on.
EXACT_CORRIDOR_METERS = 1600
CITY_CORRIDOR_METERS = 8000


def find_route_stations(geometry, distance_miles):
    coordinates = geometry["coordinates"]

    # Use a local projection centered on the route.
    center = coordinates[len(coordinates) // 2]

    projection = CRS.from_proj4(
        f"+proj=aeqd +lat_0={center[1]} +lon_0={center[0]} "
        "+datum=WGS84 +units=m"
    )

    transformer = Transformer.from_crs(
        "EPSG:4326",
        projection,
        always_xy=True,
    )

    route = np.asarray([point[:2] for point in coordinates], dtype=float)
    projected = np.column_stack(transformer.transform(route[:, 0], route[:, 1]))

    starts, ends = projected[:-1], projected[1:]
    segment_lengths = np.hypot(*(ends - starts).T)
    route_length = segment_lengths.sum()

    if route_length == 0:
        return []

    segment_offsets = np.concatenate(([0.0], np.cumsum(segment_lengths)[:-1]))
    segments = shapely.linestrings(np.stack((starts, ends), axis=1))

    # Skip stations outside the route's bounding box before measuring.
    margin = CITY_CORRIDOR_METERS / 111_000 * 1.5
    south, north = route[:, 1].min() - margin, route[:, 1].max() + margin
    lon_margin = margin / max(np.cos(np.radians(max(abs(south), abs(north)))), 0.1)
    west, east = route[:, 0].min() - lon_margin, route[:, 0].max() + lon_margin

    stations = list(
        Station.objects.filter(
            latitude__range=(south, north),
            longitude__range=(west, east),
            prices__isnull=False,
        )
        .annotate(route_price=Avg("prices__price_per_gallon"))
        .values("opis_id", "name", "latitude", "longitude",
                "coordinate_source", "route_price")
    )

    if not stations:
        return []

    longitudes = np.array([float(s["longitude"]) for s in stations])
    latitudes = np.array([float(s["latitude"]) for s in stations])
    xy = np.column_stack(transformer.transform(longitudes, latitudes))

    # Find each station's nearest route segment with a spatial index.
    (station_index, segment_index), distances = shapely.STRtree(
        segments).query_nearest(
            shapely.points(xy),
            max_distance=CITY_CORRIDOR_METERS,
            return_distance=True,
            all_matches=False,
        )

    # Position along the route: segment start plus projection onto it.
    start = starts[segment_index]
    direction = ends[segment_index] - start
    length = segment_lengths[segment_index]
    along = np.einsum("ij,ij->i", xy[station_index] - start, direction)
    along = np.clip(along / np.where(length > 0, length, 1), 0, length)
    miles = np.zeros(len(stations))
    miles[station_index] = (
        (segment_offsets[segment_index] + along) / route_length * distance_miles
    )

    station_distances = np.full(len(stations), np.inf)
    station_distances[station_index] = distances

    exact = np.array([
        s["coordinate_source"] == Station.CoordinateSource.STATION
        for s in stations
    ])
    corridor = np.where(exact, EXACT_CORRIDOR_METERS, CITY_CORRIDOR_METERS)

    # A station at mile zero can supply fuel before departure.
    keep = (
        (station_distances <= corridor)
        & (miles >= 0)
        & (miles < distance_miles)
    )

    candidates = [
        {
            "id": station["opis_id"],
            "name": station["name"],
            "latitude": float(station["latitude"]),
            "longitude": float(station["longitude"]),
            "location_precision": "exact" if is_exact else "city",
            "mile": float(mile),
            "price": str(station["route_price"]),
        }
        for station, mile, is_exact, kept in zip(stations, miles, exact, keep)
        if kept
    ]

    return sorted(candidates, key=lambda station: station["mile"])
