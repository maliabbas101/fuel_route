# Fuel Route

A Django project for planning driving trips in the USA with cost-effective fuel
stops. This initial version includes the database models, fuel-price CSV importer,
and Django admin interface.


## Requirements

- Python 3.13.
- Django 6.1.2 and its dependencies, pinned in `requirements.txt`.

## Setup

Open PowerShell in the project folder containing `manage.py`:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py import_fuel_prices fuel-prices.csv
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

Open [Django admin](http://127.0.0.1:8000/admin/) and sign in to inspect the data.
Create the admin account only once. Stop the server with `Ctrl+C`.

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

The CSV has no coordinates, timestamps, or fuel-type column. Coordinates remain
empty until geocoding is added. All price records are retained; the price-selection
policy for optimization is still to be decided.

Validate the file without changing the database:

```powershell
.\.venv\Scripts\python.exe manage.py import_fuel_prices fuel-prices.csv --dry-run
```

The importer validates the complete file before saving it in a database transaction.
Reimporting replaces the entire price snapshot without duplicating stations or
clearing their coordinates. Stations absent from a replacement file remain stored
without prices. Supply a complete dataset, rather than an incremental update.





