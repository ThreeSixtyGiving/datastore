from django.core.management.base import BaseCommand

from db.models import Latest
from db.management.spinner import Spinner

import os
import json


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

        for source in latest_data.sourcefile_set.all():
            data_all.append(source.data)

            grant_file_name = "%s/json_all/%s.json" % (
                options['dir'],
                source.data['identifier']
            )

            # Write out grant data
            with open(grant_file_name, 'w') as grantfp:
                grants = {
                    'grants': list(source.grant_set.all().values_list('data', flat=True))
                }

                grantfp.write(json.dumps(grants, indent=2))

        with open(data_all_file, 'w+') as data_all_fp:
            data_all_fp.write(json.dumps(data_all, indent=2))

        spinner.stop()
