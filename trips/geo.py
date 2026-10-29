import json
from functools import lru_cache
from pathlib import Path

from pyproj import Geod, Transformer
from shapely.geometry import Point, shape
from shapely.ops import nearest_points
from shapely.prepared import prep

from .constants import USA_BOUNDARY_TOLERANCE_METERS

USA_BOUNDARY_PATH = Path(__file__).resolve().parent / "data" / "usa_boundary.geojson"
GEOD = Geod(ellps="WGS84")


@lru_cache(maxsize=1)
def usa_boundary():
    """Return the boundary geometry and a prepared copy for fast checks."""
    with USA_BOUNDARY_PATH.open(encoding="utf-8") as source:
        feature = json.load(source)
    geometry = shape(feature["geometry"])
    return geometry, prep(geometry)


def is_in_usa(longitude, latitude):
    """True inside the boundary or within its tolerance of the generalized coastline."""
    geometry, prepared = usa_boundary()
    point = Point(longitude, latitude)
    if prepared.covers(point):
        return True
    nearest = nearest_points(geometry, point)[0]
    _, _, meters = GEOD.inv(longitude, latitude, nearest.x, nearest.y)
    return meters <= USA_BOUNDARY_TOLERANCE_METERS


def meters_projection(longitude, latitude):
    """Projects longitude/latitude arrays to meters around a center point."""
    return Transformer.from_crs(
        "EPSG:4326",
        f"+proj=aeqd +lat_0={latitude} +lon_0={longitude} +units=m",
        always_xy=True,
    ).transform
