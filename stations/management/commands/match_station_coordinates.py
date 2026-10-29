import csv
import json
import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from stations.constants import DEFAULT_STATION_COORDINATES
from stations.models import Station


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def export_exact_coordinates(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["opis_id", "latitude", "longitude"])
        writer.writerows(
            Station.objects.filter(coordinate_source=Station.CoordinateSource.STATION)
            .order_by("opis_id")
            .values_list("opis_id", "latitude", "longitude")
        )


class Command(BaseCommand):
    help = "Match OSM coordinates by brand, branch number, city, and state."

    def add_arguments(self, parser):
        parser.add_argument("input_path", type=Path)
        parser.add_argument("--state", required=True)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument(
            "--export",
            type=Path,
            default=Path(DEFAULT_STATION_COORDINATES),
            help="With --apply, rewrite this file with every "
            "exact station coordinate.",
        )

    def handle(self, *args, **options):
        state = options["state"].upper()
        index = defaultdict(list)

        try:
            with options["input_path"].open(encoding="utf-8") as source:
                for line_number, line in enumerate(source, start=1):
                    record = json.loads(line)
                    tags = record["tags"]

                    brand = normalize(tags.get("brand", ""))
                    branch = str(tags.get("ref", "")).strip()
                    city = normalize(tags.get("addr:city", ""))
                    record_state = tags.get("addr:state", "").upper()

                    if (
                        not brand
                        or not branch.isdigit()
                        or not city
                        or record_state != state
                    ):
                        continue

                    latitude = Decimal(str(record["latitude"]))
                    longitude = Decimal(str(record["longitude"]))

                    if (
                        not latitude.is_finite()
                        or not longitude.is_finite()
                        or not -90 <= latitude <= 90
                        or not -180 <= longitude <= 180
                    ):
                        raise ValueError(f"Invalid coordinates on line {line_number}")

                    key = (brand, int(branch), city, state)
                    index[key].append((latitude, longitude))

        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            InvalidOperation,
        ) as exc:
            raise CommandError(f"Cannot load candidate file: {exc}") from exc

        stations = (
            Station.objects.filter(
                state=state,
                prices__isnull=False,
            )
            .exclude(
                coordinate_source=Station.CoordinateSource.STATION,
            )
            .distinct()
            .order_by("opis_id")
        )

        updates = []
        unmatched = 0
        ambiguous = 0

        for station in stations:
            match = re.fullmatch(r"(.+?)\s*#\s*(\d+)", station.name.strip())

            if not match:
                unmatched += 1
                continue

            key = (
                normalize(match.group(1)),
                int(match.group(2)),
                normalize(station.city),
                station.state.upper(),
            )

            candidates = index.get(key, [])

            if not candidates:
                unmatched += 1
                continue

            if len(candidates) != 1:
                ambiguous += 1
                continue

            latitude, longitude = candidates[0]
            station.latitude = latitude
            station.longitude = longitude
            station.coordinate_source = Station.CoordinateSource.STATION
            updates.append(station)

            self.stdout.write(
                f"{station.opis_id}: {station.name}, {station.city} "
                f"-> {latitude}, {longitude}"
            )

        if options["apply"]:
            with transaction.atomic():
                Station.objects.bulk_update(
                    updates,
                    ["latitude", "longitude", "coordinate_source"],
                    batch_size=500,
                )
            export_exact_coordinates(options["export"])

        action = "Saved" if options["apply"] else "Would save"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action}: {len(updates)}; "
                f"unmatched: {unmatched}; ambiguous: {ambiguous}."
            )
        )
