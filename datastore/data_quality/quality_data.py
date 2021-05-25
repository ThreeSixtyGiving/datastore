from lib360dataquality.cove.threesixtygiving import (
    USEFULNESS_TEST_CLASS,
    common_checks_360,
)
from lib360dataquality.cove.schema import Schema360

import json
from tempfile import TemporaryDirectory

schema = Schema360()


def create(grants):
    """grants: grants json"""

    cove_results = {"file_type": "json"}

    with TemporaryDirectory() as tempdir:
        common_checks_360(
            cove_results, tempdir, grants, schema, test_classes=[USEFULNESS_TEST_CLASS]
        )

    # We don't quite want the result as-is
    # our format is:
    # [
    #   { "TestClassName": { "heading": "text", "count": n } }
    # ]

    quality_results = []

    for test in cove_results["usefulness_checks"]:
        quality_results.append(
            {
                test[0]["type"]: {
                    "heading": test[0]["heading"],
                    "count": test[0]["count"],
                }
            }
        )

    return quality_results
