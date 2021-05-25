from lib360dataquality.cove.threesixtygiving import (
    USEFULNESS_TEST_CLASS,
    common_checks_360,
)
from lib360dataquality.cove.schema import Schema360

schema = Schema360()


def create(grants):
    """grants: grants json"""

    result = {}

    common_checks_360(result, "/", grants, schema, test_classes=[USEFULNESS_TEST_CLASS])

    return result
