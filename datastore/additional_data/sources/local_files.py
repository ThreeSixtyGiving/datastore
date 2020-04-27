import csv
import gzip
import json
import os

# Based on grantnav/import_to_elastic_search by David Raznick and Ben Webb
# https://github.com/ThreeSixtyGiving/grantnav/tree/master/dataload


class LocalFilesSource(object):
    """ Adds additional data to grant data """

    def __init__(self):
        self.id_name_org_mappings = {
            "fundingOrganization": {},
            "recipientOrganization": {},
        }

        self.data_files_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "data_files"
        )

        self.postcode_to_area = {}
        self.district_code_to_area = {}
        self.ward_code_to_area = {}
        self.district_name_to_code = {}

        self._setup_area_mappings()
        self._setup_charity_mappings()
        self._setup_org_name_mappings()

    def update_additional_data(self, grant, additional_data):
        self.update_additional_with_org_mappings(
            grant, "fundingOrganization", additional_data
        )
        self.update_additional_with_org_mappings(
            grant, "recipientOrganization", additional_data
        )
        self.update_additional_with_region(grant, additional_data)

    def _setup_charity_mappings(self):
        """ Setup info for charity names """

        with open(os.path.join(self.data_files_dir, "charity_names.json")) as fd:

            charity_names = json.load(fd)
        self.id_name_org_mappings["recipientOrganization"].update(charity_names)

    def _setup_org_name_mappings(self):
        """ Setup overrides for org name """

        with open(
            os.path.join(self.data_files_dir, "primary_funding_org_name.json")
        ) as fd:
            funding_org_name = json.load(fd)
        self.id_name_org_mappings["fundingOrganization"].update(funding_org_name)

    def _setup_area_mappings(self):
        """ Setup the area/district mappings """

        with open(
            os.path.join(self.data_files_dir, "codelist.csv")
        ) as codelist, gzip.open(
            os.path.join(self.data_files_dir, "codepoint_with_heading.csv.gz"), "rt"
        ) as codepoint:

            codelist_csv = csv.DictReader(codelist)
            code_to_name = {}
            for row in codelist_csv:
                code_to_name[row["code"]] = row["name"]

            codepoint_csv = csv.DictReader(codepoint)

            for row in codepoint_csv:
                district_code = row["Admin_district_code"]
                district_name = code_to_name.get(district_code, "").replace(" (B)", "")
                ward_code = row["Admin_ward_code"]
                ward_name = code_to_name.get(ward_code, "")

                regional_code = row["NHS_HA_code"]
                area_name = ""
                if not regional_code or regional_code[0] != "E":
                    country_code = row["Country_code"]
                    first_letter = country_code[0]
                    if first_letter == "S":
                        area_name = "Scotland"
                    if first_letter == "W":
                        area_name = "Wales"
                else:
                    area_name = code_to_name[regional_code]

                self.postcode_to_area[row["Postcode"].replace(" ", "").upper()] = {
                    "district_code": district_code,
                    "district_name": district_name,
                    "area_name": area_name,
                    "ward_name": ward_name,
                    "ward_code": ward_code,
                }
                self.district_code_to_area[district_code] = {
                    "district_code": district_code,
                    "district_name": district_name,
                    "area_name": area_name,
                }
                self.ward_code_to_area[ward_code] = {
                    "district_code": district_code,
                    "district_name": district_name,
                    "area_name": area_name,
                    "ward_name": ward_name,
                    "ward_code": ward_code,
                }

                self.district_name_to_code[district_name] = district_code

        # Northern Ireland codes and names not included in Code-Point, but uses a separate source
        with open(
            os.path.join(self.data_files_dir, "WD15_LGD15_NI_LU.csv")
        ) as ni_lookup:

            ni_lookup_csv = csv.DictReader(ni_lookup)

            for row in ni_lookup_csv:
                district_code = row["LGD15CD"]
                district_name = row["LGD15NM"].replace(" (B)", "")
                ward_code = row["WD15CD"]
                ward_name = row["WD15NM"]
                area_name = "Northern Ireland"

                self.district_code_to_area[district_code] = {
                    "district_code": district_code,
                    "district_name": district_name,
                    "area_name": area_name,
                }
                self.ward_code_to_area[ward_code] = {
                    "district_code": district_code,
                    "district_name": district_name,
                    "area_name": area_name,
                    "ward_name": ward_name,
                    "ward_code": ward_code,
                }

                self.district_name_to_code[district_name] = district_code

    def update_additional_with_org_mappings(self, grant, org_key, additional_data):
        mapping = self.id_name_org_mappings[org_key]
        orgs = grant.get(org_key, [])
        for org in orgs:
            org_id, name = org.get("id"), org.get("name")
            if not name:
                name = org_id
            if not org_id:
                return

            found_name = mapping.get(org_id)
            if not found_name:
                mapping[org_id] = name
                found_name = name
            additional_data["id_and_name"] = json.dumps([found_name, org_id])

    def _add_area_to_grant(self, area, additional_data):
        if area.get("ward_code"):
            additional_data["recipientWardNameGeoCode"] = area["ward_code"]
            additional_data["recipientWardName"] = self.ward_code_to_area.get(
                area["ward_code"], {}
            ).get("ward_name")
        if area["district_name"]:
            additional_data["recipientDistrictName"] = area["district_name"]
            additional_data[
                "recipientDistrictGeoCode"
            ] = self.district_name_to_code.get(area["district_name"])
        if area["area_name"]:
            additional_data["recipientRegionName"] = area["area_name"]

        additional_data["recipientLocation"] = " ".join(area.values())

    def update_additional_with_region(self, grant, additional_data):
        try:
            post_code = grant["recipientOrganization"][0]["postalCode"]
        except (KeyError, IndexError):
            post_code = ""

        # If there is a 'BT' postcode we can safely assume this is in NI
        if post_code and post_code.startswith("BT"):
            additional_data["recipientRegionName"] = "Northern Ireland"

        # test postcode first
        area = self.postcode_to_area.get(str(post_code).replace(" ", "").upper())
        if area:
            self._add_area_to_grant(area, additional_data)
            return

        if not area:
            try:
                locations = grant["recipientOrganization"][0]["location"]
            except (KeyError, IndexError):
                return

            # then test ward
            for location in locations:
                geoCode = location.get("geoCode")
                if geoCode and geoCode in self.ward_code_to_area:
                    self._add_area_to_grant(
                        self.ward_code_to_area.get(geoCode), additional_data
                    )
                    return

            # finally district
            for location in locations:
                geoCode = location.get("geoCode")
                if geoCode and geoCode in self.district_code_to_area:
                    self._add_area_to_grant(
                        self.district_code_to_area.get(geoCode), additional_data
                    )
                    return
                # No NI data but try and get name from data
                if geoCode and geoCode.startswith("N09"):
                    additional_data["recipientRegionName"] = "Northern Ireland"
                    additional_data["recipientDistrictName"] = location["name"]
