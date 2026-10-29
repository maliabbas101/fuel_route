from django.db.models import Avg
from pyproj import CRS, Transformer
from shapely.geometry import LineString, Point

from stations.models import Station


def find_route_stations(geometry, distance_miles, corridor_meters=1600):
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

    projected = [
        transformer.transform(longitude, latitude)
        for longitude, latitude, *_ in coordinates
    ]

    line = LineString(projected)

    if line.length == 0:
        return []

    stations = (
        Station.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            prices__isnull=False,
        )
        .annotate(route_price=Avg("prices__price_per_gallon"))
    )

    candidates = []

    for station in stations:
        x, y = transformer.transform(
            float(station.longitude),
            float(station.latitude),
        )

        point = Point(x, y)

        if line.distance(point) > corridor_meters:
            continue

        # Scale geometry position to the provider's driving distance.
        mile = line.project(point) / line.length * distance_miles

        if not 0 < mile < distance_miles:
            continue

        candidates.append({
            "id": station.opis_id,
            "name": station.name,
            "latitude": float(station.latitude),
            "longitude": float(station.longitude),
            "mile": mile,
            "price": str(station.route_price),
        })

    return sorted(candidates, key=lambda station: station["mile"])