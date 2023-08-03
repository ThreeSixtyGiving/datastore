import csv
import io
import zipfile
from datetime import datetime

import requests

from additional_data.models import GeoCodeName

# based on 'import_chd' function in
# https://github.com/drkane/find-that-postcode/blob/master/findthatpostcode/commands/codes.py


class GeoCodeNamesSource(object):
    """Uses CHD (Change history data) at https://geoportal.statistics.gov.uk/ to obtain information about geo code names."""

    CHD_URL = "https://www.arcgis.com/sharing/rest/content/items/393a031178684c69973d0e416a862890/data"

    def __init__(self):
        pass

    def get_zipfile(self, url=CHD_URL):
        r = requests.get(url, stream=True)

        return zipfile.ZipFile(io.BytesIO(r.content))

    def process_date(self, value, date_format="%d/%m/%Y"):
        if value in ["", "n/a"]:
            return None
        date_time = datetime.strptime(value, date_format)
        return str(date_time)

    def process_float(self, value):
        if value in ["", "n/a"]:
            return None
        if not isinstance(value, str):
            return value
        value = value.replace(",", "")
        return float(value)

    def load_change_history(self, infile, areas):
        """
        Contains the change history for geographies, where new coding is being used, from x date onwards.
        """
        reader = csv.DictReader(io.TextIOWrapper(infile, "utf-8-sig"))
        for area in reader:
            areas[area["GEOGCD"]] = {
                "code": area["GEOGCD"],
                "name": area["GEOGNM"],
                "name_welsh": area["GEOGNMW"] if area["GEOGNMW"] else None,
                "statutory_instrument_id": area["SI_ID"] if area["SI_ID"] else None,
                "statutory_instrument_title": area["SI_TITLE"]
                if area["SI_TITLE"]
                else None,
                "date_start": self.process_date(area["OPER_DATE"], "%d/%m/%Y"),
                "date_end": self.process_date(area["TERM_DATE"], "%d/%m/%Y"),
                "parent": area["PARENTCD"] if area["PARENTCD"] else None,
                "entity": area["ENTITYCD"],
                "owner": area["OWNER"],
                "active": area["STATUS"] == "live",
                "areaehect": self.process_float(area["AREAEHECT"]),
                "areachect": self.process_float(area["AREACHECT"]),
                "areaihect": self.process_float(area["AREAIHECT"]),
                "arealhect": self.process_float(area["AREALHECT"]),
                "sort_order": area["GEOGCD"],
                "predecessor": [],
                "successor": [],
                "equivalents": {},
            }

    def load_changes(self, infile, areas):
        """
        Contains details of name changes since x date and includes the current and previous names as well as
        the operative date of those changes.
        """
        reader = csv.DictReader(io.TextIOWrapper(infile, "utf-8-sig"))

        for area in reader:
            if area["GEOGCD_P"] == "":
                continue
            if area["GEOGCD"] in areas:
                areas[area["GEOGCD"]]["predecessor"].append(area["GEOGCD_P"])
            if area["GEOGCD_P"] in areas:
                areas[area["GEOGCD_P"]]["successor"].append(area["GEOGCD"])

    def load_equivalents(self, infile, areas):
        """
        Contains both the current codes and names and the previous ONS, MHCLG, ODS/DH, Scottish and Welsh government code
        and name equivalents. Where available it also contains the appropriate code and name equivalents for geographies
        in the constituent countries.
        """
        equivalents_geo_codes = {
            "ons": ["GEOGCDO", "GEOGNMO"],
            "mhclg": ["GEOGCDD", "GEOGNMD"],
            "nhs": ["GEOGCDH", "GEOGNMH"],
            "scottish_government": ["GEOGCDS", "GEOGNMS"],
            "welsh_government": ["GEOGCDWG", "GEOGNMWG", "GEOGNMWWG"],
        }

        reader = csv.DictReader(io.TextIOWrapper(infile, "utf-8-sig"))
        for area in reader:
            if area["GEOGCD"] not in areas:
                continue
            for k, v in equivalents_geo_codes.items():
                if area[v[0]]:
                    areas[area["GEOGCD"]]["equivalents"][k] = area[v[0]]

    def get_areas(self, zip_file):
        areas = {}

        for file in zip_file.filelist:
            try:
                with zip_file.open("ChangeHistory.csv", "r") as infile:
                    self.load_change_history(infile, areas)

                with zip_file.open("Changes.csv", "r") as infile:
                    self.load_changes(infile, areas)

                with zip_file.open("Equivalents.csv", "r") as infile:
                    self.load_equivalents(infile, areas)
            except KeyError:
                continue

        print("[areas] Processed %s areas" % len(areas))
        return areas

    def save_data(self, areas):
        bulk_save = []

        for code, data in areas.items():
            bulk_save.append(GeoCodeName(code=code, data=data))

        GeoCodeName.objects.bulk_create(bulk_save)

    def import_code_names(self, url=CHD_URL):
        """
        Example of a data db entry:
        {
            'code': 'E32000002', 'name': 'Bexley and Bromley', 'name_welsh': None,
            'statutory_instrument_id': '1111/1001', 'statutory_instrument_title': 'GSS re-coding strategy',
            'date_start': datetime.datetime(2010, 5, 6, 0, 0), 'date_end': None, 'parent': 'E12000007',
            'entity': 'E32', 'owner': 'GLA', 'active': True, 'areaehect': None, 'areachect': None, 'areaihect': None,
            'arealhect': None, 'sort_order': 'E32000002', 'predecessor': [], 'successor': [],
            'equivalents': {'ons': 'E32000002'}
        }
        """
        zip_file = self.get_zipfile(url)
        areas = self.get_areas(zip_file)

        if GeoCodeName.objects.exists():
            GeoCodeName.objects.all().delete()

        self.save_data(areas)
