from .constants import MAX_RANGE_MILES, MPG, TANK_GALLONS
from .exceptions import NoFeasiblePlanError


def plan_fuel_stops(distance, stations, start_fuel):
    """
    Greedy cheapest-fuel plan. At each station on the way:
    - a cheaper station is within range: buy just enough to reach it;
    - otherwise: fill up and drive to the cheapest station within range.
    Nothing can be bought at the start, so first drive to the cheapest
    station the starting fuel reaches.
    """
    finish = {"mile": distance, "price": 0}
    ahead = sorted(stations, key=lambda s: s["mile"]) + [finish]
    position, fuel, current = 0, start_fuel, None
    stops = []

    while current is not finish:
        range_miles = MAX_RANGE_MILES if current else fuel * MPG
        reachable = [s for s in ahead if s["mile"] <= position + range_miles]
        if not reachable:
            raise NoFeasiblePlanError(out_of_range_reason(position, ahead[0], current))

        cheaper = [s for s in reachable if current and s["price"] < current["price"]]
        if cheaper:
            target = cheaper[0]
            gallons = (target["mile"] - position) / MPG - fuel
        else:
            target = min(reachable, key=lambda s: s["price"])
            gallons = TANK_GALLONS - fuel if current else 0

        if gallons > 0:
            fuel += gallons
            stops.append(
                {
                    **current,
                    "gallons_to_buy": round(gallons, 3),
                    "cost_usd": round(gallons * current["price"], 2),
                }
            )

        fuel -= (target["mile"] - position) / MPG
        position, current = target["mile"], target
        ahead = [s for s in ahead if s["mile"] > position]

    return {
        "fuel_stops": stops,
        "fuel_purchased_gallons": round(sum(s["gallons_to_buy"] for s in stops), 2),
        "fuel_purchase_cost_usd": round(sum(s["cost_usd"] for s in stops), 2),
    }


def out_of_range_reason(position, next_stop, current):
    """Explain why the next station or the finish cannot be reached."""
    gap = next_stop["mile"] - position
    target = "fuel station on the route" if "id" in next_stop else "finish"
    if current is None:
        first = "first " if "id" in next_stop else ""
        return (
            f"The {first}{target} is {gap:.0f} miles away, beyond what the "
            f"starting fuel covers. Start with at least {gap / MPG:.1f} gallons."
        )
    return (
        f"No fuel station in the {gap:.0f} miles after mile {position:.0f}; "
        f"the vehicle range is {MAX_RANGE_MILES} miles."
    )
