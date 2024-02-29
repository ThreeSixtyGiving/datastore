import json
import os
from django.db import transaction
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache

import db.models as db
from additional_data.generator import AdditionalDataGenerator
from db.management.spinner import Spinner


class Command(BaseCommand):
    help = "Loads data that has been downloaded and processed by the datagetter"

    def add_arguments(self, parser):
        parser.add_argument(
            type=str,
            nargs=1,
            action="store",
            dest="data_dir",
            help="The location of the data dir",
        )

        parser.add_argument(
            "--skip-missing",
            action="store_true",
            help="Skip any missing dataset files instead of raising an error",
            default=False,
        )

    def check_dir_looks_right(self):
        """Quickly check if the supplied dir looks correct"""
        ls = os.listdir(self.options["data_dir"][0])

        if "data_all.json" not in ls or "json_all" not in ls:
            raise CommandError(
                "%s doesn't look like the right dir expecting"
                " atleast data_all.json and data_all dir" % self.options["data_dir"][0]
            )

    def load_dataset_data(self):
        """Loads the dataset data which describes the grant data"""
        path = os.path.join(self.options["data_dir"][0], "data_all.json")
        with open(path, encoding="utf-8") as f:
            return json.loads(f.read())

    def load_grant_data(self, path):
        """return the grant json for the given path"""

        # As we want to use the path given by option to the command
        # reconstruct the file path with this value

        filename = os.path.split(path)[-1]
        print("Loading %s" % filename, file=self.stdout)

        new_path = os.path.join(self.options["data_dir"][0], "json_all", filename)

        try:
            with open(new_path, encoding="utf-8") as f:
                return json.loads(f.read())
        except FileNotFoundError as e:
            if self.options["skip_missing"]:
                return {"grants": []}
            else:
                raise e

    def load_data(self):
        grant_additional_data_generator = AdditionalDataGenerator()
        grants_added = 0
        dataset = self.load_dataset_data()

        getter_run = db.GetterRun.objects.create()

        for ob in dataset:
            prefix = ob["publisher"]["prefix"]
            publisher, c = db.Publisher.objects.get_or_create(
                getter_run=getter_run,
                prefix=prefix,
                data=ob["publisher"],
                org_id=ob["publisher"].get("org_id", "unknown"),
                name=ob["publisher"]["name"],
                source=db.Entity.PUBLISHER,
            )

            source_file = db.SourceFile.objects.create(data=ob, getter_run=getter_run)

            try:
                grant_data = self.load_grant_data(ob["datagetter_metadata"]["json"])

                grant_bulk_insert = []

                for grant in grant_data["grants"]:
                    try:
                        additional_data = grant_additional_data_generator.create(grant)
                    except Exception as e:
                        print(
                            "Generating additional for grant %s failed %s"
                            % (grant["id"], e),
                            file=self.stderr,
                        )
                        additional_data = None

                    grant_bulk_insert.append(
                        db.Grant.from_data(
                            source_file=source_file,
                            publisher=publisher,
                            data=grant,
                            additional_data=additional_data,
                            getter_run=getter_run,
                        )
                    )

                db.Grant.objects.bulk_create(grant_bulk_insert)
                grants_added = grants_added + len(grant_data["grants"])

            except (FileNotFoundError, KeyError, TypeError, json.JSONDecodeError) as e:
                print(
                    "Skipping loading due to: '%s'" % e,
                    file=self.stdout,
                )
                # For debug    raise e
                continue

        return grants_added

    def handle(self, *args, **options):
        self.options = options
        grants_added = 0

        self.check_dir_looks_right()

        spinner = Spinner()
        spinner.start()

        with transaction.atomic():
            grants_added = self.load_data()

        spinner.stop()
        print("\nData loaded: %s grants added" % grants_added, file=self.stdout)

        print("Updating Latest", file=self.stdout)
        db.Latest.update()

        print("Updating quality data", file=self.stdout)
        call_command("rewrite_quality_data", "latest")
        # Update entities data for funders and recipients
        call_command("manage_entities_data", "--update")

        # Clear all cached objects - The latest data as well as new data has been added
        cache.clear()
