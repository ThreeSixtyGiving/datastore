import requests_mock
from django.test import TestCase

from additional_data.models import GeoLookup
from additional_data.sources.geo_lookup import GeoLookupSource
from db.models import Grant


class TestAdditionalDataGeoLookup(TestCase):
    fixtures = ["test_data.json"]
    EXISTING_AREA = "E01011964"

    def mock_csv_downloads(self, m):
        # Import Geo lookups data.
        for areatype, a in GeoLookupSource.SOURCE_URLS.items():

            # mock the CSV downloads
            url_filename = a["url_lookup"].split("/")[-1]
            with open(
                "./datastore/tests/files/geolookups/{}".format(url_filename), "r"
            ) as infile:
                m.get("{}".format(a["url_lookup"]), text=infile.read())

            if a.get("url_latlong"):
                url_filename = a["url_latlong"].split("/")[-1]
                with open(
                    "./datastore/tests/files/geolookups/{}".format(url_filename), "r"
                ) as infile:
                    m.get("{}".format(a["url_latlong"]), text=infile.read())

    def test_import_geolookups_with_data(self):
        geo = GeoLookupSource()

        with requests_mock.Mocker() as m:
            self.mock_csv_downloads(m)

            geo.import_geo_lookups()

            self.assertEqual(len(GeoLookup.objects.all()), 60)

            # check one example
            geo_object = GeoLookup.objects.filter(areacode=self.EXISTING_AREA)
            self.assertTrue(len(geo_object), 1)
            self.assertEqual(geo_object[0].data["areaname"], "Hartlepool 007B")
            self.assertEqual(
                round(geo_object[0].data["latitude"], 5), round(54.68510808262816, 5)
            )
            self.assertEqual(geo_object[0].data["areatype"], "lsoa")
            self.assertEqual(geo_object[0].data["rgncd"], "E12000001")
            # {
            #     "ewcd": "K04000001",
            #     "ewnm": "England and Wales",
            #     "gbcd": "K03000001",
            #     "gbnm": "Great Britain",
            #     "ukcd": "K02000001",
            #     "uknm": "United Kingdom",
            #     "ladcd": "E06000001",
            #     "ladnm": "Hartlepool",
            #     "rgncd": "E12000001",
            #     "rgnnm": "North East",
            #     "ctrycd": "E92000001",
            #     "ctrynm": "England",
            #     "utlacd": "E06000001",
            #     "utlanm": "Hartlepool",
            #     "cauthcd": "E47000006",
            #     "cauthnm": "Tees Valley",
            #     "lad17cd": "E06000001",
            #     "areacode": "E01011964",
            #     "areaname": "Hartlepool 007B",
            #     "areatype": "lsoa",
            #     "msoa11cd": "E02002489",
            #     "msoa11nm": "Hartlepool 007",
            #     "ttwa11cd": "E30000215",
            #     "ttwa11nm": "Hartlepool",
            #     "msoa11hclnm": "Old Town & Grange",
            #     "latitude": 54.68510808262816,
            #     "longitude": -1.223715283044111,
            # }

    def test_import_geolookup_deletes_previous_records(self):
        # When import_geo_lookups is run, should delete NSPL model data.
        geo = GeoLookupSource()

        with requests_mock.Mocker() as m:
            self.mock_csv_downloads(m)

            geo.import_geo_lookups()

            self.assertEqual(len(GeoLookup.objects.all()), 60)

            # check one example
            self.assertTrue(
                GeoLookup.objects.filter(areacode=self.EXISTING_AREA).first()
            )

            geo.import_geo_lookups()
            self.assertEqual(len(GeoLookup.objects.all()), 60)

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
