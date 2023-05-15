import datetime

from django.test import TestCase

from data_quality import quality_data
import db.models as db


class TestDataQualityData(TestCase):
    """Test creating data quality data"""

    fixtures = ["test_data.json"]
    maxDiff = None

    def test_create_data_quality_data(self):
        grant = db.Grant.objects.first()
        quality = quality_data.create({"grants": [grant.data]})

        # Our test data in the test_data.json currently generates 2
        # data quality usefulness results
        self.assertEqual(len(quality), 2)

    def test_create_sourcefile_publisher_quality_data(self):
        source_file = db.SourceFile.objects.get(pk=3)

        # Create source file aggregate and quality data
        grants_list = {
            "grants": list(source_file.grant_set.values_list("data", flat=True))
        }

        source_file.quality, source_file.aggregate = quality_data.create(grants_list)

        source_file.save()

        expected_sourcefile_aggregate = {
            "count": 5,
            "recipient_organisations": ["360G-example-a"],
            "recipient_individuals": 0,
            "funders": ["GB-example-b"],
            "max_award_date": "2019-10-03",
            "min_award_date": "2019-10-03",
            "currencies": {
                "GBP": {
                    "count": 5,
                    "total_amount": 1341,
                    "max_amount": 583,
                    "min_amount": 92,
                    "currency_symbol": "&pound;",
                }
            },
            "award_years": {"2019": 5},
            "recipient_org_types": {},
        }
        expected_sourcefile_quality = {
            "RecipientOrg360GPrefix": {
                "heading": "5 recipient organisation grants have a <span class=\"highlight-background-text\">Recipient Org:Identifier</span> that starts '360G-'",
                "count": 5,
                "percentage": 1.0,
                "fail": True,
            },
            "FundingOrg360GPrefix": {"count": 0, "fail": False},
            "NoRecipientOrgCompanyCharityNumber": {
                "heading": '5 recipient organisation grants do not have either a <span class="highlight-background-text">Recipient Org:Company Number</span> or a <span class="highlight-background-text">Recipient Org:Charity Number</span>',
                "count": 5,
                "percentage": 1.0,
                "fail": True,
            },
            "IndividualsCodeListsNotPresent": {"count": 0, "fail": False},
            "IncompleteRecipientOrg": {"count": 0, "fail": False},
            "NoGrantProgramme": {"count": 0, "fail": False},
            "NoBeneficiaryLocation": {"count": 0, "fail": False},
            "TitleDescriptionSame": {"count": 0, "fail": False},
            "TitleLength": {"count": 0, "fail": False},
            "NoLastModified": {"count": 0, "fail": False},
            "NoDataSource": {
                "heading": '5 grants do not have <span class="highlight-background-text">Data Source</span> information',
                "count": 5,
                "percentage": 1.0,
                "fail": True,
            },
            "ClassificationNotPresent": {
                "heading": "5 grants do not contain classifications field",
                "count": 5,
                "percentage": 1.0,
                "fail": True,
            },
            "BeneficiaryLocationNameNotPresent": {"count": 0, "fail": False},
            "BeneficiaryLocationCountryCodeNotPresent": {
                "heading": "5 grants do not contain beneficiaryLocation/0/countryCode field",
                "count": 5,
                "percentage": 1.0,
                "count": 5,
                "fail": True,
            },
            "BeneficiaryLocationGeoCodeNotPresent": {"count": 0, "fail": False},
            "PlannedDurationNotPresent": {"count": 0, "fail": False},
            "GrantProgrammeTitleNotPresent": {"count": 0, "fail": False},
            # These two are odd because they're datastore-home-brew
            "RecipientOrgPrefixExternal": {
                "count": 0,
                "fail": True,
                "heading": "Recipient Orgs with external org identifier",
                "percentage": 0.0,
            },
            "RecipientOrgPrefix50pcExternal": {
                "count": 2.5,
                "fail": True,
                "percentage": 1,
            },
        }

        self.assertEqual(
            expected_sourcefile_quality,
            source_file.quality,
            "Grant quality data not as expected",
        )
        self.assertEqual(
            expected_sourcefile_aggregate,
            source_file.aggregate,
            "Grant aggregate data not as expected",
        )

        # Create publisher aggregate and quality data

        publisher = source_file.get_publisher()

        (
            publisher.quality,
            publisher.aggregate,
        ) = quality_data.create_publisher_stats(publisher)

        publisher.save()

        current_year = datetime.date.today().year
        expected_publisher_aggregate = {
            "total": {
                "grants": 5,
                "GBP": 1341.0,
                "publishers": 1,
                "recipientOrganisations": 1,
                "recipientIndividuals": 0,
                "funders": 1,
            },
            "jsonFiles": 0,
            "csvFiles": 0,
            "xlsxFiles": 100,
            "odsFiles": 0,
            "awardYears": {
                str(year): (5 if year == 2019 else 0)
                for year in range(current_year, current_year - 10, -1)
            },
            "orgIdTypes": {},
            "awardedThisYear": 0,
            "awardedLastThreeMonths": 0,
        }
        expected_publisher_quality = {
            "hasBeneficiaryLocationName": 100,
            "hasRecipientOrgLocations": 100,
            "hasGrantDuration": 100,
            "hasGrantProgrammeTitle": 100,
            "hasGrantClassification": 0,
            "hasBeneficiaryLocationGeoCode": 100,
            "hasRecipientOrgCompanyOrCharityNumber": 0,
            "has50pcExternalOrgId": 0,
        }

        self.assertEqual(publisher.aggregate, expected_publisher_aggregate)
        self.assertEqual(publisher.quality, expected_publisher_quality)
