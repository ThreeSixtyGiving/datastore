import csv
import hashlib
import io
import zipfile
from datetime import datetime

import requests

from additional_data.models import NSPL, GeoCodeName

# Code based on https://github.com/drkane/find-that-postcode/blob/main/findthatpostcode/commands/postcodes.py


class NSPLSource(object):
    """Imports NSPL (National Statistics Postcode Lookup) data and
    outputs 'recipientOrganization' location data into additional_data"""

    # Current url is August 2023 data based on 2021 Cencus, taken from:
    #  https://geoportal.statistics.gov.uk/datasets/national-statistics-postcode-lookup-2021-census-august-2023/about
    # To find the latest when it updates, have a look on the gov statistics geoportal:
    #  Search for the most recent "National Statistics Postcode Lookup 2021 Cencus"
    #  https://geoportal.statistics.gov.uk/search?collection=Dataset&q=National%20Statistics%20Postcode%20Lookup%20-%202021%20Census&sort=-modified&source=office%20for%20national%20statistics&tags=national%20statistics%20postcode%20lookup%2C2021_cencus&type=csv%20collection
    NSPL_URL = "https://www.arcgis.com/sharing/rest/content/items/204e40244d4d4903ba1861d492f47d29/data"

    def __init__(self):
        self._nspl_cache = {}
        self._code_name_cache = {}

    def get_zipfile(self, url=NSPL_URL):
        r = requests.get(url, stream=True)

        return zipfile.ZipFile(io.BytesIO(r.content))

    def process_nspl_data(self, zip_file):

        for file in zip_file.filelist:
            if not file.filename.endswith(".csv") or not file.filename.startswith(
                "Data/multi_csv/NSPL"
            ):
                continue

            print("[postcodes] Opening %s" % file.filename)

            postcode_count = 0

            with zip_file.open(file, "r") as postcode_csv:

                postcode_csv = io.TextIOWrapper(postcode_csv)
                reader = csv.DictReader(postcode_csv)

                postcodes = []
                for record in reader:

                    # null any blank fields (or ones with a dummy code in)
                    for key in record:
                        if record[key] == "" or record[key] in [
                            "E99999999",
                            "S99999999",
                            "W99999999",
                            "N99999999",
                        ]:
                            record[key] = None

                    # date fields
                    for field in ["dointr", "doterm"]:
                        if record[field]:
                            date_field = datetime.strptime(record[field][:6], "%Y%m")
                            record[field] = str(date_field)

                    # latitude and longitude
                    for field in ["lat", "long"]:
                        if record[field]:
                            record[field] = float(record[field])
                            if record[field] == 99.999999:
                                record[field] = None
                    if record["lat"] and record["long"]:
                        record["location"] = {
                            "lat": record["lat"],
                            "lon": record["long"],
                        }

                    # integer fields
                    for field in [
                        "oseast1m",
                        "osnrth1m",
                        "usertype",
                        "osgrdind",
                        "imd",
                    ]:
                        if record[field]:
                            record[field] = int(record[field])

                    # add postcode hash
                    record["hash"] = hashlib.md5(
                        record["pcds"].lower().replace(" ", "").encode()
                    ).hexdigest()

                    postcodes.append(record)
                    postcode_count += 1

                self.save_nspl_data(postcodes)

                print("[postcodes] Processed %s postcodes" % postcode_count)

    def save_nspl_data(self, data):
        bulk_save = []

        for record in data:
            nspl_postcode = (
                record["pcd"]
                if record["pcd"]
                else record["pcd2"]
                if record["pcd2"]
                else record["pcds"]
            )
            postcode = "".join(nspl_postcode.split()).upper()
            bulk_save.append(NSPL(postcode=postcode, data=record))

        NSPL.objects.bulk_create(bulk_save)

    def import_nspl(self, url=NSPL_URL):
        """
        Example of a data db entry:
        {
            'ccg': 'S03000012', 'ced': None, 'cty': None, 'eer': 'S15000001', 'imd': 6808, 'lat': 57.101474,
            'pcd': 'AB1 0AA', 'pct': 'S03000012', 'pfa': 'S23000009', 'rgn': None, 'stp': None, 'ctry': 'S92000003',
            'hash': '3b7db6a231babf449f1c6d7a61ce317f', 'laua': 'S12000033', 'lep1': None, 'lep2': None,
            'long': -2.242851, 'nuts': 'S31000935', 'oa11': 'S00090303', 'park': None, 'pcd2': 'AB1  0AA',
            'pcds': 'AB1 0AA', 'pcon': 'S14000002', 'ttwa': 'S22000047', 'ward': 'S13002843', 'wz11': 'S34002990',
            'bua11': None, 'nhser': None, 'oac11': '1C3', 'calncv': None, 'dointr': '1980-01-01 00:00:00',
            'doterm': '1996-06-01 00:00:00', 'hlthau': 'S08000020', 'lsoa11': 'S01006514', 'msoa11': 'S02001237',
            'teclec': 'S09000001', 'buasd11': None, 'ru11ind': '3', 'location': {'lat': 57.101474, 'lon': -2.242851},
            'oseast1m': 385386, 'osgrdind': 1, 'osnrth1m': 801193, 'usertype': 0
        }
        Field names information can be found in NSPL User Guide at https://geoportal.statistics.gov.uk/
        """
        if NSPL.objects.exists():
            NSPL.objects.all().delete()

        zip_file = self.get_zipfile(url)
        self.process_nspl_data(zip_file)

    def get_location_data_by_postcode(self, postcode):
        format_postcode = "".join(postcode.split()).upper()
        try:
            return self._nspl_cache[format_postcode]
        except KeyError:
            try:
                nspl = NSPL.objects.get(postcode=format_postcode)
                self._nspl_cache[format_postcode] = nspl.data
                return nspl.data
            except NSPL.DoesNotExist:
                self._nspl_cache[format_postcode] = None
                pass

    def update_location_data_code_names(self, location_data):
        """Adds new entries to location data dict with code names."""
        for field_name, field_value in location_data.copy().items():
            if type(field_value) is not str:
                continue

            try:
                code_name_obj = self._code_name_cache[field_value]
                if code_name_obj is None:
                    continue
            except KeyError:
                try:
                    code_name_obj = GeoCodeName.objects.get(code=field_value)
                    self._code_name_cache[field_value] = code_name_obj
                except GeoCodeName.DoesNotExist:
                    self._code_name_cache[field_value] = None
                    continue

            code_name = code_name_obj.data.get("name")
            location_data["{}_name".format(field_name)] = code_name

        return location_data

    def update_additional_data(self, grant, additional_data):
        """
        Updates with 'recipientOrganizationLocation' based on it's postcode.
        It checks first the `recipientOrganization` `postalCode` in the grant.
        """
        recipient_orgs = grant.get("recipientOrganization", [])

        for recipient_org in recipient_orgs:
            postcode = recipient_org.get("postalCode")
            if postcode:
                location_data = self.get_location_data_by_postcode(postcode)
                if location_data:
                    self.update_location_data_code_names(location_data)
                    additional_data["recipientOrganizationLocation"] = location_data
                    break
