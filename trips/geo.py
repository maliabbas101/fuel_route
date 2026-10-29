import json
from functools import lru_cache
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.prepared import prep

USA_BOUNDARY_PATH = Path(__file__).resolve().parent / "data" / "usa_boundary.geojson"


@lru_cache(maxsize=1)
def usa_boundary():
    with USA_BOUNDARY_PATH.open(encoding="utf-8") as source:
        feature = json.load(source)
    return prep(shape(feature["geometry"]))


def is_in_usa(longitude, latitude):
    return bool(usa_boundary().covers(Point(longitude, latitude)))


def meters_projection(longitude, latitude):
    """Projects longitude/latitude arrays to meters around a center point."""
    return Transformer.from_crs(
        "EPSG:4326",
        f"+proj=aeqd +lat_0={latitude} +lon_0={longitude} +units=m",
        always_xy=True,
    ).transform
