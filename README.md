# Fuel Route

A Django API that plans a driving trip between two points in the USA, chooses
cost-effective fuel stops for a vehicle with a 500-mile range (50-gallon tank,
10 miles per gallon), and returns the route, the stops and the total fuel cost.
Each trip makes one call to [openrouteservice](https://openrouteservice.org/);
repeated trips are served from a one-hour cache.

This is an approximate planner: most station positions are city centers, not
the stations themselves. See [Station coordinates](#station-coordinates).


## Requirements

- Python 3.13.
- Django 6.1.2 and Django REST framework, with all dependencies pinned in
  `requirements.txt`.

## Setup

Open PowerShell in the project folder containing `manage.py`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_fuel_prices fuel-prices.csv
.\.venv\Scripts\python.exe manage.py apply_place_coordinates --apply
.\.venv\Scripts\python.exe manage.py check
```

If the virtual environment already exists, skip the first command. These commands
use its Python directly, so activating the environment is optional.

## Run locally

Create an admin account, then start the development server:

```powershell
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for links to the map,
the API and admin. Open [Django admin](http://127.0.0.1:8000/admin/) and sign
in to inspect the data.
Create the admin account only once. Stop the server with `Ctrl+C`.

Copy `.env.example` to `.env` and set `ORS_API_KEY` to a free
openrouteservice key before planning trips.

## API

`POST /api/trips/plan/`

```json
{
  "start": {"latitude": 40.7128, "longitude": -74.0060},
  "finish": {"latitude": 34.0522, "longitude": -118.2437},
  "initial_fuel_gallons": 50
}
```

`initial_fuel_gallons` is optional (0 to 50, default 50). Both points must be
inside the contiguous USA: latitude 24 to 50 and longitude -125 to -66
(western longitudes are negative). The response contains:

- `route_geojson`: the route line.
- `start_snap_miles` and `finish_snap_miles`: how far each point was moved to
  reach the nearest road (up to 5 km).
- `fuel_stops`: each stop's station, mile, gallons bought, price, cost and
  `location_precision` (`exact` or `city`).
- `distance_miles`, `fuel_consumed_gallons`, `fuel_purchased_gallons` and
  `fuel_purchase_cost_usd`.
- `assumptions`: the price policy and station-location sources.

Stations are loaded into memory on the first request, so restart the server
after re-importing prices or coordinates.

Fuel already in the tank at departure is not included in the cost.

| Status | Meaning |
| --- | --- |
| 200 | Trip planned. |
| 400 | Invalid input; errors are listed per field. |
| 422 | `NO_FEASIBLE_FUEL_PLAN`: no stations close enough to reach the finish. |
| 422 | No public road within 5 km of a point, no road connects the points, or the route exceeds openrouteservice's 6,000 km limit. |
| 502 / 503 | The routing service failed, timed out or hit its quota. |

A map that calls this endpoint is at
[http://127.0.0.1:8000/api/trips/map/](http://127.0.0.1:8000/api/trips/map/).
Opening the endpoint itself in a browser shows Django REST framework's
browsable API.

## Code layout

| Module | Responsibility |
| --- | --- |
| `trips/views.py` | HTTP only: validate the request, call the planner, map errors to status codes |
| `trips/serializers.py` | Request validation, including the USA boundary check |
| `trips/planner.py` | Runs route → stations along it → fuel plan |
| `trips/routing.py` | openrouteservice client with a one-hour route cache |
| `trips/stations.py` | Finds stations within the corridor and their mile along the route |
| `trips/optimizer.py` | Greedy cheapest-fuel algorithm, independent of Django |
| `trips/geo.py` | USA boundary and map-projection helpers |
| `trips/constants.py`, `trips/exceptions.py` | Shared settings and errors |
| `stations/` | Models, data-import commands and place-name matching |

## Tests and formatting

The tests mock the routing service, so they need no API key:

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe -m black --check .
.\.venv\Scripts\python.exe -m isort --check-only .
```

## Fuel-price data

The supplied CSV contains:

| Item | Count |
| --- | ---: |
| Source price rows | 8,151 |
| Unique stations | 6,738 |
| Stations with multiple distinct prices | 597 |

`Station` stores one location per OPIS ID and uses the first station name in the
file. `FuelPrice` stores each source row with its name, rack ID, and price. Prices
use decimal fields to preserve the precision in the CSV.

The CSV has no coordinates, timestamps, or fuel-type column. All price records
are retained. For planning, a station's price is the average of its CSV price
rows.

Validate the file without changing the database:

```powershell
.\.venv\Scripts\python.exe manage.py import_fuel_prices fuel-prices.csv --dry-run
```

The importer validates the complete file before saving it in a database transaction.
Reimporting replaces the entire price snapshot without duplicating stations or
clearing their coordinates. Stations absent from a replacement file remain stored
without prices. Supply a complete dataset, rather than an incremental update.

## Station coordinates

The CSV has no coordinates, so stations are located without any API calls:

1. **Exact points.** `match_station_coordinates` matches OpenStreetMap fuel
   stations by brand, branch number, city and state. Few OSM records carry
   branch numbers, so this covers only a handful of stations. With `--apply`
   it also rewrites the committed `data/station-coordinates.csv`.
2. **City centers.** Every other station gets the center of its city from
   `data/place-coordinates.csv`.

`apply_place_coordinates --apply` loads both committed files, exact points
first, so a fresh database needs no OSM downloads.

| Station coordinates | Count |
| --- | ---: |
| Exact OSM point | 22 |
| Census place (city, town, village, CDP) | 6,271 |
| Census county subdivision (town, township) | 103 |
| GeoNames populated place | 171 |
| USA stations with no coordinates (ambiguous or unknown city name) | 59 |
| Canadian stations (outside the USA, skipped) | 112 |

That locates 99.1% of the 6,626 USA stations.

City-center points can be a few miles from the highway exit a station is on,
so the route search uses a 1.6 km corridor for exact points and an 8 km
corridor for city centers. Each fuel stop reports its `location_precision`.

Because of this, a city-center stop is approximate:

- A station in a city near the route may be included even if it is off the
  route, or excluded if the city center is more than 8 km away.
- A stop's mile along the route, and so whether it is reachable on the
  remaining fuel, can be off by a few miles.

`data/place-coordinates.csv` is committed. To rebuild it, download the
[Census Gazetteer](https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html)
national places and county subdivisions files and the
[GeoNames](https://download.geonames.org/export/dump/) `US.zip` dump, then run:

```powershell
.\.venv\Scripts\python.exe manage.py build_place_coordinates `
    --places 2025_Gaz_place_national.txt `
    --cousubs 2025_Gaz_cousubs_national.txt `
    --geonames US.txt
```

A city name that matches places more than 25 miles apart in the same state,
such as Middletown, PA, is left unresolved rather than guessed.

GeoNames data is licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); Census data is in
the public domain.
