import requests_mock
from pathlib import PurePath
from django.test import TestCase

from additional_data.models import GeoCodeName
from additional_data.sources.geocode_names import GeoCodeNamesSource

test_files_dir = PurePath(__file__).parent.joinpath("files")


class TestAdditionalDataCodeNames(TestCase):
    def test_import_code_names_with_data(self):
        code_names = GeoCodeNamesSource()

        with requests_mock.Mocker() as m:
            with open(
                test_files_dir.joinpath("code_names_with_data.zip"), "rb"
            ) as infile:
                # Change History Data url returns a zipfile. We are replacing the zipfile by mocking it.
                m.get("{}".format(code_names.CHD_URL), body=infile)
                code_names.import_code_names()

                self.assertEqual(len(GeoCodeName.objects.all()), 3)
                # check one example
                code_names_object = GeoCodeName.objects.filter(code="S12000015")
                self.assertTrue(len(code_names_object), 1)
                self.assertEqual(
                    code_names_object[0].data,
                    {
                        "code": "S12000015",
                        "name": "Fife",
                        "owner": "LGBC",
                        "active": False,
                        "entity": "S12",
                        "parent": None,
                        "date_end": "2018-02-01 00:00:00",
                        "areachect": 132502.5,
                        "areaehect": 137390.69,
                        "areaihect": 0.0,
                        "arealhect": 132502.5,
                        "successor": [],
                        "date_start": "2009-01-01 00:00:00",
                        "name_welsh": None,
                        "sort_order": "S12000015",
                        "equivalents": {"ons": "00QR"},
                        "predecessor": ["00QR"],
                        "statutory_instrument_id": "1111/1001",
                        "statutory_instrument_title": "GSS re-coding strategy",
                    },
                )

    def test_import_code_names_without_data(self):
        code_names = GeoCodeNamesSource()

        with requests_mock.Mocker() as m:
            with open(
                test_files_dir.joinpath("code_names_with_no_data.zip"), "rb"
            ) as infile:
                # Change History Data url returns a zipfile. We are replacing the zipfile by mocking it.
                m.get("{}".format(code_names.CHD_URL), body=infile)
                code_names.import_code_names()

                self.assertEqual(len(GeoCodeName.objects.all()), 0)

    def test_import_code_names_deletes_previous_records(self):
        # When import_code_names is run, should delete CodeName model data.
        code_names = GeoCodeNamesSource()

        with requests_mock.Mocker() as m:
            with open(
                test_files_dir.joinpath("code_names_with_data.zip"), "rb"
            ) as infile:
                # Change History Data url returns a zipfile. We are replacing the zipfile by mocking it.
                m.get("{}".format(code_names.CHD_URL), body=infile)
                code_names.import_code_names()

                self.assertTrue(GeoCodeName.objects.filter(code="S12000015").first())

                with open(
                    test_files_dir.joinpath("code_names_with_data_bis.zip"), "rb"
                ) as infile:
                    # Change History Data url returns a zipfile. We are replacing the zipfile by mocking it.
                    m.get("{}".format(code_names.CHD_URL), body=infile)
                    code_names.import_code_names()

                    self.assertEqual(len(GeoCodeName.objects.all()), 6)
                    self.assertFalse(
                        GeoCodeName.objects.filter(code="S12000015").first()
                    )
                    self.assertTrue(
                        GeoCodeName.objects.filter(code="E32000003").first()
                    )
