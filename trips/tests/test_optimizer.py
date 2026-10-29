from django.test import SimpleTestCase

from trips.exceptions import NoFeasiblePlanError
from trips.optimizer import plan_fuel_stops


def station(station_id, mile, price):
    return {"id": station_id, "mile": mile, "price": price}


class PlanFuelStopsTests(SimpleTestCase):
    def test_no_stops_when_starting_fuel_reaches_finish(self):
        plan = plan_fuel_stops(300, [station(1, 100, 3.0)], start_fuel=50)

        self.assertEqual(plan["fuel_stops"], [])
        self.assertEqual(plan["fuel_purchase_cost_usd"], 0)

    def test_buys_just_enough_to_reach_a_cheaper_station(self):
        stations = [station("A", 0, 4.0), station("B", 100, 3.0)]

        plan = plan_fuel_stops(300, stations, start_fuel=0)

        stops = [
            (s["id"], s["gallons_to_buy"], s["cost_usd"]) for s in plan["fuel_stops"]
        ]
        self.assertEqual(stops, [("A", 10, 40.0), ("B", 20, 60.0)])
        self.assertEqual(plan["fuel_purchase_cost_usd"], 100.0)

    def test_fills_up_when_no_cheaper_station_is_in_range(self):
        stations = [station("A", 0, 3.0), station("B", 400, 4.0)]

        plan = plan_fuel_stops(800, stations, start_fuel=0)

        stops = [
            (s["id"], s["gallons_to_buy"], s["cost_usd"]) for s in plan["fuel_stops"]
        ]
        self.assertEqual(stops, [("A", 50, 150.0), ("B", 30, 120.0)])
        self.assertEqual(plan["fuel_purchased_gallons"], 80)

    def test_first_drives_to_cheapest_station_reachable_on_starting_fuel(self):
        stations = [
            station("A", 50, 4.0),
            station("B", 90, 3.0),
            station("C", 200, 5.0),
        ]

        plan = plan_fuel_stops(400, stations, start_fuel=10)

        self.assertEqual(plan["fuel_stops"][0]["id"], "B")

    def test_fails_when_a_gap_exceeds_the_vehicle_range(self):
        with self.assertRaises(NoFeasiblePlanError):
            plan_fuel_stops(1200, [station("A", 0, 3.0), station("B", 600, 3.0)], 0)

    def test_fails_when_starting_fuel_reaches_no_station(self):
        with self.assertRaises(NoFeasiblePlanError):
            plan_fuel_stops(300, [station("A", 100, 3.0)], start_fuel=5)
