import json

import requests_mock
from django.test import TestCase

from additional_data.models import NSPL
from additional_data.sources.code_names import CodeNamesSource
from additional_data.sources.nspl import NSPLSource
from db.models import Grant


class TestAdditionalDataNSPL(TestCase):
    fixtures = ["test_data.json"]
    EXITING_POSTCODE = "EX364AJ"

    def test_import_nspl_with_data(self):
        nspl = NSPLSource()

        with requests_mock.Mocker() as m:
            # Import NSPL data.
            with open("./datastore/tests/files/nspl_with_data.zip", "rb") as infile:
                # NSPL url returns a zipfile. We are replacing the zipfile by mocking it.
                m.get("{}".format(nspl.NSPL_URL), body=infile)
                nspl.import_nspl()

                self.assertEqual(len(NSPL.objects.all()), 6)

                # check one example
                nspl_object = NSPL.objects.filter(postcode=self.EXITING_POSTCODE)
                self.assertTrue(len(nspl_object), 1)
                self.assertEqual(
                    nspl_object[0].data,
                    {
                        "ccg": "E38000230",
                        "ced": "E58000298",
                        "cty": "E10000008",
                        "eer": "E15000009",
                        "imd": 10643,
                        "lat": 51.013971,
                        "pcd": "EX364AJ",
                        "pct": "E16000145",
                        "pfa": "E23000035",
                        "rgn": "E12000009",
                        "stp": "E54000037",
                        "ctry": "E92000001",
                        "hash": "406d4d87706c78d0cb4018521c82d56b",
                        "laua": "E07000043",
                        "lep1": "E37000016",
                        "lep2": None,
                        "long": -3.834169,
                        "nuts": "E05012435",
                        "oa11": "E00101959",
                        "park": None,
                        "pcd2": "EX36 4AJ",
                        "pcds": "EX36 4AJ",
                        "pcon": "E14000838",
                        "ttwa": "E30000162",
                        "ward": "E05012435",
                        "wz11": "E33049068",
                        "bua11": "E34002433",
                        "nhser": "E40000006",
                        "oac11": "8A1",
                        "calncv": "E56000014",
                        "dointr": "1980-01-01 00:00:00",
                        "doterm": None,
                        "hlthau": "E18000010",
                        "lsoa11": "E01020135",
                        "msoa11": "E02004187",
                        "teclec": "E24000032",
                        "buasd11": "E35999999",
                        "ru11ind": "D2",
                        "location": {"lat": 51.013971, "lon": -3.834169},
                        "oseast1m": 271433,
                        "osgrdind": 1,
                        "osnrth1m": 125445,
                        "usertype": 0,
                    },
                )

    def test_import_nspl_without_data(self):
        nspl = NSPLSource()

        with requests_mock.Mocker() as m:
            with open("./datastore/tests/files/nspl_with_no_data.zip", "rb") as infile:
                # NSPL url returns a zipfile. We are replacing the zipfile by mocking it.
                m.get("{}".format(nspl.NSPL_URL), body=infile)
                nspl.import_nspl()

                self.assertEqual(len(NSPL.objects.all()), 0)

    def test_import_nspl_deletes_previous_records(self):
        # When import_nspl is run, should delete NSPL model data.
        nspl = NSPLSource()

        with requests_mock.Mocker() as m:
            with open("./datastore/tests/files/nspl_with_data.zip", "rb") as infile:
                # NSPL url returns a zipfile. We are replacing the zipfile by mocking it.
                m.get("{}".format(nspl.NSPL_URL), body=infile)
                nspl.import_nspl()

                self.assertTrue(
                    NSPL.objects.filter(postcode=self.EXITING_POSTCODE).first()
                )

                with open(
                    "./datastore/tests/files/nspl_with_data_bis.zip", "rb"
                ) as infile:
                    # NSPL url returns a zipfile. We are replacing the zipfile by mocking it.
                    m.get("{}".format(nspl.NSPL_URL), body=infile)
                    nspl.import_nspl()

                    self.assertEqual(len(NSPL.objects.all()), 2)
                    self.assertFalse(
                        NSPL.objects.filter(postcode=self.EXITING_POSTCODE).first()
                    )
                    self.assertTrue(NSPL.objects.filter(postcode="CT11AA").first())

    def save_nspl_mock_data(self):
        with open("./datastore/tests/files/nspl_postcode.json") as infile:
            json_object = json.load(infile)
            for record in json_object:
                postcode = "".join(record["pcd"].split()).upper()
                NSPL.objects.create(postcode=postcode, data=record)

    def test_save_mock_data(self):
        self.save_nspl_mock_data()
        record = NSPL.objects.filter(postcode=self.EXITING_POSTCODE)
        self.assertEqual(len(record), 1)
        records = NSPL.objects.all()
        self.assertEqual(len(records), 15)

    def test_nspl_update_additional_data_with_existing_postcode_no_code_names(self):
        self.save_nspl_mock_data()

        grant = Grant.objects.first()
        # Add an existing postcode.
        grant.data["recipientOrganization"][0]["postalCode"] = self.EXITING_POSTCODE

        additional_data = {}
        nspl = NSPLSource()
        nspl.update_additional_data(grant.data, additional_data)

        self.assertIn("recipientOrganizationLocation", additional_data)
        self.assertEqual(
            additional_data["recipientOrganizationLocation"],
            NSPL.objects.get(postcode=self.EXITING_POSTCODE).data,
        )

    def test_nspl_update_additional_data_with_existing_postcode_with_code_names(self):
        # Import Code Names data.
        code_names = CodeNamesSource()
        with requests_mock.Mocker() as m:
            with open(
                "./datastore/tests/files/code_names_with_data.zip", "rb"
            ) as infile:
                # Change History Data url returns a zipfile. We are replacing the zipfile by mocking it.
                m.get("{}".format(code_names.CHD_URL), body=infile)
                code_names.import_code_names()

                self.save_nspl_mock_data()

                grant = Grant.objects.first()
                # Add an existing postcode.
                grant.data["recipientOrganization"][0][
                    "postalCode"
                ] = self.EXITING_POSTCODE

                additional_data = {}
                nspl = NSPLSource()
                nspl.update_additional_data(grant.data, additional_data)

                self.assertIn("recipientOrganizationLocation", additional_data)
                self.assertNotEqual(
                    additional_data["recipientOrganizationLocation"],
                    NSPL.objects.get(postcode=self.EXITING_POSTCODE).data,
                )
                self.assertEqual(
                    additional_data["recipientOrganizationLocation"]["cty"], "E10000008"
                )
                self.assertEqual(
                    additional_data["recipientOrganizationLocation"]["cty_name"],
                    "Devon",
                )

    def test_nspl_update_additional_data_with_not_existing_postcode(self):
        self.save_nspl_mock_data()

        grant = Grant.objects.first()
        # Add a non existing postcode.
        grant.data["recipientOrganization"][0]["postalCode"] = "AB10AA"

        additional_data = {}
        nspl = NSPLSource()
        nspl.update_additional_data(grant.data, additional_data)

        self.assertNotIn("recipientOrganizationLocation", additional_data)
        self.assertEqual(len(additional_data), 0)

    def test_nspl_update_additional_data_without_postcode(self):
        self.save_nspl_mock_data()

        grant = Grant.objects.first()
        # Delete the postcode key.
        grant.data["recipientOrganization"][0].pop("postalCode")

        additional_data = {}
        nspl = NSPLSource()
        nspl.update_additional_data(grant.data, additional_data)

        self.assertNotIn("recipientOrganizationLocation", additional_data)
        self.assertEqual(len(additional_data), 0)

    def test_nspl_update_additional_data_breaks_after_updating(self):
        # Once we have one recipient org location, the loop should break.
        self.save_nspl_mock_data()

        grant = Grant.objects.first()
        # Add an existing postcode.
        grant.data["recipientOrganization"][0]["postalCode"] = self.EXITING_POSTCODE

        additional_data = {"recipientOrgInfos": [{"postalCode": "EX364DE"}]}
        nspl = NSPLSource()
        nspl.update_additional_data(grant.data, additional_data)

        self.assertEqual(
            additional_data["recipientOrganizationLocation"],
            NSPL.objects.get(postcode=self.EXITING_POSTCODE).data,
        )
