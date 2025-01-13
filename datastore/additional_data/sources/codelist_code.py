import csv
import requests
from django.db import transaction

from additional_data.models import CodelistCode

code_lists_urls = [
    "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/grantToIndividualsPurpose.csv",
    "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/grantToIndividualsReason.csv",
    "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/regrantType.csv",
    "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/locationScope.csv",
    "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/geoCodeType.csv",
    # These codelists aren't yet processed
    # "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/countryCode.csv",
    # "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/currency.csv",
]


class CodeListSource(object):
    """Looks up codes from 360Giving codelists and gets the title value of the code
    responsible for field: codeListLookup
    """

    def import_codelists(self):
        with transaction.atomic():
            CodelistCode.objects.all().delete()

            for code_list_url in code_lists_urls:
                # list name = last item in split -4 to remove extension .csv
                list_name = code_list_url.split("/")[-1:][0][:-4]
                print(f"fetching codelist: {list_name}")
                with requests.get(code_list_url, stream=True) as r:
                    r.raise_for_status()
                    file_data = csv.DictReader(
                        r.iter_lines(decode_unicode=True), delimiter=","
                    )
                    for value in file_data:
                        # In https://github.com/ThreeSixtyGiving/standard/blob/main/codelists/geoCodeType.csv
                        # we have non unique codes with differing descriptions. We have to just take the first
                        # one we come accross to avoid an integrity error on the unique constraints.
                        # https://github.com/ThreeSixtyGiving/standard/issues/391
                        try:
                            CodelistCode.objects.get(
                                code=value["Code"], list_name=list_name
                            )
                        except CodelistCode.DoesNotExist:
                            CodelistCode.objects.create(
                                code=value["Code"],
                                title=value["Title"],
                                description=value["Description"],
                                list_name=list_name,
                            )

    def update_additional_data(self, grant, additional_data):
        # check All the fields in the grant data that use codelists and make
        # additional data field versions of them

        primaryGrantReason = ""
        secondaryGrantReason = ""
        grantPurpose = []
        regrantType = ""
        locationScope = ""
        beneficiary_geoCodeTypes = []
        recipient_organization_geoCodeType = ""
        funding_organization_geoCodeType = ""

        try:
            code = grant["toIndividualsDetails"]["primaryGrantReason"]
            primaryGrantReason = CodelistCode.objects.get(
                code=code, list_name="grantToIndividualsReason"
            ).title
        except (KeyError, CodelistCode.DoesNotExist):
            pass

        try:
            code = grant["toIndividualsDetails"]["secondaryGrantReason"]
            secondaryGrantReason = CodelistCode.objects.get(
                code=code, list_name="grantToIndividualsReason"
            ).title
        except (KeyError, CodelistCode.DoesNotExist):
            pass

        try:
            codes = grant["toIndividualsDetails"]["grantPurpose"]
            for code in codes:
                grantPurpose.append(
                    CodelistCode.objects.get(
                        code=code, list_name="grantToIndividualsPurpose"
                    ).title
                )
        except (KeyError, CodelistCode.DoesNotExist):
            pass

        try:
            code = grant["regrantType"]
            regrantType = CodelistCode.objects.get(
                code=code, list_name="regrantType"
            ).title
        except (KeyError, CodelistCode.DoesNotExist):
            pass

        try:
            code = grant["locationScope"]
            locationScope = CodelistCode.objects.get(
                code=code, list_name="locationScope"
            ).title
        except (KeyError, CodelistCode.DoesNotExist):
            pass

        for location in grant["beneficiaryLocation"]:
            try:
                code = location["geoCodeType"]
                if code_title := CodelistCode.objects.get(
                    code=location["geoCodeType"], list_name="geoCodeType"
                ).title:
                    beneficiary_geoCodeTypes.append(code_title)

            except (KeyError, IndexError, CodelistCode.DoesNotExist):
                continue

        try:
            code = grant["fundingOrganization"][0]["location"][0]["geoCodeType"]
            funding_organization_geoCodeType = CodelistCode.objects.get(
                code=code, list_name="geoCodeType"
            ).title
        except (KeyError, IndexError, CodelistCode.DoesNotExist):
            pass

        try:
            code = grant["recipientOrganization"][0]["location"][0]["geoCodeType"]
            recipient_organization_geoCodeType = CodelistCode.objects.get(
                code=code, list_name="geoCodeType"
            ).title
        except (KeyError, IndexError, CodelistCode.DoesNotExist):
            pass

        additional_data["codeListLookup"] = {
            "toIndividualsDetails": {
                "primaryGrantReason": primaryGrantReason,
                "secondaryGrantReason": secondaryGrantReason,
                "grantPurpose": grantPurpose,
            },
            "regrantType": regrantType,
            "locationScope": locationScope,
            "geoCodeType": {
                "beneficiaryLocations": beneficiary_geoCodeTypes,
                "recipientOrganization0": recipient_organization_geoCodeType,
                "fundingOrganization0": funding_organization_geoCodeType,
            },
        }
