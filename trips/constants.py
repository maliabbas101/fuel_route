MPG = 10
TANK_GALLONS = 50
MAX_RANGE_MILES = MPG * TANK_GALLONS

# Stations cover the contiguous USA only, so trips must start and end inside it.
CONTIGUOUS_USA_BOUNDS = {
    "min_latitude": 24,
    "max_latitude": 50,
    "min_longitude": -125,
    "max_longitude": -66,
}

METERS_PER_MILE = 1609.344
EXACT_CORRIDOR_METERS = 1600
CITY_CORRIDOR_METERS = 8000
ROUTE_SIMPLIFY_METERS = 100
# The 1:5,000,000 boundary can put real coastal points just offshore.
USA_BOUNDARY_TOLERANCE_METERS = 1000

ORS_DIRECTIONS_URL = (
    "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
)
ROUTING_TIMEOUT_SECONDS = 20
ROUTE_CACHE_SECONDS = 3600
# How far openrouteservice may move a trip point to reach a road.
ORS_SNAP_RADIUS_METERS = 5000

# openrouteservice error codes caused by the requested points.
ORS_DISTANCE_LIMIT = 2004
ORS_ROUTE_NOT_FOUND = 2009
ORS_NO_ROAD_NEAR_POINT = 2010
