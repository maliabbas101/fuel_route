import json
from functools import lru_cache
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.prepared import prep


@lru_cache(maxsize=1)
def usa_boundary():
    path = Path(__file__).resolve().parent / "data" / "usa_boundary.geojson"
    with path.open(encoding="utf-8") as source:
        feature = json.load(source)
    return prep(shape(feature["geometry"]))


def is_in_usa(longitude, latitude):
    return bool(usa_boundary().covers(Point(longitude, latitude)))
