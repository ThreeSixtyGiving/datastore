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


@contextmanager
@transaction.atomic
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
    rewrite_quality_data("latest", threads=0)
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

    sourcefile = SourceFile.objects.create(
        data=sf_data,
        getter_run=getter_run,
        quality={},
        aggregate={},
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
    currency: str = "GBP",
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
        "currency": currency,
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
