# An alternative to the test_data.json fixture
# These functions can be used to generate on-the-fly test data for
# tests that require more fine control or testing mutations e.g. Entities data
from datetime import timedelta, datetime, timezone, time
from django.db import transaction
from typing import TypedDict, Optional, Generator
from contextlib import contextmanager

import logging
import faker
import django.utils.timezone

from db.models import (
    SourceFile,
    GetterRun,
    Grant,
    Latest,
)
from db.management.commands.manage_entities_data import update_entities
from data_quality.management.commands.rewrite_quality_data import rewrite_quality_data
from monitoring.metrics import (
    gather_metrics,
)

logger = logging.getLogger(__name__)


@transaction.atomic
@contextmanager
def fake_getter_run(
    fake: faker.Faker,
    timestamp: Optional[datetime] = None,
    timestamp_dt: Optional[timedelta] = None,
) -> Generator[GetterRun, None, None]:
    """
    Context manager that creates a GetterRun 1 day after the last one, or at a
    random past date if there are no prior GetterRuns.
    Create Publishers, SourceFiles, Grants etc. inside the with block,
    the Latest & entities data will be updated at the end of the with block.

    Optionally provide timestamp to define the timestamp of the getterrun,
    or timestamp_dt as a timedelta since the last getterrun.
    """
    if timestamp is None:
        try:
            last_getter_run = GetterRun.latest()
            if timestamp_dt:
                timestamp = last_getter_run.datetime + timestamp_dt
            else:
                # If neither timestamp nor timestamp_dt are provided, set the timestamp
                # to quarter past midnight the following day.
                timestamp = datetime.combine(
                    last_getter_run.datetime.date() + timedelta(days=1),
                    time(hour=0, minute=15),
                    timezone.utc,
                )
        except GetterRun.DoesNotExist:
            # Start with a past date at least 30 days ago
            timestamp = datetime.combine(
                fake.date_object(django.utils.timezone.now() - timedelta(days=30)),
                time(hour=0, minute=15),
                timezone.utc,
            )

    getter_run = GetterRun.objects.create(datetime=timestamp)
    logger.info(f"Created Fake GetterRun {getter_run.id} @ {getter_run.datetime}")

    if getter_run.datetime > datetime.now(tz=timezone.utc):
        # Some tests break if you use future dates
        logger.error("Fake GetterRun exists in real future")

    yield getter_run

    # Update entities, metrics data etc after each GetterRun
    Latest.update()
    update_entities()
    # Race conditions seem to happen when running tests if threads are enabled
    rewrite_quality_data("latest", publisher_only=True, threads=0)
    gather_metrics()


class FakePublisherInfo(TypedDict):
    name: str
    prefix: str
    org_id: str
    logo: str
    website: str
    last_published: str


def fake_publisher_info(fake: faker.Faker) -> FakePublisherInfo:
    publisher_prefix = f"360GX-{fake.slug()}"
    publisher_info: FakePublisherInfo = {
        "name": fake.company(),
        "prefix": publisher_prefix,
        "logo": fake.image_url(),
        "org_id": f"XE-EXAMPLE-{publisher_prefix}",
        "website": fake.url(),
        "last_published": "2019-11-29",
    }

    return publisher_info


def fake_sourcefile(
    fake: faker.Faker,
    getter_run: GetterRun,
    publisher_info: FakePublisherInfo,
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
        "publisher": publisher_info,
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
                getter_run.datetime + timedelta(minutes=fake.random_int(1, 60))
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
        getter_run=getter_run,
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
    amount_awarded: Optional[int] = None,
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
        "amountAwarded": amount_awarded or fake.random_int(10000, 1000000, 10000),
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
        source_file=new_sourcefile,
        additional_data=grant.additional_data,
    )
    new_grant.save()
    return new_grant


def fake_grant_org(
    fake: faker.Faker,
):
    """Fake fundingOrganisation or recipientOrganisation that can be given to fake_grant"""
    return {"id": f"GB-CHC-9000{fake.random_int(100, 999)}", "name": fake.company()}
