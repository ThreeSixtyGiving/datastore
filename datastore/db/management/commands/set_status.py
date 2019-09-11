from django.core.management.base import BaseCommand, CommandError

from db.models import Status, Statuses


class Command(BaseCommand):
    help = "Sets a status flag"

    def add_arguments(self, parser):
        parser.add_argument(
            '--list-options',
            action='store_true',
            help="List the status and items to be in a status",
        )

        parser.add_argument(
            '--list',
            action='store_true',
            help="List the status and items to be in a status",
        )

        parser.add_argument(
            '--what',
            action='store',
            dest='what',
            help='The thing to set the status of e.g. datagetter',
        )

        parser.add_argument(
            '--status',
            action='store',
            dest='status',
            help='The status to set the thing to e.g. IN_PROGRESS',
        )

    def handle(self, *args, **options):

        if options.get('list_options'):
            # TODO future refactor as this is a bit clunky
            print(Statuses.__dict__)
            return

        if options.get('list'):
            print(Status.objects.all().values())
            return

        if options.get('status') and options.get('what'):
            item, c = Status.objects.get_or_create(what=options['what'])
            try:
                item.status = Statuses.__dict__.get(options['status'])
            except KeyError:
                print("Unknown status use --list-options to list statuses")
            item.save()

        else:
            raise CommandError("Not enough parameters supplied to set status")
