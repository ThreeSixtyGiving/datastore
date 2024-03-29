import requests_mock
from pathlib import PurePath
from django.test import TestCase

from additional_data.models import GeoLookup
from additional_data.sources.geo_lookup import GeoLookupSource
from db.models import Grant

test_files_dir = PurePath(__file__).parent.joinpath("files").joinpath("geolookups")


class TestAdditionalDataGeoLookup(TestCase):
    fixtures = ["test_data.json"]
    EXISTING_AREA = "E01011964"
    TOTAL_GEOLOOKUPS = 821

    def mock_csv_downloads(self, m):
        # Import Geo lookups data.
        for areatype, a in GeoLookupSource.SOURCE_URLS.items():
            # mock the CSV downloads
            url_filename = a["url_lookup"].split("/")[-1]
            with open(test_files_dir.joinpath(url_filename), "r") as infile:
                m.get("{}".format(a["url_lookup"]), text=infile.read())

            if a.get("url_latlong"):
                url_filename = a["url_latlong"].split("/")[-1]
                with open(test_files_dir.joinpath(url_filename), "r") as infile:
                    m.get("{}".format(a["url_latlong"]), text=infile.read())

    def test_import_geolookups_with_data(self):
        geo = GeoLookupSource()

        with requests_mock.Mocker() as m:
            self.mock_csv_downloads(m)

            geo.import_geo_lookups()

            self.assertEqual(len(GeoLookup.objects.all()), self.TOTAL_GEOLOOKUPS)

            # check one example
            geo_object = GeoLookup.objects.filter(areacode=self.EXISTING_AREA)
            self.assertTrue(len(geo_object), 1)
            self.assertEqual(geo_object[0].data["areaname"], "Hartlepool 007B")
            self.assertEqual(
                round(geo_object[0].data["latitude"], 5), round(54.684671337771334, 5)
            )
            self.assertEqual(geo_object[0].data["areatype"], "lsoa")
            self.assertEqual(geo_object[0].data["rgncd"], "E12000001")
            # {
            #   "ewcd": "K04000001",
            #   "ewnm": "England and Wales",
            #   "gbcd": "K03000001",
            #   "gbnm": "Great Britain",
            #   "ukcd": "K02000001",
            #   "uknm": "United Kingdom",
            #   "ladcd": "E06000001",
            #   "ladnm": "Hartlepool",
            #   "rgncd": "E12000001",
            #   "rgnnm": "North East",
            #   "ctrycd": "E92000001",
            #   "ctrynm": "England",
            #   "msoacd": "E02002489",
            #   "msoanm": "Hartlepool 007",
            #   "utlacd": "E06000001",
            #   "utlanm": "Hartlepool",
            #   "cauthcd": "E47000006",
            #   "cauthnm": "Tees Valley",
            #   "areacode": "E01011964",
            #   "areaname": "Hartlepool 007B",
            #   "areatype": "lsoa",
            #   "latitude": 54.684671337771334,
            #   "lsoa11cd": "E01011964",
            #   "lsoa11nm": "Hartlepool 007B",
            #   "lsoa21cd": "E01011964",
            #   "msoa11cd": "E02002489",
            #   "msoa11nm": "Hartlepool 007",
            #   "longitude": -1.223763133596042,
            #   "msoahclnm": "Old Town & Grange",
            #   "msoa11hclnm": "Old Town & Grange",
            #   "ladcd_active": "E06000001",
            #   "ladnm_active": "Hartlepool"
            # }

    def test_import_geolookup_deletes_previous_records(self):
        # When import_geo_lookups is run, should delete NSPL model data.
        geo = GeoLookupSource()

        with requests_mock.Mocker() as m:
            self.mock_csv_downloads(m)

            geo.import_geo_lookups()

            self.assertEqual(len(GeoLookup.objects.all()), self.TOTAL_GEOLOOKUPS)

            # check one example
            self.assertTrue(
                GeoLookup.objects.filter(areacode=self.EXISTING_AREA).first()
            )

            geo.import_geo_lookups()
            self.assertEqual(len(GeoLookup.objects.all()), self.TOTAL_GEOLOOKUPS)

    def save_mock_data(self):
        geo = GeoLookupSource()
        with requests_mock.Mocker() as m:
            self.mock_csv_downloads(m)
            geo.import_geo_lookups()

    def test_nspl_update_additional_data_beneficiaryLocation(self):
        self.save_mock_data()
        grant = Grant.objects.first()
        grant.data["beneficiaryLocation"][0]["geoCode"] = self.EXISTING_AREA

        additional_data = {}
        geo = GeoLookupSource()
        geo.update_additional_data(grant.data, additional_data)

        self.assertIn("locationLookup", additional_data)
        self.assertEqual(
            additional_data["locationLookup"][0]["areaname"],
            GeoLookup.objects.get(areacode=self.EXISTING_AREA).data["areaname"],
        )
        self.assertEqual(
            round(additional_data["locationLookup"][0]["latitude"], 5),
            round(
                GeoLookup.objects.get(areacode=self.EXISTING_AREA).data["latitude"], 5
            ),
        )

    def test_nspl_update_additional_data_beneficiaryLocation_prioritised(self):
        self.save_mock_data()
        grant = Grant.objects.first()
        grant.data["beneficiaryLocation"][0]["geoCode"] = self.EXISTING_AREA
        grant.data["recipientOrganization"][0]["location"] = [
            {"geoCode": self.EXISTING_AREA}
        ]
        additional_data = {
            "recipientOrganizationLocation": {"lsoa11": self.EXISTING_AREA}
        }

        geo = GeoLookupSource()
        geo.update_additional_data(grant.data, additional_data)

        self.assertIn("locationLookup", additional_data)
        self.assertEqual(
            len(additional_data["locationLookup"]),
            1,
        )

    def test_nspl_update_additional_data_recipientOrganization(self):
        self.save_mock_data()
        grant = Grant.objects.first()
        del grant.data["beneficiaryLocation"]
        grant.data["recipientOrganization"][0]["location"] = [
            {"geoCode": self.EXISTING_AREA}
        ]

        additional_data = {}
        geo = GeoLookupSource()
        geo.update_additional_data(grant.data, additional_data)

        self.assertIn("locationLookup", additional_data)
        self.assertEqual(
            additional_data["locationLookup"][0]["areaname"],
            GeoLookup.objects.get(areacode=self.EXISTING_AREA).data["areaname"],
        )
        self.assertEqual(
            round(additional_data["locationLookup"][0]["latitude"], 5),
            round(
                GeoLookup.objects.get(areacode=self.EXISTING_AREA).data["latitude"], 5
            ),
        )

    def test_nspl_update_additional_data_recipientOrganizationLocation(self):
        self.save_mock_data()
        grant = Grant.objects.first()
        del grant.data["beneficiaryLocation"]

        additional_data = {
            "recipientOrganizationLocation": {"lsoa11": self.EXISTING_AREA}
        }
        geo = GeoLookupSource()
        geo.update_additional_data(grant.data, additional_data)

        self.assertIn("locationLookup", additional_data)
        self.assertEqual(
            additional_data["locationLookup"][0]["areaname"],
            GeoLookup.objects.get(areacode=self.EXISTING_AREA).data["areaname"],
        )
        self.assertEqual(
            round(additional_data["locationLookup"][0]["latitude"], 5),
            round(
                GeoLookup.objects.get(areacode=self.EXISTING_AREA).data["latitude"], 5
            ),
        )
