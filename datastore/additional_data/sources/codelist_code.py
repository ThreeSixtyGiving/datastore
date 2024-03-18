import csv
import requests

from additional_data.models import CodelistCode

code_lists_urls = [
    "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/grantToIndividualsPurpose.csv",
    "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/grantToIndividualsReason.csv",
    "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/regrantType.csv",
    # These lists aren't yet ready for use in the datastore
    # https://github.com/ThreeSixtyGiving/standard/issues/348
    # https://github.com/ThreeSixtyGiving/standard/issues/349
    # "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/countryCode.csv",
    # "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/currency.csv",
    # "https://raw.githubusercontent.com/ThreeSixtyGiving/standard/main/codelists/geoCodeType.csv",
]


class CodeListSource(object):
    """Looks up codes from 360Giving codelists and gets the title value of the code
    responsible for field: codeListLookup
    """

    def import_codelists(self):
        CodelistCode.objects.all().delete()

        for code_list_url in code_lists_urls:
            # list name = last item in split -4 to remove extension .csv
            list_name = code_list_url.split("/")[-1:][0][:-4]
            with requests.get(code_list_url, stream=True) as r:
                r.raise_for_status()
                file_data = csv.DictReader(
                    r.iter_lines(decode_unicode=True), delimiter=","
                )
                for value in file_data:
                    CodelistCode.objects.create(
                        code=value["Code"],
                        title=value["Title"],
                        description=value["Description"],
                        list_name=list_name,
                    )

    def update_additional_data(self, grant, additional_data):
        # check All the fields in the grant data that use codelists and make additional data field versions of them

        primaryGrantReason = ""
        secondaryGrantReason = ""
        grantPurpose = []
        regrantType = ""

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

        additional_data["codeListLookup"] = {
            "toIndividualsDetails": {
                "primaryGrantReason": primaryGrantReason,
                "secondaryGrantReason": secondaryGrantReason,
                "grantPurpose": grantPurpose,
            },
            "regrantType": regrantType,
        }
