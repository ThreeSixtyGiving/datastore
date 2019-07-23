from django.core.management.base import BaseCommand, CommandError

from db.common import CanonicalDataset
from db.management.spinner import Spinner

import os
import json

class Command(BaseCommand):
    help = "Outputs a datagetter compatible datadump of our best/canonical data"

    def add_arguments(self, parser):


        parser.add_argument(
            '--dir',
            action='store',
            dest='dir',
            type=str,
            help="Destination of data output dir",
            default="canonical_data"
        )


    def handle(self, *args, **options):

        os.makedirs("%s/json_all/" % options['dir'], mode=0o700)

        spinner = Spinner()
        spinner.start()

        canonical_data = CanonicalDataset()

        data_all = []
        source_index = {}

        data_all_file = "%s/data_all.json" % options['dir']

        for source in canonical_data.sources:
            data_all.append(source['data'])
            # Build a temporary index cache to avoid querying sources later
            source_index[source['id']] = source['data']


        with open(data_all_file, 'w+') as data_all_fp:
            data_all_fp.write(json.dumps(data_all, indent=2))

        grants_grouped = {}

        # Build the grants json file (each file contains multiple grants per source)

        for grant in canonical_data.grants:
            grant_file_name = "%s/json_all/%s.json" % (
                options['dir'],
                source_index[grant['source_file_id']]['identifier']
            )

            # If it doesn't already exist as a group create it
            if not grants_grouped.get(grant_file_name, None):
                grants_grouped[grant_file_name] = []


            grants_grouped[grant_file_name].append(grant['data'])

        for file_name, grants_list in grants_grouped.items():
            grant_file = {
                'grants': grants_list
            }

            with open(file_name, 'w+') as grantfp:
                grantfp.write(json.dumps(grant_file, indent=2))

        spinner.stop()


