"""Validate a full CSV, then atomically replace its price snapshot."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stations.models import FuelPrice, Station

HEADERS = {
    "OPIS Truckstop ID",
    "Truckstop Name",
    "Address",
    "City",
    "State",
    "Rack ID",
    "Retail Price",
}


class Command(BaseCommand):
    help = (
        "Import a complete CSV snapshot; preserve source rows and station coordinates."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        stations, prices = {}, []
        try:
            with options["csv_path"].open(encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                if set(reader.fieldnames or []) != HEADERS:
                    raise CommandError(
                        "CSV headers must match the supplied assessment file."
                    )
                for line, raw in enumerate(reader, start=2):
                    try:
                        if None in raw or any(value is None for value in raw.values()):
                            raise ValueError("wrong number of columns")
                        row = {key: value.strip() for key, value in raw.items()}
                        opis_id, rack_id = int(row["OPIS Truckstop ID"]), int(
                            row["Rack ID"]
                        )
                        price = Decimal(row["Retail Price"])
                        if opis_id <= 0 or rack_id < 0:
                            raise ValueError("invalid station or rack ID")
                        if not price.is_finite() or not Decimal("0") < price < Decimal(
                            "10000"
                        ):
                            raise ValueError("price must be positive and below 10000")
                        if price != price.quantize(Decimal("0.00000001")):
                            raise ValueError("price has more than eight decimal places")
                        data = dict(
                            name=row["Truckstop Name"],
                            address=row["Address"],
                            city=row["City"],
                            state=row["State"].upper(),
                        )
                        if any(not value for value in data.values()):
                            raise ValueError("missing station name or address")
                        if (
                            len(data["state"]) != 2
                            or not data["state"].isascii()
                            or not data["state"].isalpha()
                        ):
                            raise ValueError("state must be a two-letter abbreviation")
                        if (
                            len(data["name"]) > 255
                            or len(data["address"]) > 255
                            or len(data["city"]) > 100
                        ):
                            raise ValueError(
                                "station text exceeds database field length"
                            )
                        if opis_id in stations:
                            previous = stations[opis_id]
                            if any(
                                previous[key].casefold() != data[key].casefold()
                                for key in ("address", "city", "state")
                            ):
                                raise ValueError(
                                    "same station ID has conflicting locations"
                                )
                        else:
                            stations[opis_id] = data
                        prices.append((opis_id, line, data["name"], rack_id, price))
                    except (ValueError, InvalidOperation) as exc:
                        raise CommandError(f"CSV row {line}: {exc}") from exc
        except (OSError, UnicodeError, csv.Error) as exc:
            raise CommandError(f"Cannot read CSV: {exc}") from exc
        if not prices:
            raise CommandError(
                "CSV contains no data rows; existing data was not changed."
            )
        price_sets = {}
        for opis_id, _, _, _, price in prices:
            price_sets.setdefault(opis_id, set()).add(price)
        conflicts = sum(len(values) > 1 for values in price_sets.values())
        self.stdout.write(
            f"Validated {len(prices)} price rows, {len(stations)} stations; "
            f"{conflicts} stations have multiple prices (all preserved)."
        )
        if options["dry_run"]:
            self.stdout.write("Dry run: no database changes.")
            return
        with transaction.atomic():
            Station.objects.bulk_create(
                [
                    Station(opis_id=opis_id, **data)
                    for opis_id, data in stations.items()
                ],
                update_conflicts=True,
                unique_fields=["opis_id"],
                update_fields=["name", "address", "city", "state"],
                batch_size=500,
            )
            station_ids = dict(Station.objects.values_list("opis_id", "id"))
            FuelPrice.objects.all().delete()
            FuelPrice.objects.bulk_create(
                [
                    FuelPrice(
                        station_id=station_ids[opis_id],
                        source_row=line,
                        source_name=name,
                        rack_id=rack_id,
                        price_per_gallon=price,
                    )
                    for opis_id, line, name, rack_id, price in prices
                ],
                batch_size=500,
            )
        self.stdout.write(
            self.style.SUCCESS(
                "Import complete. Re-running will not duplicate records."
            )
        )
