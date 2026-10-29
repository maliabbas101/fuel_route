from .constants import MPG
from .exceptions import NoFeasiblePlanError
from .optimizer import plan_fuel_stops
from .routing import get_route
from .stations import find_route_stations


def plan_trip(start, finish, start_fuel):
    """Route the trip, find stations along it and choose the fuel stops."""
    route, cache_hit = get_route(start, finish)
    distance = route["distance_miles"]
    stations = find_route_stations(route["geometry"], distance)

    summary = {
        "distance_miles": round(distance, 2),
        "duration_seconds": route["duration_seconds"],
        "fuel_consumed_gallons": round(distance / MPG, 2),
        "route_geojson": route["geometry"],
        "candidate_station_count": len(stations),
        "route_cache_hit": cache_hit,
    }
    try:
        plan = plan_fuel_stops(distance, stations, start_fuel)
    except NoFeasiblePlanError as exc:
        exc.route_summary = summary
        raise

    return {
        **summary,
        **plan,
        "assumptions": {
            "initial_fuel_gallons": start_fuel,
            "starting_fuel_cost_included": False,
            "price_policy": "Average of the CSV prices for each station",
            "station_locations": "Exact where matched, otherwise city center",
        },
    }
