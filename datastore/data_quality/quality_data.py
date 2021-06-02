from lib360dataquality.cove.threesixtygiving import (
    USEFULNESS_TEST_CLASS,
    TEST_CLASSES,
    common_checks_360,
)
from lib360dataquality.cove.schema import Schema360
from lib360dataquality import check_field_present
from tempfile import TemporaryDirectory

schema = Schema360()


def create(grants):
    """grants: grants json"""

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
    # value we template out all the expected results from all the available tests.

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
