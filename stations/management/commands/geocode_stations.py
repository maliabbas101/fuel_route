import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from stations.models import Station


class Command(BaseCommand):
    help = "Fetch geocoding candidates without changing the database."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=1)

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1:
            raise CommandError("--limit must be greater than zero.")

        api_key = os.environ.get("ORS_API_KEY")
        if not api_key:
            raise CommandError("Set the ORS_API_KEY environment variable.")

        stations = list(
            Station.objects.filter(
                Q(latitude__isnull=True) | Q(longitude__isnull=True),
                prices__isnull=False,
            )
            .distinct()
            .order_by("opis_id")[:limit]
        )

        for index, station in enumerate(stations):
            if index:
                time.sleep(1)

            # Highway exit descriptions confused our earlier address searches.
            query = f"{station.name}, {station.city}, {station.state}, USA"
            params = urlencode({
                "text": query,
                "boundary.country": "USA",
                "layers": "venue",
                "size": 3,
            })

            request = Request(
                f"https://api.openrouteservice.org/geocode/search?{params}",
                headers={
                    "Authorization": api_key,
                    "Accept": "application/json",
                },
            )

            self.stdout.write(f"\n{station.opis_id}: {query}")

            try:
                with urlopen(request, timeout=20) as response:
                    data = json.load(response)
            except HTTPError as exc:
                # Stop on authentication or quota errors.
                if exc.code in (401, 403, 429):
                    raise CommandError(
                        f"API returned HTTP {exc.code}. "
                        "Check your key, permissions, and quota."
                    ) from None
                self.stderr.write(f"API returned HTTP {exc.code}; skipped.")
                continue
            except (URLError, TimeoutError):
                self.stderr.write("Request failed or timed out; skipped.")
                continue
            except (ValueError, UnicodeError):
                self.stderr.write("API returned invalid JSON; skipped.")
                continue

            if not isinstance(data, dict):
                self.stderr.write("Unexpected response format; skipped.")
                continue

            features = data.get("features")
            if not isinstance(features, list):
                self.stderr.write("Response has no valid features list; skipped.")
                continue

            if not features:
                self.stdout.write("No candidates found.")
                continue

            for feature in features:
                properties = feature.get("properties") or {}
                geometry = feature.get("geometry") or {}

                self.stdout.write(json.dumps({
                    "label": properties.get("label"),
                    "state": properties.get("region_a"),
                    "city": properties.get("locality"),
                    "layer": properties.get("layer"),
                    "coordinates": geometry.get("coordinates"),
                }))

        self.stdout.write("\nFinished. No database changes made.")