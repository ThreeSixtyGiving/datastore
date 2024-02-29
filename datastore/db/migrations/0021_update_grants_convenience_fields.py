"""
The previous migration created new convenience fields on Grant to aid indexing and faster queries,
This migration follows on to populate the fields on all existing Grants.
"""

from django.db import migrations


UPDATE_GRANTS_SQL = """
UPDATE db_grant AS g
SET publisher_org_id = p.org_id,
    recipient_org_ids = ARRAY(SELECT jsonb_array_elements_text(jsonb_path_query_array((g.data)->'recipientOrganization', '$[*].id'))),
    funding_org_ids = ARRAY(SELECT jsonb_array_elements_text(jsonb_path_query_array((g.data)->'fundingOrganization', '$[*].id')))
FROM db_publisher AS p
WHERE g.publisher_id = p.id;
"""

UPDATE_GRANTS_REVERSE_SQL = """
UPDATE db_grant AS g
SET publisher_org_id = NULL,
    recipient_org_ids = NULL,
    funding_org_ids = NULL;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("db", "0020_auto_20240226_1454"),
    ]

    operations = [migrations.RunSQL(UPDATE_GRANTS_SQL, UPDATE_GRANTS_REVERSE_SQL)]
