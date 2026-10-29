import csv
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stations.models import Station
from stations.places import place_key


class Command(BaseCommand):
    help = (
        "Apply exact station coordinates, then give every other station the "
        "coordinates of its city."
    )

    def add_arguments(self, parser):
        parser.add_argument("input_path", type=Path, nargs="?",
                            default=Path("data/place-coordinates.csv"))
        parser.add_argument("--stations", type=Path,
                            default=Path("data/station-coordinates.csv"),
                            help="Exact station coordinates, applied first.")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        exact = {}
        places = {}
        try:
            if options["stations"].exists():
                with options["stations"].open(encoding="utf-8") as file:
                    for row in csv.DictReader(file):
                        exact[int(row["opis_id"])] = (
                            Decimal(row["latitude"]), Decimal(row["longitude"]))
            with options["input_path"].open(encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    latitude = Decimal(row["latitude"])
                    longitude = Decimal(row["longitude"])
                    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                        raise ValueError(f"Invalid coordinates for {row}")
                    places[row["state"], row["place_key"]] = (
                        latitude, longitude, row["source"])
        except (OSError, KeyError, ValueError, InvalidOperation) as exc:
            raise CommandError(f"Cannot load coordinate file: {exc}") from exc

        updates = []
        sources = Counter()
        for station in Station.objects.all():
            if station.opis_id in exact:
                station.latitude, station.longitude = exact[station.opis_id]
                station.coordinate_source = Station.CoordinateSource.STATION
                updates.append(station)
                sources["station"] += 1
                continue
            if station.coordinate_source == Station.CoordinateSource.STATION:
                # Matched in this database but not yet exported; keep it.
                sources["station"] += 1
                continue
            match = places.get((station.state, place_key(station.city)))
            if match is None:
                if station.latitude is not None:
                    # Clear coordinates from a source that no longer matches.
                    station.latitude = station.longitude = None
                    station.coordinate_source = ""
                    updates.append(station)
                sources["unresolved"] += 1
                continue
            station.latitude, station.longitude, station.coordinate_source = match
            updates.append(station)
            sources[match[2]] += 1

        if options["apply"]:
            with transaction.atomic():
                Station.objects.bulk_update(
                    updates,
                    ["latitude", "longitude", "coordinate_source"],
                    batch_size=500,
                )

        action = "Saved" if options["apply"] else "Would save"
        summary = ", ".join(f"{k}: {v}" for k, v in sorted(sources.items()))
        self.stdout.write(self.style.SUCCESS(
            f"{action} station coordinates. {summary}."))
