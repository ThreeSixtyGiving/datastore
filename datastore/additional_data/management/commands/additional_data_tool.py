import json

from django.core.management.base import BaseCommand

from additional_data.generator import AdditionalDataGenerator


class Command(BaseCommand):
    help = "Writes the additional_data object to ThreeSixtyGiving grant data JSON file"

    def add_arguments(self, parser):
        parser.add_argument(
            type=str,
            action="store",
            dest="grants_file",
            help="The JSON file that contains an array of ThreeSixtyGiving grant data",
        )

        parser.add_argument(
            "--license-name",
            action="store",
            dest="license_name",
            help="The name of the license under which this grant data is published",
        )

        parser.add_argument(
            "--license-url",
            action="store",
            dest="license",
            help="The URL of the license under which this grant data is published",
        )

    def handle(self, *args, **options):

        source_file = {}
        if options["license_name"]:
            source_file["license_name"] = options["license_name"]
        if options["license"]:
            source_file["license"] = options["license"]

        with open(options["grants_file"]) as grants_file:
            grants_json = json.load(grants_file)

            generator = AdditionalDataGenerator()

            for grant in grants_json["grants"]:
                additional_data = generator.create(grant, source_file)
                grant["additional_data"] = additional_data

            with open(options["grants_file"], "w") as grants_file:
                json.dump(grants_json, grants_file, indent=2)
