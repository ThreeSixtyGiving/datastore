# An alternative to the test_data.json fixture
# These functions can be used to generate on-the-fly test data for
# tests that require more fine control or testing mutations e.g. Entities data
from datetime import timedelta, datetime, timezone
from typing import Dict, Any, TypedDict, NamedTuple, Literal, List, Optional
from contextlib import contextmanager

import faker


from db.models import (
    Publisher,
    Funder,
    SourceFile,
    GetterRun,
    Entity,
    Recipient,
    Grant,
    Latest,
)
from db.management.commands.manage_entities_data import update_entities
from monitoring.metrics import (
    gather_metrics,
    publisher_metrics,
    funder_metrics,
    source_file_metrics,
)
from monitoring.models import (
    PublisherMetricsRecord,
    FunderMetricsRecord,
    SourceFileMetricsRecord,
)


@contextmanager
def fake_getter_run(fake: faker.Faker, timestamp: Optional[datetime] = None):
    """
    Context manager that creates a GetterRun approx 1 day after the last one, or at a random date if none given.
    Create Publishers, SourceFiles and Grants inside the with block, and Latest & entities data will be updated after.
    """
    if timestamp is None:
        try:
            last_getter_run = GetterRun.latest()
            timestamp = last_getter_run.datetime + timedelta(
                hours=fake.random_int(22, 26)
            )
        except GetterRun.DoesNotExist:
            timestamp = fake.past_datetime(tzinfo=timezone.utc)

    getter_run = GetterRun.objects.create(datetime=timestamp)

    yield getter_run

    Latest.update()
    update_entities()
    gather_metrics()


def fake_publisher(fake: faker.Faker, getter_run: GetterRun) -> Publisher:
    publisher_aggregate = {
        "total": {
            "GBP": 2852197.0,
            "grants": 118,
            "funders": 1,
            "publishers": 1,
            "recipientIndividuals": 0,
            "recipientOrganisations": 82,
        },
        "csvFiles": 100,
        "odsFiles": 0,
        "jsonFiles": 0,
        "xlsxFiles": 0,
        "awardYears": {
            "2015": 0,
            "2016": 0,
            "2017": 0,
            "2018": 1,
            "2019": 12,
            "2020": 12,
            "2021": 21,
            "2022": 21,
            "2023": 29,
            "2024": 22,
        },
        "orgIdTypes": {
            "SC": 46760,
            "CHC": 305478,
            "COH": 197806,
            "EDU": 10601,
            "EIN": 1070,
            "LAE": 4454,
            "NHS": 1876,
            "NIC": 6790,
            "org": 1393,
            "UKPRN": 65188,
        },
        "awardedThisYear": 100,
        "awardedLastThreeMonths": 100,
    }

    publisher_quality = {
        "hasGrantDuration": 100,
        "has50pcExternalOrgId": 100,
        "hasGrantClassification": 0,
        "hasGrantProgrammeTitle": 0,
        "hasRecipientOrgLocations": 100,
        "hasBeneficiaryLocationName": 100,
        "hasBeneficiaryLocationGeoCode": 0,
        "hasRecipientOrgCompanyOrCharityNumber": 100,
    }

    publisher_prefix = fake.slug()
    publisher = Publisher.objects.create(
        org_id=f"XE-EXAMPLE-{publisher_prefix}",
        data={
            "name": fake.company(),
            "prefix": publisher_prefix,
        },
        aggregate=publisher_aggregate,
        quality=publisher_quality,
        getter_run=getter_run,
    )

    return publisher


def copy_publisher(
    fake: faker.Faker, publisher: Publisher, new_getter_run: GetterRun
) -> Publisher:
    return Publisher.objects.create(
        org_id=publisher.org_id,
        data=publisher.data,
        aggregate=publisher.aggregate,
        quality=publisher.quality,
        getter_run=new_getter_run,
    )


def fake_sourcefile(
    fake: faker.Faker,
    publisher: Publisher,
    valid: bool = True,
    downloads: bool = True,
) -> SourceFile:

    sf_data_year = fake.year()
    sf_data_org_name = fake.company()
    sf_data_title = (f"{sf_data_org_name} - community grants awarded {sf_data_year}",)
    sf_data = {
        "title": sf_data_title,
        "issued": f"{sf_data_year}-06-05",
        "license": "http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
        "modified": "2024-02-02T14:43:01.000+0000",
        "publisher": {
            "logo": fake.image_url(),
            "name": publisher.name,
            "org_id": publisher.org_id,
            "prefix": publisher.prefix,
            "website": fake.url(),
            "last_published": "2019-11-29",
        },
        "identifier": fake.uuid4(),
        "description": "",
        "distribution": [
            {
                "title": sf_data_title,
                "accessURL": fake.uri(),
                "downloadURL": fake.uri(),
            }
        ],
        "license_name": "Open Government Licence 3.0 (United Kingdom)",
        "datagetter_metadata": {
            "json": "/home/datastore/latest_datagetter//data/json_all/a001p00000z9ps2AAA.json",
            "valid": valid,
            "downloads": downloads,
            "file_size": 15545,
            "file_type": "xlsx",
            "acceptable_license": True,
            # "datetime_downloaded": "2024-12-01T00:02:41+00:00",
            "datetime_downloaded": (
                publisher.getter_run.datetime
                + timedelta(minutes=fake.random_int(1, 60))
            ).isoformat(),
        },
    }

    sf_quality = {
        "TitleLength": {"fail": False, "count": 0},
        "NoDataSource": {
            "fail": True,
            "count": 39,
            "heading": '100% of grants do not have <span class="highlight-background-text">Data Source</span> information',
            "percentage": 1.0,
        },
        "NoLastModified": {
            "fail": True,
            "count": 39,
            "heading": '100% of grants do not have <span class="highlight-background-text">Last Modified</span> information',
            "percentage": 1.0,
        },
        "NoGrantProgramme": {
            "fail": True,
            "count": 39,
            "heading": '100% of grants do not contain any <span class="highlight-background-text">Grant Programme</span> fields',
            "percentage": 1.0,
        },
        "FundingOrg360GPrefix": {"fail": False, "count": 0},
        "TitleDescriptionSame": {"fail": False, "count": 0},
        "NoBeneficiaryLocation": {"fail": False, "count": 0},
        "IncompleteRecipientOrg": {
            "fail": True,
            "count": 39,
            "heading": "100% of recipient organisation grants do not have recipient organisation location information",
            "percentage": 1.0,
        },
        "RecipientOrg360GPrefix": {
            "fail": False,
            "count": 22,
            "heading": "56% of recipient organisation grants have a <span class=\"highlight-background-text\">Recipient Org:Identifier</span> that starts '360G-'",
            "percentage": 0.5641025641025641,
        },
        "ClassificationNotPresent": {
            "fail": True,
            "count": 39,
            "heading": "100% of grants do not contain classifications/0/title field",
            "percentage": 1.0,
        },
        "PlannedDurationNotPresent": {
            "fail": True,
            "count": 39,
            "heading": "100% of grants do not contain plannedDates/0/duration or (plannedDates/startDate and plannedDates/endDate) field",
            "percentage": 1.0,
        },
        "RecipientOrgPrefixExternal": {
            "fail": False,
            "count": 17,
            "heading": "Recipient Orgs with external org identifier",
            "percentage": 0.4358974358974359,
        },
        "GrantProgrammeTitleNotPresent": {
            "fail": True,
            "count": 39,
            "heading": "100% of grants do not contain grantProgramme/0/title field",
            "percentage": 1.0,
        },
        "IndividualsCodeListsNotPresent": {"fail": False, "count": 0},
        "RecipientOrgPrefix50pcExternal": {
            "fail": True,
            "count": 8.5,
            "percentage": 0.4358974358974359,
        },
        "BeneficiaryLocationNameNotPresent": {"fail": False, "count": 0},
        "NoRecipientOrgCompanyCharityNumber": {"fail": False, "count": 0},
        "BeneficiaryLocationGeoCodeNotPresent": {"fail": False, "count": 0},
        "BeneficiaryLocationCountryCodeNotPresent": {
            "fail": True,
            "count": 39,
            "heading": "100% of grants do not contain beneficiaryLocation/0/countryCode field",
            "percentage": 1.0,
        },
    }

    sf_aggregate = {
        "count": 39,
        "funders": ["GB-LAE-OXO"],
        "currencies": {
            "GBP": {
                "count": 39,
                "max_amount": 190000,
                "min_amount": 1000,
                "total_amount": 782531,
                "currency_symbol": "&pound;",
            }
        },
        "award_years": {"2018": 39},
        "max_award_date": "2018-04-19",
        "min_award_date": "2018-02-13",
        "recipient_org_types": {"CHC": 15, "COH": 2},
        "recipient_individuals": 0,
        "recipient_organisations": [
            "360G-CHC-1032845",
            "360G-CHC-1049343",
            "360G-CHC-1055305",
            "360G-CHC-1055914",
            "360G-CHC-1063068",
            "360G-CHC-1084256",
            "360G-CHC-1123488",
            "360G-CHC-1140556",
            "360G-CHC-1150626",
            "360G-CHC-1160320",
            "360G-CHC-1161597",
            "360G-CHC-1173191",
            "360G-CHC-270852",
            "360G-CHC-274222",
            "360G-CHC-299903",
            "360G-CHC-313035",
            "360G-CHC-5138370",
            "360G-CHC-6835605",
            "360G-CHC-900039",
            "360G-OxfordCC-Cutteslowe-Seniors",
            "360G-OxfordCC-Oxford-International-Links",
            "360G-OxfordCC-Wood-Farm-Youth-Centre",
            "GB-CHC-1041014",
            "GB-CHC-1070805",
            "GB-CHC-1079495",
            "GB-CHC-1092265",
            "GB-CHC-1107094",
            "GB-CHC-1108612",
            "GB-CHC-1108679",
            "GB-CHC-1137129",
            "GB-CHC-1144821",
            "GB-CHC-1154860",
            "GB-CHC-1172048",
            "GB-CHC-273172",
            "GB-CHC-299533",
            "GB-COH-03591512",
            "GB-COH-09605591",
        ],
    }

    sourcefile = SourceFile.objects.create(
        data=sf_data,
        getter_run=publisher.getter_run,
        quality=sf_quality,
        aggregate=sf_aggregate,
    )
    return sourcefile


def copy_sourcefile(
    fake: faker.Faker,
    sourcefile: SourceFile,
    new_getter_run: GetterRun,
    valid: Optional[bool] = None,
    downloads: Optional[bool] = None,
    copy_grants: bool = False,
) -> SourceFile:
    # Update datagetter metadata with new download date to reflect new Getter Run
    sf_data = sourcefile.data.copy()
    datagetter_metadata = sf_data["datagetter_metadata"].copy()

    # "datetime_downloaded": "2024-12-01T00:02:41+00:00",
    datagetter_metadata["datetime_downloaded"] = (
        new_getter_run.datetime + timedelta(minutes=fake.random_int(1, 60))
    ).isoformat()

    # Override valid / downloads
    if valid is not None:
        datagetter_metadata["valid"] = valid

    if downloads is not None:
        datagetter_metadata["downloads"] = downloads

    sf_data["datagetter_metadata"] = datagetter_metadata

    new_sourcefile = SourceFile.objects.create(
        data=sf_data,
        getter_run=new_getter_run,
        quality=sourcefile.quality,
        aggregate=sourcefile.aggregate,
    )

    if copy_grants:
        for grant in sourcefile.grant_set.all():
            copy_grant(
                fake,
                grant=grant,
                new_sourcefile=new_sourcefile,
                new_getter_run=new_getter_run,
            )

    return new_sourcefile


class GrantOrganisation(TypedDict):
    id: str
    name: str


def fake_grant(
    fake: faker.Faker,
    sourcefile: SourceFile,
    funder: GrantOrganisation,
    recipient: GrantOrganisation,
) -> Grant:
    grant_id = f"{sourcefile.data['publisher']['prefix']}-{fake.uuid4()}"
    grant_award_date = fake.past_date(tzinfo=timezone.utc).isoformat()

    grant_data = {
        "id": grant_id,
        "title": fake.sentence(),
        "Website": {
            "Decision Notes": fake.sentence(),
            "Project Detail": fake.paragraph(),
        },
        "currency": "GBP",
        "awardDate": grant_award_date,
        "dataSource": fake.url(),
        "description": fake.paragraph(),
        "fromOpenCall": "Yes",
        "amountAwarded": fake.random_int(10000, 1000000, 10000),
        "grantProgramme": [
            {"code": "Open Programme", "title": fake.sentence()},
        ],
        "beneficiaryLocation": [{"name": fake.city()}],
        "fundingOrganization": [funder],
        "recipientOrganization": [recipient],
    }

    grant = Grant.from_data(
        data=grant_data,
        getter_run=sourcefile.getter_run,
        publisher=sourcefile.get_publisher(),
        source_file=sourcefile,
        additional_data={},
    )
    grant.save()
    return grant


def copy_grant(
    fake: faker.Faker,
    grant: Grant,
    new_getter_run: GetterRun,
    new_sourcefile: SourceFile,
) -> Grant:
    new_grant = Grant.from_data(
        data=grant.data,
        getter_run=new_getter_run,
        publisher=new_sourcefile.get_publisher(),
        source_file=new_sourcefile,
        additional_data=grant.additional_data,
    )
    new_grant.save()
    return new_grant
