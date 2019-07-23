from django.core.management.base import BaseCommand

from db.models import invalidate_cache


class Command(BaseCommand):
    help = "Clears our cache"

    def handle(self, *args, **options):
        invalidate_cache()
