from django.core.management.base import BaseCommand
from django.db.models import Q

from stations.models import Station


class Command(BaseCommand):
    help = "List stations that need geocoding."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=10)

    def handle(self, *args, **options):
        limit = options["limit"]

        if limit < 1:
            self.stderr.write("--limit must be greater than zero.")
            return

        stations = (
            Station.objects.filter(
                Q(latitude__isnull=True) | Q(longitude__isnull=True),
                prices__isnull=False,
            )
            .distinct()
            .order_by("opis_id")[:limit]
        )

        for station in stations:
            self.stdout.write(
                f"{station.opis_id}: {station.name}, "
                f"{station.address}, {station.city}, {station.state}"
            )

        self.stdout.write(
            self.style.SUCCESS(f"Listed {len(stations)} stations.")
        )