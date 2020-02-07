import json
import os

from django.core.management.base import BaseCommand

from db.management.spinner import Spinner
from db.models import Latest


class Command(BaseCommand):
    help = "Outputs a grantnav compatible datadump of our best Latest data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dir',
            action='store',
            dest='dir',
            type=str,
            help="Destination of data output dir",
            default="grantnav_data"
        )

        parser.add_argument(
            '--indent-json',
            action='store',
            dest='indent',
            type=int,
            help="Indentation of JSON output",
            default=None
        )

    def handle(self, *args, **options):
        """ Create grantnav package:

          - data_all.json (all sources)
          - json_all/
                |- grants.json (lists of grants)
                |- grants.json
                ...
        """
        spinner = Spinner()
        spinner.start()

        latest_data = Latest.objects.get(series=Latest.CURRENT)

        # Create the data_all json file
        os.makedirs("%s/json_all/" % options['dir'], mode=0o700)

        data_all = []
        data_all_file = "%s/data_all.json" % options['dir']

        def flatten_grant(in_grant):
            """ Flattens grant object to make compatible with grantnav """
            out_grant = {}
            out_grant.update(in_grant['data'])
            try:
                out_grant.update(in_grant['additional_data'])
                out_grant['additional_data_added'] = True
            except TypeError:
                # We may not have any additional_data and therefore it will be
                # None(Type)
                pass

            return out_grant

        for source in latest_data.sourcefile_set.all():
            data_all.append(source.data)

            grant_file_name = "%s/json_all/%s.json" % (
                options['dir'],
                source.data['identifier']
            )

            # Write out grant data
            with open(grant_file_name, 'w') as grantfp:

                grants_list = list(source.grant_set.all().values('data', 'additional_data'))

                grants_list_flattened = map(flatten_grant, grants_list)

                grants = {
                    'grants': list(grants_list_flattened)
                }

                grantfp.write(json.dumps(grants, indent=options['indent']))

        with open(data_all_file, 'w+') as data_all_fp:
            data_all_fp.write(json.dumps(data_all, indent=options['indent']))

        spinner.stop()
