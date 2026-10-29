from decimal import Decimal

MPG = Decimal("10")
TANK_CAPACITY = Decimal("50")
MAX_RANGE = MPG * TANK_CAPACITY


def optimize_fuel(distance_miles, stations, initial_fuel_gallons=50):
    """
    Optimize purchases on a fixed route, excluding station detours.

    stations:
        [{"id": 1, "mile": 300, "price": "3.50"}, ...]

    Starting fuel is already owned and excluded from purchase cost.
    """
    distance = Decimal(str(distance_miles))
    fuel = Decimal(str(initial_fuel_gallons))

    if not distance.is_finite() or distance <= 0:
        raise ValueError("Trip distance must be positive and finite.")

    if not fuel.is_finite() or not 0 <= fuel <= TANK_CAPACITY:
        raise ValueError("Starting fuel must be between 0 and 50 gallons.")

    points = []

    for station in stations:
        mile = Decimal(str(station["mile"]))
        price = Decimal(str(station["price"]))

        if not mile.is_finite() or not 0 <= mile < distance:
            raise ValueError("Station distance must be within the route.")

        if not price.is_finite() or price <= 0:
            raise ValueError("Station price must be positive and finite.")

        points.append({
            "id": station["id"],
            "mile": mile,
            "price": price,
        })

    points.sort(key=lambda point: (point["mile"], point["price"]))

    # The destination needs no further fuel.
    destination = {"id": None, "mile": distance, "price": Decimal("0")}
    points.append(destination)

    position = Decimal("0")
    current = None
    stops = []
    total_cost = Decimal("0")
    purchased = Decimal("0")

    while position < distance:
        if current is None:
            # At the start, only the supplied starting fuel is available.
            reachable = [
                point for point in points
                if position <= point["mile"] <= position + fuel * MPG
            ]

            if not reachable:
                raise ValueError("No fuel station is reachable with starting fuel.")

            target = min(
                reachable,
                key=lambda point: (point["price"], point["mile"]),
            )
            gallons_to_buy = Decimal("0")

        else:
            ahead = [
                point for point in points
                if position < point["mile"] <= position + MAX_RANGE
            ]

            if not ahead:
                raise ValueError("No feasible fuel plan: gap exceeds 500 miles.")

            cheaper = [
                point for point in ahead
                if point["price"] < current["price"]
            ]

            if cheaper:
                target = cheaper[0]
                desired_fuel = (target["mile"] - position) / MPG
            else:
                target = min(
                    ahead,
                    key=lambda point: (point["price"], point["mile"]),
                )
                desired_fuel = TANK_CAPACITY

            gallons_to_buy = max(Decimal("0"), desired_fuel - fuel)

            if gallons_to_buy > 0:
                # Each purchase is charged to the cent; the total is their sum.
                cost = (gallons_to_buy * current["price"]).quantize(
                    Decimal("0.01"))
                fuel += gallons_to_buy
                purchased += gallons_to_buy
                total_cost += cost

                stops.append({
                    "station_id": current["id"],
                    "mile": float(position),
                    "gallons_to_buy": float(gallons_to_buy),
                    "price_per_gallon": str(current["price"]),
                    "cost_usd": str(cost),
                })

        fuel -= (target["mile"] - position) / MPG
        position = target["mile"]
        current = target

        # Avoid revisiting a different station at the same route position.
        points = [point for point in points if point["mile"] > position]

    return {
        "fuel_stops": stops,
        "fuel_purchased_gallons": float(purchased),
        "fuel_purchase_cost_usd": str(total_cost.quantize(Decimal("0.01"))),
        "ending_fuel_gallons": float(fuel),
    }