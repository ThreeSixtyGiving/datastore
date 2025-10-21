import json
import os
from typing import Dict, Any

from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

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

    def check_grant_data_tools_compatible(
        self, grant: Dict[str, Any], distribution_url: [str], publisher_name: [str]
    ) -> bool:
        """
        Some Grants contain data that is valid according to the current standard, but not acceptable to tooling
        e.g. will cause errors when trying to process or render the data.
        This method checks for such data, with the goal of excluding unacceptable Grants from our dataset.

        Checks made are:
        - Does the Grant ID contain newline characters
        - Does any Org IDs contain newline characters
        """
        try:
            # Does Grant ID contain newlines?
            grant_id = grant["id"]

            def log_problem_char(field, value):
                # json.dumps() the grant id to escape any unexpected characters
                value = json.dumps(value)
                grant_id_esc = json.dumps(grant_id)
                funding_org_name = grant["fundingOrganization"][0]["name"]

                print(
                    f"ProblemChar, {grant_id_esc}, {field}, {value}, {funding_org_name}, {publisher_name}, {distribution_url}, skipping grant",
                    file=self.stdout,
                )

            if "\n" in grant_id:
                log_problem_char("grant_id", grant_id)
                return False

            # Does any Org ID contain newlines?
            # Note we don't check Publisher Org ID because that's not part of the original grant data

            try:
                recipient_org_ids = [
                    ro["id"] for ro in grant["recipientOrganization"] if "id" in ro
                ]

                for org_id in recipient_org_ids:
                    if "\n" in org_id:
                        log_problem_char("recipientOrganization id", org_id)
                        return False

            except KeyError:
                pass

            funding_org_ids = [
                fo["id"] for fo in grant["fundingOrganization"] if "id" in fo
            ]

            for org_id in funding_org_ids:
                if "\n" in org_id:
                    log_problem_char("fundingOrganization id", org_id)
                    return False
        except Exception as e:
            print(
                "Error in check_grant_data_tools_compatible continuing anyway %s" % e,
                file=self.stderr,
            )

        return True

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

        # Clear out any previous datagetter run publishers
        db.Publisher.objects.all().delete()

        for ob in dataset:
            prefix = ob["publisher"]["prefix"]
            publisher, p_created = db.Publisher.objects.get_or_create(
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
                        additional_data = grant_additional_data_generator.create(
                            grant, source_file.data
                        )
                    except Exception as e:
                        print(
                            "Generating additional for grant %s failed %s"
                            % (grant["id"], e),
                            file=self.stderr,
                        )
                        additional_data = None

                    if self.check_grant_data_tools_compatible(
                        grant,
                        ob["distribution"][0]["downloadURL"],
                        ob["publisher"]["name"],
                    ):
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
