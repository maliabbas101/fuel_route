"""Place-name matching and distance helpers for the coordinate commands."""

import re

from pyproj import Geod

from .constants import METERS_PER_MILE

WGS84 = Geod(ellps="WGS84")

CENSUS_SUFFIX = re.compile(
    r"\s+(city and borough|(consolidated|metropolitan|unified) government"
    r"|urban county|charter township|city|town|township|village|borough|CDP"
    r"|municipality|plantation|gore|grant|location|purchase"
    r"|unorganized territory)$",
    re.IGNORECASE,
)
CENSUS_PREFIX = re.compile(r"^(town|city|village|borough) of\s+", re.IGNORECASE)


def place_key(name):
    """Normalize "Saint Johns", "St. Johns" and "ST JOHNS" to one key."""
    name = name.upper().replace(".", "").replace("'", "")
    name = re.sub(r"\b(SAINTE|SAINT|STE|ST)\b", "ST", name)
    name = re.sub(r"\b(FORT|FT)\b", "FT", name)
    name = re.sub(r"\b(MOUNT|MT)\b", "MT", name)
    return re.sub(r"[^A-Z0-9]", "", name)


def census_keys(name):
    full = re.sub(r"\s*\(.*?\)", "", name.strip())
    base = CENSUS_PREFIX.sub("", CENSUS_SUFFIX.sub("", full))
    names = {full, base}
    if "-" in base:
        names.add(base.split("-")[0])
    return {place_key(value) for value in names}


def miles_between(a, b):
    """Distance in miles between two (latitude, longitude) points."""
    _, _, meters = WGS84.inv(a[1], a[0], b[1], b[0])
    return meters / METERS_PER_MILE
