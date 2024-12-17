from django.core.management.base import BaseCommand, CommandError
from monitoring.metrics import gather_metrics


class Command(BaseCommand):
    help = "Calculates and records monitoring metrics"

    def handle(self, *args, **options):
        gather_metrics()
