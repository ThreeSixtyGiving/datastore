from django.core.management.base import BaseCommand

from additional_data.models import OrgInfoCache


class Command(BaseCommand):
    help = "Delete find that charity data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-prompt", action="store_true", help="Don't prompt before delete",
        )

    def handle(self, *args, **options):

        if not options["no_prompt"]:
            confirm = input("Confirm delete y/n: ")

        if "y" in confirm.lower() or options["no_prompt"]:
            OrgInfoCache.objects.all().delete()
