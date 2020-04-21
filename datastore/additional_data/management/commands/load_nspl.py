from django.core.management.base import BaseCommand

# from additional_data.models import nspl?


class Command(BaseCommand):
    help = "Sets a status flag"

    def add_arguments(self, parser):
        pass

    #        parser.add_argument(
    #            type=str,
    #           nargs=1,
    #           action="store",
    #           dest="file_path",
    #            help="The location of the nspl file",
    #        )

    def handle(self, *args, **options):
        # Do data import
        pass
