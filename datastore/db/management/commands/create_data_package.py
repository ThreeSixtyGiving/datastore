import json
import os

from django.core.management.base import BaseCommand

from db.management.spinner import Spinner
from db.models import Latest

from db.management.commands.manage_entities_data import create_orgs_list


class Command(BaseCommand):
    help = "Outputs a data package of our best Latest data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            action="store",
            dest="dir",
            type=str,
            help="Destination of data output dir",
            default="grantnav_data",
        )

        parser.add_argument(
            "--indent-json",
            action="store",
            dest="indent",
            type=int,
            help="Indentation of JSON output",
            default=None,
        )

    def handle(self, *args, **options):
        """Create data package with the structure:

        - data_all.json (all sources)
        - json_all/
              |- grants.json (contains lists of grants)
              |- grants.json
              |...
        - funders.jl
        - recipients.jl
        """
        spinner = Spinner()
        spinner.start()

        latest_data = Latest.objects.get(series=Latest.CURRENT)

        # Create the data_all json file
        os.makedirs("%s/json_all/" % options["dir"], mode=0o700)

        data_all = []

        data_all_file = "%s/data_all.json" % options["dir"]
        recipients_file = "%s/recipients.jl" % options["dir"]
        funders_file = "%s/funders.jl" % options["dir"]

        with open(funders_file, "w") as funders_fp:
            create_orgs_list("funder", funders_fp)

        with open(recipients_file, "w") as recipients_fp:
            create_orgs_list("recipient", recipients_fp)

        def flatten_grant(in_grant):
            """Add the additional_data inside grant object"""
            out_grant = {}
            out_grant.update(in_grant["data"])
            try:
                out_grant["additional_data"] = in_grant["additional_data"]
            except KeyError:
                # additional_data isn't required and is not available
                pass

            return out_grant

        for source in latest_data.sourcefile_set.all():
            data_all.append(source.data)

            grant_file_name = "%s/json_all/%s.json" % (
                options["dir"],
                source.data["identifier"],
            )

            # Write out grant data
            with open(grant_file_name, "w") as grantfp:

                grants_list = list(
                    source.grant_set.all().values("data", "additional_data")
                )

                grants_list_flattened = map(flatten_grant, grants_list)

                grants = {"grants": list(grants_list_flattened)}

                grantfp.write(json.dumps(grants, indent=options["indent"]))

        with open(data_all_file, "w+") as data_all_fp:
            data_all_fp.write(json.dumps(data_all, indent=options["indent"]))

        spinner.stop()
