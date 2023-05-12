import db.models as db

from lib360dataquality.cove.threesixtygiving import (
    USEFULNESS_TEST_CLASS,
    TEST_CLASSES,
    common_checks_360,
)
from lib360dataquality.cove.schema import Schema360
from lib360dataquality import check_field_present

from django.db.models import Sum
from django.db.models.expressions import RawSQL
from django.db import connection

from tempfile import TemporaryDirectory
from datetime import datetime, timedelta


def create(grants):
    """Creates data quality data for a set of grants
    grants: grants json"""

    cove_results = {"file_type": "json"}

    # Inject some extra tests to the default set of USEFULNESS TEST CLASS

    TEST_CLASSES[USEFULNESS_TEST_CLASS] = TEST_CLASSES[USEFULNESS_TEST_CLASS] + [
        check_field_present.ClassificationNotPresent,
        check_field_present.BeneficiaryLocationNameNotPresent,
        check_field_present.BeneficiaryLocationCountryCodeNotPresent,
        check_field_present.BeneficiaryLocationGeoCodeNotPresent,
        check_field_present.PlannedDurationNotPresent,
        check_field_present.GrantProgrammeTitleNotPresent,
        check_field_present.IndividualsCodeListsNotPresent,
    ]

    with TemporaryDirectory() as tempdir:
        common_checks_360(
            cove_results,
            tempdir,
            grants,
            Schema360(),
            test_classes=[USEFULNESS_TEST_CLASS],
        )

    # We don't quite want the result as-is from cove/lib360dataquality
    # our format is:
    # {
    #   "TestClassName": { "heading": "text", "count": n, "fail": false },
    #   ...
    # }
    # We only get results when a quality test finds an issue, so to provide a count 0
    # value we template out all the expected results with 0 from all the available tests.

    quality_results = {}

    # Create the template
    for available_test in TEST_CLASSES[USEFULNESS_TEST_CLASS]:
        quality_results[available_test.__name__] = {"count": 0, "fail": False}

    # Initialise two new tests
    # These will be derived from RecipientOrg360GPrefix
    quality_results["RecipientOrgPrefixExternal"] = {"count": 0, "fail": False}
    quality_results["RecipientOrgPrefix50pcExternal"] = {"count": 0, "fail": False}

    # Update with a heading and count template.
    for test in cove_results["usefulness_checks"]:
        quality_results[test[0]["type"]] = {
            "heading": test[0]["heading"],
            # The number of grants that failed the check
            "count": test[0]["count"],
            # The % of the relevant grants that failed the check
            "percentage": test[0]["percentage"],
            # If all the grants fail a test then we mark as fail true
            "fail": test[0]["percentage"] == 1.0,
        }

        # if "Individuals" in test[0]["type"]:
        #   print(test)

        if "RecipientOrg360GPrefix" in test[0]["type"]:
            # This test tells us the number and % of grants which use a 360G-something prefix
            # in the org-ids in the recipient organisation for a grant.
            #
            # We can use this test's data to fill in the data for the two new tests RecipientOrgPrefixExternal and RecipientOrgPrefix50pcExternal
            quality_results["RecipientOrgPrefix50pcExternal"] = {
                "fail": test[0]["percentage"] >= 0.5,
                "count": test[0]["count"] / 2,
                "percentage": 1,
            }

            grants_recipient_ext_org = (
                cove_results["grants_aggregates"]["count"]
                - cove_results["grants_aggregates"]["recipient_individuals_count"]
                - test[0]["count"]
            )
            quality_results["RecipientOrgPrefixExternal"] = {
                "count": grants_recipient_ext_org,
                "percentage": grants_recipient_ext_org
                / (
                    cove_results["grants_aggregates"]["count"]
                    - cove_results["grants_aggregates"]["recipient_individuals_count"]
                ),
                "fail": grants_recipient_ext_org == 0,
                "heading": "Recipient Orgs with external org identifier",
            }

    aggregates = {
        "count": cove_results["grants_aggregates"]["count"],
        "recipient_organisations": list(
            cove_results["grants_aggregates"]["distinct_recipient_org_identifier"]
        ),
        "recipient_individuals": cove_results["grants_aggregates"][
            "recipient_individuals_count"
        ],
        "funders": list(
            cove_results["grants_aggregates"]["distinct_funding_org_identifier"]
        ),
        "max_award_date": cove_results["grants_aggregates"]["max_award_date"],
        "min_award_date": cove_results["grants_aggregates"]["min_award_date"],
        "currencies": cove_results["grants_aggregates"]["currencies"],
        "award_years": cove_results["grants_aggregates"]["award_years"],
    }

    # Create a list of the org_id types e.g. COH with the count
    # e.g. recipient_org_types: { "COH": 20, "ABC": 12 }
    # TODO this could be added to dataquality if the aggregate mechanism were
    # extensible.

    aggregates["recipient_org_types"] = {}

    def extract_org_id_type(org_id):
        # Ignore internal org ids
        if org_id.lower().startswith("360g"):
            return None

        try:
            return org_id.split("-")[1]
        except IndexError:
            return None

    for grant in grants["grants"]:
        # skip if grant isn't for an organization
        if not grant.get("recipientOrganization"):
            continue

        org_id_type = extract_org_id_type(grant["recipientOrganization"][0]["id"])
        if org_id_type:
            try:
                aggregates["recipient_org_types"][org_id_type] += 1
            except KeyError:
                aggregates["recipient_org_types"][org_id_type] = 1

    return quality_results, aggregates


class SourceFilesStats(object):
    def __init__(self, source_file_set):
        self.source_file_set = source_file_set

        self.quality_query_parameters = {
            "hasBeneficiaryLocationName": {
                "quality__BeneficiaryLocationNameNotPresent__fail": False
            },
            "hasGrantDuration": {"quality__PlannedDurationNotPresent__fail": False},
            "hasGrantProgrammeTitle": {
                "quality__GrantProgrammeTitleNotPresent__fail": False
            },
            "hasGrantClassification": {
                "quality__ClassificationNotPresent__fail": False
            },
            "hasBeneficiaryLocationGeoCode": {
                "quality__BeneficiaryLocationGeoCodeNotPresent__fail": False
            },
        }

        # If a set of source files has 0 recipient organisations (i.e. 100% grants to individuals) these tests
        # are meaningless and will fail so don't output them.
        if self.get_total_recipient_organisations() > 0:
            self.quality_query_parameters.update(
                {
                    "hasRecipientOrgLocations": {
                        "quality__IncompleteRecipientOrg__fail": False
                    },
                    "hasRecipientOrgCompanyOrCharityNumber": {
                        "quality__NoRecipientOrgCompanyCharityNumber__fail": False
                    },
                    "has50pcExternalOrgId": {
                        "quality__RecipientOrgPrefix50pcExternal__fail": False
                    },
                }
            )

        if self.get_total_recipient_individuals() > 0:
            self.quality_query_parameters.update(
                {
                    "hasRecipientIndidualsCodelists": {
                        "quality__IndividualsCodeListsNotPresent__fail": False
                    },
                }
            )

        self.file_types = ["json", "csv", "xlsx", "ods"]

    def count(self):
        return self.source_file_set.count()

    def get_pc_total_file_types(self):
        """Returns the % of different file types"""
        ret = {}

        for file_type in self.file_types:
            ret["%sFiles" % file_type] = round(
                self.source_file_set.filter(
                    data__datagetter_metadata__file_type__contains=file_type
                ).count()
                / self.count()
                * 100
            )

        return ret

    def get_pc_publishers_file_types(self):
        """Returns the % publishers using different file types"""
        ret = {}

        for file_type in self.file_types:
            ret["%sFiles" % file_type] = round(
                self.source_file_set.filter(
                    data__datagetter_metadata__file_type__contains=file_type
                )
                .distinct("data__publisher__prefix")
                .count()
                / self.get_total_publishers()
                * 100
            )

        return ret

    def get_total_grants(self):
        return self.source_file_set.annotate(
            total=RawSQL("((aggregate->>%s)::int)", ("count",))
        ).aggregate(Sum("total"))["total__sum"]

    def get_total_gbp(self):
        try:
            total_gbp = float(
                self.source_file_set.annotate(
                    total=RawSQL(
                        "((aggregate->'currencies'->'GBP'->>%s)::float)",
                        ("total_amount",),
                    )
                ).aggregate(Sum("total"))["total__sum"]
            )
        except TypeError:
            # Happens if the source file has no GBP
            total_gbp = 0

        return total_gbp

    def get_total_publishers(self):
        return self.source_file_set.distinct("data__publisher__prefix").count()

    def get_total_recipient_organisations(self):
        # Determine if we're dealing with just one publisher and whether we need to limit
        # the source files to that publisher rather than all in 'latest'
        if self.source_file_set.distinct("data__publisher__prefix").count() == 1:
            source_file_ids = ",".join(
                map(str, self.source_file_set.values_list("id", flat=True))
            )
            query = f"""
            SELECT DISTINCT(jsonb_array_elements(db_sourcefile.aggregate->'recipient_organisations'))
            FROM db_sourcefile
            WHERE db_sourcefile.id IN ({source_file_ids})
            """
        else:
            latest_id = db.Latest.objects.get(series=db.Latest.CURRENT).pk
            query = f"""
            SELECT DISTINCT(jsonb_array_elements(db_sourcefile.aggregate->'recipient_organisations'))
            FROM db_sourcefile
            INNER JOIN db_sourcefile_latest on db_sourcefile.id=db_sourcefile_latest.sourcefile_id
            WHERE db_sourcefile_latest.latest_id={latest_id}
            """

        with connection.cursor() as cursor:
            cursor.execute(query)
            total = len(cursor.fetchall())

        return total

    def get_total_recipient_individuals(self):
        return self.source_file_set.annotate(
            total=RawSQL("((aggregate->>%s)::int)", ("recipient_individuals",))
        ).aggregate(Sum("total"))["total__sum"]

    def get_total_funders(self):
        # Determine if we're dealing with just one publisher and whether we need to limit
        # the source files to that publisher rather than all in 'latest'
        if self.source_file_set.distinct("data__publisher__prefix").count() == 1:
            source_file_ids = ",".join(
                map(str, self.source_file_set.values_list("id", flat=True))
            )
            query = f"""
            SELECT DISTINCT(jsonb_array_elements(db_sourcefile.aggregate->'funders'))
            FROM db_sourcefile
            WHERE db_sourcefile.id IN ({source_file_ids})
            """
        else:
            latest_id = db.Latest.objects.get(series=db.Latest.CURRENT).pk
            query = f"""
            SELECT DISTINCT(jsonb_array_elements(db_sourcefile.aggregate->'funders'))
            FROM db_sourcefile
            INNER JOIN db_sourcefile_latest on db_sourcefile.id=db_sourcefile_latest.sourcefile_id
            WHERE db_sourcefile_latest.latest_id={latest_id}
            """

        with connection.cursor() as cursor:
            cursor.execute(query)
            total = len(cursor.fetchall())

        return total

    def get_pc_quality_grants(self):
        ret = {}
        total_grants = self.get_total_grants()
        total_recipient_org_grants = (
            total_grants - self.get_total_recipient_individuals()
        )

        for metric, query in self.quality_query_parameters.items():
            # Aggregate total number of errors for the metric
            ret[metric] = (
                self.source_file_set.filter(**query)
                .annotate(total=RawSQL("((aggregate->>%s)::int)", ("count",)))
                .aggregate(Sum("total"))["total__sum"]
            )

            if ret[metric] == None:
                ret[metric] = 0

            # Workout percentage of total errors / all grants in the relevant recipient set
            if "Org" in metric:
                ret[metric] = round(ret[metric] / total_recipient_org_grants * 100)
            else:
                ret[metric] = round(ret[metric] / total_grants * 100)

        return ret

    def get_pc_quality_publishers(self):
        ret = {}

        for metric, query in self.quality_query_parameters.items():
            ret[metric] = round(
                self.source_file_set.filter(**query)
                .distinct("data__publisher__prefix")
                .count()
                / self.get_total_publishers()
                * 100
            )

        return ret

    def get_pc_publishers_awarding_in_last(self, delta):
        data_delta = datetime.now() - timedelta(days=delta)
        return round(
            self.source_file_set.annotate(
                modified=RawSQL("(aggregate->>'max_award_date')::timestamp", [])
            )
            .filter(modified__gte=data_delta)
            .distinct("data__publisher__prefix")
            .count()
            / self.get_total_publishers()
            * 100
        )

    def get_pc_publishers_publishing_in_last(self, delta):
        data_delta = datetime.now() - timedelta(days=delta)
        return round(
            self.source_file_set.annotate(
                modified=RawSQL("(data->>'modified')::timestamp", [])
            )
            .filter(modified__gte=data_delta)
            .distinct("data__publisher__prefix")
            .count()
            / self.get_total_publishers()
            * 100
        )

    def get_pc_publishers_with_recipient_ext_org(self):

        ret = {}
        total_publishers = self.get_total_publishers()

        ranges = [
            [0, 10],
            [10, 20],
            [20, 30],
            [30, 40],
            [40, 50],
            [50, 60],
            [60, 70],
            [70, 80],
            [90, 100],
        ]

        query = self.source_file_set.annotate(
            pc=RawSQL(
                "(quality->'RecipientOrgPrefixExternal'->>'count')::float / (aggregate->>'count')::float * 100",
                [],
            ),
        )

        for range in ranges:
            ret["{}% - {}%".format(*range)] = (
                query.filter(pc__range=(range[0], range[1]))
                .distinct("data__publisher__prefix")
                .count()
                / total_publishers
                * 100
            )

        return ret

    def get_total_grants_awarded_in_last_ten_years(self):

        this_year_int = datetime.now().year
        award_years = {}

        for i in range(0, 10):
            year_str = str(this_year_int - i)

            award_years[year_str] = self.source_file_set.annotate(
                year_total=RawSQL("((aggregate->'award_years'->>%s)::int)", (year_str,))
            ).aggregate(Sum("year_total"))["year_total__sum"]

            if award_years[year_str] == None:
                award_years[year_str] = 0

        return award_years

    def get_pc_publishers_with_grants_awarded_in_last_ten_years(self):

        this_year_int = datetime.now().year
        award_years = {}

        for i in range(0, 10):
            year_str = str(this_year_int - i)

            award_years[year_str] = round(
                self.source_file_set.annotate(
                    year_total=RawSQL(
                        "((aggregate->'award_years'->>%s)::int)", (year_str,)
                    )
                )
                .filter(year_total__gt=0)
                .distinct("data__publisher__prefix")
                .count()
                / self.get_total_publishers()
                * 100
            )

            if award_years[year_str] == None:
                award_years[year_str] = 0

        return award_years

    def get_grant_org_id_types_used(self):
        latest_id = db.Latest.objects.get(series=db.Latest.CURRENT).pk

        # Django ORM doesn't allow raw sql if you don't SELECT an id field and as
        # we want to do an aggregate fall back to fully raw sql
        # This creates `key | sum` results for the latest sourcefiles by lateral joining the results of
        # jsonb_each_text (which are key | value) of the recipient_org_types json field.

        query = f"""
         SELECT keyval.key, SUM(keyval.value::int)
         FROM db_sourcefile
           INNER JOIN db_sourcefile_latest on db_sourcefile.id=db_sourcefile_latest.sourcefile_id,
           jsonb_each_text(aggregate->'recipient_org_types') as keyval
         WHERE
           aggregate->'recipient_org_types' is not null AND
           db_sourcefile_latest.latest_id={latest_id}
         GROUP BY keyval.key
         ORDER BY sum DESC
         LIMIT 10
        """

        cursor = connection.cursor()
        cursor.execute(query)

        results = {}

        for row in cursor.fetchall():
            results[row[0]] = row[1]

        return results


def create_publisher_stats(publisher):
    """Create stats and aggregate data about a publisher's grants"""

    ret = generate_stats("overview_grants", publisher.get_sourcefiles())

    return ret["quality"], ret["aggregate"]


def generate_stats(mode, source_file_set):
    """Looks at the source files and aggregates the quality and aggregate stats in the source_file_set
    valid modes are: overview_publishers and overview_grants
    """

    source_files_stats = SourceFilesStats(source_file_set)

    ret = {
        "aggregate": {
            "total": {
                "grants": source_files_stats.get_total_grants(),
                "GBP": source_files_stats.get_total_gbp(),
                "publishers": source_files_stats.get_total_publishers(),
                "recipientOrganisations": source_files_stats.get_total_recipient_organisations(),
                "recipientIndividuals": source_files_stats.get_total_recipient_individuals(),
                "funders": source_files_stats.get_total_funders(),
            }
        },
        "quality": {},
    }

    if mode == "overview_grants":
        ret["aggregate"].update(source_files_stats.get_pc_total_file_types())
        ret["quality"] = source_files_stats.get_pc_quality_grants()
        ret["aggregate"][
            "awardYears"
        ] = source_files_stats.get_total_grants_awarded_in_last_ten_years()
        ret["aggregate"][
            "orgIdTypes"
        ] = source_files_stats.get_grant_org_id_types_used()
        ret["aggregate"][
            "awardedThisYear"
        ] = source_files_stats.get_pc_publishers_awarding_in_last(366)
        ret["aggregate"][
            "awardedLastThreeMonths"
        ] = source_files_stats.get_pc_publishers_awarding_in_last(92)

    elif mode == "overview_publishers":
        ret["aggregate"].update(source_files_stats.get_pc_publishers_file_types())
        ret["aggregate"][
            "publishedThisYear"
        ] = source_files_stats.get_pc_publishers_publishing_in_last(366)
        ret["aggregate"][
            "publishedLastThreeMonths"
        ] = source_files_stats.get_pc_publishers_publishing_in_last(92)
        ret["quality"] = source_files_stats.get_pc_quality_publishers()
        ret["aggregate"][
            "awardYears"
        ] = source_files_stats.get_pc_publishers_with_grants_awarded_in_last_ten_years()
        ret["aggregate"][
            "recipientsExternalOrgId"
        ] = source_files_stats.get_pc_publishers_with_recipient_ext_org()

    else:
        raise Exception("Unknown mode. Valid modes: publishers, grants")

    return ret
