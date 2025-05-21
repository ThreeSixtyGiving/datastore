from lib360dataquality.cove.threesixtygiving import common_checks_360
from lib360dataquality.additional_test import TestType
from lib360dataquality.cove.schema import Schema360

schema = Schema360()


def create(grants):
    """grants: grants json"""

    result = {}

    common_checks_360(
        result, "/", grants, schema, test_classes=[TestType.USEFULNESS_TEST_CLASS]
    )

    return result
