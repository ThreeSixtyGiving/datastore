from django.core.management.base import BaseCommand, CommandError

import db.models as db

from django.db import connection
from django.db.backends.postgresql.introspection import DatabaseIntrospection

import sys, json

from additional_data.sources.find_that_charity import non_primary_org_ids_map


def update_entities():

    grants = db.Latest.objects.get(series=db.Latest.CURRENT).grant_set.values_list(
        "data", flat=True
    )

    # Delete old entities from previous latest
    print("Removing old entity data")
    db.Recipient.objects.all().delete()
    db.Funder.objects.all().delete()

    recipient_orgs_bulk = {}
    funder_orgs_bulk = {}
    non_primary_org_ids_map_cache = non_primary_org_ids_map()

    print("Analysing latest best grant data for entities")

    for grant in grants:
        for recipient in grant.get("recipientOrganization", []):
            # If the org-id provided is a non-primary org-id return the primary
            # otherwise return the specified org-id
            org_id = non_primary_org_ids_map_cache.get(recipient["id"], recipient["id"])

            try:
                recipient_ob = recipient_orgs_bulk[org_id]
            except KeyError:
                recipient_ob = db.Recipient(org_id=org_id)
                recipient_orgs_bulk[org_id] = recipient_ob

            recipient_ob.add_name(recipient["name"])
            recipient_ob.source = db.Entity.GRANT
            recipient_ob.update_aggregate(grant)

        # Create funding orgs
        for funder in grant["fundingOrganization"]:
            # If the org-id provided is a non-primary org-id return the primary
            # otherwise return the specified org-id
            org_id = non_primary_org_ids_map_cache.get(funder["id"], funder["id"])

            try:
                funder_ob = funder_orgs_bulk[org_id]
            except KeyError:
                funder_ob = db.Funder(
                    org_id=org_id,
                )
                funder_orgs_bulk[org_id] = funder_ob

            funder_ob.add_name(funder["name"])
            funder_ob.source = db.Entity.GRANT
            funder_ob.update_aggregate(grant)

    print("Creating recipient org entities")
    db.Recipient.objects.bulk_create(recipient_orgs_bulk.values(), batch_size=100000)
    print("Creating funder org entities")
    db.Funder.objects.bulk_create(funder_orgs_bulk.values(), batch_size=100000)


def create_orgs_list(entity_type, output=sys.stdout):
    """Outputs all the known entities for a particular type as json lines
    entity_type: publisher, recipient, funder
    output: io
    """
    introspect = DatabaseIntrospection(connection)

    query = f"""
        SELECT DISTINCT
        db_{entity_type}.org_id as "id",
        db_{entity_type}.name as name,
        db_{entity_type}."aggregate" as "aggregate",
        db_{entity_type}.additional_data as "additionalData",
        additional_data_orginfocache.data as "ftcData",
        db_publisher.name as "publisherName",
        db_publisher.prefix as "publisherPrefix"
        FROM db_{entity_type}
        LEFT OUTER JOIN additional_data_orginfocache on db_{entity_type}.org_id = additional_data_orginfocache.org_id
        LEFT OUTER JOIN db_publisher on db_{entity_type}.org_id = db_publisher.org_id
    """

    def parse_data_in_result(result, col_types):
        # work around for https://github.com/ThreeSixtyGiving/datastore/issues/125

        new_row = []
        for i, field in enumerate(result):
            if "JSONField" in col_types[i] and field:
                field = json.loads(field)
            else:
                field = field
            new_row.append(field)
        return new_row

    with connection.cursor() as cursor:
        cursor.execute(query)
        cols = [col.name for col in cursor.description]
        col_types = [
            introspect.data_types_reverse[col.type_code] for col in cursor.description
        ]

        for row in cursor.fetchall():
            row_new = parse_data_in_result(row, col_types)
            output.write(json.dumps(dict(zip(cols, row_new))))
            output.write("\r\n")


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            nargs="+",
            action="store",
            dest="entity_type",
            help="The entity type to output. One of: recipient, funder",
        )

        parser.add_argument(
            "--update",
            action="store_true",
            dest="update_entities",
            help="Update the entities data for latest best grant data",
        )

    def handle(self, *args, **options):

        if options.get("update_entities"):
            update_entities()
            return

        if options.get("entity_type"):
            for entity_type in options["entity_type"]:
                if entity_type != "recipient" and entity_type != "funder":
                    raise CommandError(f"{entity_type} is an unknown entity type")
                create_orgs_list(entity_type)

            return
