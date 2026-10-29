import csv
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from stations.constants import (
    AMBIGUITY_MILES,
    DEFAULT_PLACE_COORDINATES,
    GEONAMES_SKIPPED_CODES,
    PLACE_SOURCES,
    USA_STATES,
)
from stations.models import Station
from stations.places import census_keys, miles_between, place_key


class Command(BaseCommand):
    help = (
        "Build a city-coordinate table for station cities from the Census "
        "Gazetteer and GeoNames files."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--places",
            type=Path,
            required=True,
            help="Census Gazetteer national places file.",
        )
        parser.add_argument(
            "--cousubs",
            type=Path,
            required=True,
            help="Census Gazetteer county subdivisions file.",
        )
        parser.add_argument(
            "--geonames", type=Path, required=True, help="GeoNames US.txt dump."
        )
        parser.add_argument(
            "--output", type=Path, default=Path(DEFAULT_PLACE_COORDINATES)
        )

    def handle(self, *args, **options):
        wanted = {
            (state, place_key(city))
            for state, city in Station.objects.values_list("state", "city")
            if state in USA_STATES
        }
        if not wanted:
            raise CommandError("No USA stations found. Import prices first.")

        candidates = defaultdict(list)

        try:
            for source, path in (
                ("census_place", options["places"]),
                ("census_cousub", options["cousubs"]),
            ):
                with path.open(encoding="utf-8") as file:
                    reader = csv.DictReader(file, delimiter="|")
                    reader.fieldnames = [n.strip() for n in reader.fieldnames]
                    for row in reader:
                        for key in census_keys(row["NAME"]):
                            if (row["USPS"], key) in wanted:
                                candidates[row["USPS"], key].append(
                                    (
                                        source,
                                        float(row["INTPTLAT"]),
                                        float(row["INTPTLONG"]),
                                        0,
                                    )
                                )

            csv.field_size_limit(2**31 - 1)
            with options["geonames"].open(encoding="utf-8") as file:
                reader = csv.reader(file, delimiter="\t", quoting=csv.QUOTE_NONE)
                for row in reader:
                    if row[6] != "P" or row[7] in GEONAMES_SKIPPED_CODES:
                        continue
                    for key in {place_key(row[1]), place_key(row[2])}:
                        if (row[10], key) in wanted:
                            candidates[row[10], key].append(
                                (
                                    "geonames",
                                    float(row[4]),
                                    float(row[5]),
                                    int(row[14] or 0),
                                )
                            )
        except (OSError, KeyError, IndexError, ValueError) as exc:
            raise CommandError(f"Cannot read source file: {exc}") from exc

        rows = []
        ambiguous = 0

        for state, key in sorted(wanted):
            for source in PLACE_SOURCES:
                matches = [c for c in candidates[state, key] if c[0] == source]
                if not matches:
                    continue
                if any(
                    miles_between(matches[0][1:3], match[1:3]) > AMBIGUITY_MILES
                    for match in matches
                ):
                    ambiguous += 1
                    break
                _, latitude, longitude, _ = max(matches, key=lambda m: m[3])
                rows.append([state, key, f"{latitude:.6f}", f"{longitude:.6f}", source])
                break

        output = options["output"]
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["state", "place_key", "latitude", "longitude", "source"])
            writer.writerows(rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(rows)} of {len(wanted)} USA station cities to "
                f"{output}; ambiguous: {ambiguous}; "
                f"missing: {len(wanted) - len(rows) - ambiguous}."
            )
        )
