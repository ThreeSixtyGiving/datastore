from lib360dataquality.cove.threesixtygiving import (
    USEFULNESS_TEST_CLASS,
    TEST_CLASSES,
    common_checks_360,
)
from lib360dataquality.cove.schema import Schema360
from lib360dataquality import check_field_present

from django.db.models import Count
from django.db.models import Q, Sum
from django.db.models.expressions import RawSQL
from django.core.cache import cache

import db.models as db

from tempfile import TemporaryDirectory
import datetime

schema = Schema360()


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
    ]

    with TemporaryDirectory() as tempdir:
        common_checks_360(
            cove_results, tempdir, grants, schema, test_classes=[USEFULNESS_TEST_CLASS]
        )

    # We don't quite want the result as-is
    # our format is:
    # {
    #   "TestClassName": { "heading": "text", "count": n },
    #   "TestTwoClassName": { "count": 0 },
    # }
    # We only get results when a quality test finds an issue, so to provide a count 0
    # value we template out all the expected results with 0 from all the available tests.

    quality_results = {}

    # Create the template
    for available_test in TEST_CLASSES[USEFULNESS_TEST_CLASS]:
        quality_results[available_test.__name__] = {"count": 0}

    # Update with the results
    for test in cove_results["usefulness_checks"]:
        quality_results[test[0]["type"]] = {
            "heading": test[0]["heading"],
            "count": test[0]["count"],
        }

    aggregates = {
        "count": cove_results["grants_aggregates"]["count"],
        "recipients": len(
            cove_results["grants_aggregates"]["distinct_recipient_org_identifier"]
        ),
        "funders": len(
            cove_results["grants_aggregates"]["distinct_funding_org_identifier"]
        ),
        "max_award_date": cove_results["grants_aggregates"]["max_award_date"],
        "min_award_date": cove_results["grants_aggregates"]["min_award_date"],
        "currencies": cove_results["grants_aggregates"]["currencies"],
    }

    return quality_results, aggregates


def aggregated_stats(source_file_set, mode, cache_key=None):
    """Looks at the source files and aggregates the quality and aggregate stats in the source_file_set"""
    if cache_key:
        ret = cache.get(cache_key)
        if ret:
            return ret

    total_grants_sql = RawSQL("((aggregate->>%s)::numeric)", ("count",))
    total_grants = source_file_set.annotate(total=total_grants_sql).aggregate(
        Sum("total")
    )["total__sum"]

    totalRecipients = RawSQL("((aggregate->>%s)::numeric)", ("recipients",))

    total_gbp_query = RawSQL(
        "((aggregate->'currencies'->'GBP'->>%s)::numeric)", ("total_amount",)
    )

    try:
        total_gbp = float(
            source_file_set.annotate(total=total_gbp_query).aggregate(Sum("total"))[
                "total__sum"
            ]
        )
    except TypeError:
        # Happens if the source file has no GBP
        total_gbp = 0

    ret = {
        "aggregate": {
            "total": {
                "grants": int(total_grants),
                "GBP": total_gbp,
                "recipients": int(
                    source_file_set.annotate(total=totalRecipients).aggregate(
                        Sum("total")
                    )["total__sum"]
                ),
            }
        },
        "quality": {},
    }

    total_publishers = source_file_set.distinct("data__publisher__prefix").count()

    # The quality metrics we have are based on "Not" having something and we want to know if they DO have something
    # later we process the counts and filters to do total_publishers - not xyz / total_publishers
    # to give the total publishers that do have it.

    has_no_location_codes = source_file_set.filter(
        Q(quality__BeneficiaryLocationCountryCodeNotPresent__count__gte=1)
        | Q(quality__BeneficiaryLocationGeoCodeNotPresent__count__gte=1)
    )

    # TODO There is a more clever way to pass the filter field names in using **kwargs
    has_no_location_names = source_file_set.filter(
        quality__BeneficiaryLocationNameNotPresent__count__gte=1
    )

    has_no_recipient_org_location = source_file_set.filter(
        quality__IncompleteRecipientOrg__count__gte=1
    )
    has_no_grant_duration = source_file_set.filter(
        quality__PlannedDurationNotPresent__count__gte=1
    )
    has_no_grant_programme_title = source_file_set.filter(
        quality__GrantProgrammeTitleNotPresent__count__gte=1
    )
    has_no_grant_classification = source_file_set.filter(
        quality__ClassificationNotPresent__count__gte=1
    )

    json_files = source_file_set.exclude(
        data__datagetter_metadata__file_type__contains="json"
    )
    csv_files = source_file_set.exclude(
        data__datagetter_metadata__file_type__contains="csv"
    )
    xlsx_files = source_file_set.exclude(
        data__datagetter_metadata__file_type__contains="xlsx"
    )
    ods_files = source_file_set.exclude(
        data__datagetter_metadata__file_type__contains="ods"
    )

    this_month = datetime.datetime.now().strftime("%Y-%m")
    this_year = datetime.datetime.now().strftime("%Y")

    published_data_this_year = source_file_set.exclude(
        data__modified__startswith=this_year
    )
    published_data_this_month = source_file_set.exclude(
        data__modified__startswith=this_month
    )

    queries = {
        "hasBeneficiaryLocationCodes": has_no_location_codes,
        "hasRecipientOrgLocations": has_no_recipient_org_location,
        "hasBeneficiaryLocationName": has_no_location_names,
        "hasGrantDuration": has_no_grant_duration,
        "hasGrantProgrammeTitle": has_no_grant_programme_title,
        "hasGrantClassification": has_no_grant_classification,
    }

    # We look at the distinct publishers so that if any source file from a publisher
    # contains a quality problem in any of their source files then that publisher is counted
    # as not having that value
    if mode == "overview_publishers":

        # All this could be re-written to look at the published objects rather than aggregating the source file info
        aggregate_queries = {
            "publishedThisYear": published_data_this_year,
            "publishedThisMonth": published_data_this_month,
            "jsonFiles": json_files,
            "csvFiles": csv_files,
            "xlsxFiles": xlsx_files,
            "odsFiles": ods_files,
        }

        # Run aggregate queries
        for metric, query in aggregate_queries.items():
            ret["aggregate"][metric] = (
                total_publishers - query.distinct("data__publisher__prefix").count()
            ) / total_publishers

        # Run data quality queries
        for metric, query in queries.items():
            ret["quality"][metric] = (
                total_publishers - query.distinct("data__publisher__prefix").count()
            ) / total_publishers

        # Awarded in these years
        award_years = {}
        this_year_int = int(this_year)

        for i in range(0, 10):
            year_str = str(this_year_int - i)
            award_years[year_str] = (
                source_file_set.filter(aggregate__min_award_date__startswith=year_str)
                .distinct("data__publisher__prefix")
                .count()
                / total_publishers
            )

        ret.update({"minAwardYears": award_years})

    elif mode == "overview_grants":
        # We want to SUM the counts in the metric to know how many grants had quality issues
        count_field = RawSQL(
            "((quality->'BeneficiaryLocationCountryCodeNotPresent'->>'count')::numeric)",
            (),
        )
        count_field_two = RawSQL(
            "((quality->'BeneficiaryLocationGeoCodeNotPresent'->>'count')::numeric)",
            (),
        )
        all_code_counts = (
            has_no_location_codes.annotate(count=count_field)
            .annotate(count_two=count_field_two)
            .aggregate(Sum("count"), Sum("count_two"))
        )
        ret["quality"]["hasBeneficiaryLocationCodes"] = (
            all_code_counts["count__sum"] + all_code_counts["count_two__sum"]
        ) / (total_grants * 2)

        # TODO more clever way of doing this with a mapping of test names then loop over them
        count_field = RawSQL(
            "((quality->'IncompleteRecipientOrg'->>'count')::numeric)", ()
        )
        ret["quality"][
            "hasRecipientOrgLocations"
        ] = has_no_recipient_org_location.annotate(count=count_field)

        count_field = RawSQL(
            "((quality->'BeneficiaryLocationNameNotPresent'->>'count')::numeric)",
            (),
        )
        ret["quality"]["hasBeneficiaryLocationName"] = has_no_location_names.annotate(
            count=count_field
        )

        count_field = RawSQL(
            "((quality->'PlannedDurationNotPresent'->>'count')::numeric)", ()
        )
        ret["quality"]["hasGrantDuration"] = has_no_grant_duration.annotate(
            count=count_field
        )

        count_field = RawSQL(
            "((quality->'GrantProgrammeTitleNotPresent'->>'count')::numeric)", ()
        )
        ret["quality"][
            "hasGrantProgrammeTitle"
        ] = has_no_grant_programme_title.annotate(count=count_field)

        count_field = RawSQL(
            "((quality->'ClassificationNotPresent'->>'count')::numeric)", ()
        )
        ret["quality"]["hasGrantClassification"] = has_no_grant_classification.annotate(
            count=count_field
        )

        for metric, query in ret["quality"].items():
            # Skip this one has it is handled already due to being a special case
            if metric == "hasBeneficiaryLocationCodes":
                continue
            try:
                ret["quality"][metric] = (
                    total_grants - int(query.aggregate(Sum("count"))["count__sum"])
                ) / total_grants
            except TypeError:
                ret["quality"][metric] = "NA"

        # Awarded in these years
        award_years = {}
        this_year_int = int(this_year)

        query_args = {}

        latest = db.Latest.objects.get(series=db.Latest.CURRENT)
        grant_set = latest.grant_set.all()
        sums = []

        # Build query parameters
        for i in range(0, 10):
            # Alternatively we could do a query for each year need to test if this is faster:
            # award_years[year_str] = latest.grant_set.filter(data__awardDate__startswith=year_str).count()
            year_str = str(this_year_int - i)
            query_args[year_str] = Count(
                "data", filter=Q(data__awardDate__startswith=year_str)
            )
            sums.append(Sum(year_str))

        # Format the data
        for year_sum, total_year_grants in (
            grant_set.annotate(**query_args).aggregate(*sums).items()
        ):
            award_years[year_sum.replace("__sum", "")] = total_year_grants

        ret["aggregate"]["grantsByYear"] = award_years

    elif mode == "publishers":
        total_source_files = source_file_set.count()

        aggregate_queries = {
            "jsonFiles": json_files,
            "csvFiles": csv_files,
            "xlsxFiles": xlsx_files,
            "odsFiles": ods_files,
        }

        for metric, query in aggregate_queries.items():
            ret["aggregate"][metric] = total_source_files - query.count()

        for metric, query in queries.items():
            ret["quality"][metric] = total_source_files - query.count()

        # Awarded in these years
        award_years = {}
        this_year_int = int(this_year)

        for i in range(0, 10):
            year_str = str(this_year_int - i)
            award_years[year_str] = source_file_set.filter(
                aggregate__min_award_date__startswith=year_str
            ).count()

        ret["aggregate"]["minAwardYears"] = award_years
        ret["aggregate"]["lastLastModified"] = (
            source_file_set.order_by("-data__modified").first().data["modified"]
        )

    else:
        return {}

    if cache_key:
        cache.set(cache_key, ret)

    return ret
