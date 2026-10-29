import json
from pathlib import Path

import osmium
from django.core.management.base import BaseCommand, CommandError


class FuelHandler(osmium.SimpleHandler):
    def __init__(self, output):
        super().__init__()
        self.output = output
        self.count = 0

    def write_station(self, element, latitude, longitude, method):
        self.output.write(json.dumps({
            "osm_type": element.type_str(),
            "osm_id": element.id,
            "latitude": latitude,
            "longitude": longitude,
            "coordinate_method": method,
            "tags": dict(element.tags),
        }) + "\n")

        self.count += 1

    def node(self, node):
        if node.tags.get("amenity") != "fuel":
            return

        if node.location.valid():
            self.write_station(
                node,
                node.location.lat,
                node.location.lon,
                "mapped_point",
            )

    def way(self, way):
        if way.tags.get("amenity") != "fuel":
            return

        locations = [
            (node.lat, node.lon)
            for node in way.nodes
            if node.location.valid()
        ]

        if not locations or len(locations) != len(way.nodes):
            return

        # Approximate representative point for a mapped station area.
        latitudes, longitudes = zip(*locations)

        self.write_station(
            way,
            (min(latitudes) + max(latitudes)) / 2,
            (min(longitudes) + max(longitudes)) / 2,
            "bounding_box_center",
        )


class Command(BaseCommand):
    help = "Extract fuel-station candidates from a local OSM file."

    def add_arguments(self, parser):
        parser.add_argument("input_path", type=Path)
        parser.add_argument(
            "--output",
            type=Path,
            default=Path("data/wisconsin-fuel-stations.jsonl"),
        )

    def handle(self, *args, **options):
        input_path = options["input_path"]
        output_path = options["output"]

        if not input_path.is_file():
            raise CommandError(f"Input file not found: {input_path}")

        if input_path.resolve() == output_path.resolve():
            raise CommandError("Input and output paths must be different.")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Exclusive creation avoids overwriting an existing extraction.
            with output_path.open("x", encoding="utf-8") as output:
                handler = FuelHandler(output)
                handler.apply_file(str(input_path), locations=True)
        except FileExistsError:
            raise CommandError(
                "Output already exists. Choose a different --output path."
            ) from None
        except (OSError, RuntimeError) as exc:
            raise CommandError(
                f"Extraction failed: {exc}. "
                "Any partial output must be removed before retrying."
            ) from exc

        self.stdout.write(self.style.SUCCESS(
            f"Extracted {handler.count} candidates to {output_path}"
        ))