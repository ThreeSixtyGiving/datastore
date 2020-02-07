#!/usr/bin/env python3
import argparse
import copy
import json
import os
import random
import subprocess

# Generates some test data for loading into the data store
# requires pwgen binary

# For debug
# import pprint
# pp = pprint.PrettyPrinter(indent=2)

INDENT = 2
PUBLISHERS = 10
GRANTS_PER_PUBLISHER = 5


grant_template = {
    "id": "360G-example-c",
    "title": "Example title for this grant",
    "description": "Example grant description",
    "currency": "GBP",
    "amountAwarded": 25000,
    "awardDate": "2019-10-03T00:00:00+00:00",
    "plannedDates": [
        {"startDate": "2016-10-03", "endDate": "2017-02-15", "duration": 4}
    ],
    "recipientOrganization": [
        {
            "id": "360G-example-a",
            "name": "Receive an example grant",
            "streetAddress": "10 Downing street",
            "addressLocality": "LONDON",
            "addressCountry": "United Kingdom",
            "postalCode": "SW1 1AA",
        }
    ],
    "beneficiaryLocation": [
        {
            "name": "England; Scotland; Wales",
            "geoCode": "K02000001",
            "geoCodeType": "CTRY",
        }
    ],
    "fundingOrganization": [{"id": "GB-example-b", "name": "Funding for examples"}],
    "grantProgramme": [{"code": "00200200220", "title": "Example grants August 2019"}],
    "fromOpenCall": "Yes",
    "dateModified": "2019-08-03T00:00:00Z",
}

publisher_template = {
    "modified": "2018-08-03T10:26:34.000+0000",
    "distribution": [
        {
            "title": "Example",
            "downloadURL": "http://example.com/example.xlsx",
            "accessURL": "http://www.example.com/this-campaign",
        }
    ],
    "issued": "2016-07-15",
    "publisher": {
        "logo": "http://www.example.com/uploads/Logo.png",
        "website": "http://www.example.com/",
        "prefix": "360g-exmpl",
        "name": "The example publisher",
    },
    "datagetter_metadata": {
        "acceptable_license": True,
        "downloads": True,
        "file_size": 3359833,
        "file_type": "xlsx",
        "valid": True,
        "json": "data/json_all/aaaaaaaaaaaaaa.json",
        "datetime_downloaded": "2019-07-03T10:11:39+00:00",
    },
    "title": "Example grants",
    "identifier": "aaaaaaaaaaaaaaaaaa",
    "license": "https://creativecommons.org/licenses/by/4.0/",
    "description": "The grans from Example",
    "license_name": "Creative Commons Attribution 4.0",
}


def generate_data(output_dir="test-data"):
    os.makedirs("%s/json_all/" % output_dir)

    data_all = []

    words_needed = PUBLISHERS * PUBLISHERS * 3 + PUBLISHERS * GRANTS_PER_PUBLISHER * 2

    output = subprocess.check_output(["pwgen", "10", "%s" % words_needed])

    words = output.decode("utf-8").split("\n")

    for i in range(0, PUBLISHERS):
        data_item = copy.deepcopy(publisher_template)
        data_item["publisher"]["name"] = "The %s publisher" % words.pop()
        data_item["publisher"]["prefix"] = "360g-%s" % words.pop()
        identifier = words.pop()
        data_item["identifier"] = identifier
        data_item["datagetter_metadata"]["json"] = "data/json_all/%s.json" % identifier

        grant_data = {"grants": []}

        for j in range(0, GRANTS_PER_PUBLISHER):
            grant = copy.deepcopy(grant_template)

            grant["id"] = "360G-%s" % words.pop()
            grant["title"] = "The %s grant" % words.pop()
            grant["amountAwarded"] = random.randint(10, 1000)

            grant_data["grants"].append(grant)

        with open("%s/json_all/%s.json" % (output_dir, identifier), "w") as grantf:
            json.dump(grant_data, grantf, indent=INDENT)

        data_all.append(data_item)

    # For debug use pp.pprint(data_all)

    with open("%s/data_all.json" % output_dir, "w") as out:
        json.dump(data_all, out, indent=INDENT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        type=str,
        action="store",
        dest="output_dir",
        default="test-data",
        help="The location of the test data output",
    )

    args = parser.parse_args()

    generate_data(args.output_dir)
