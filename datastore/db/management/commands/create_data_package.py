import json
import os

from django.core.management.base import BaseCommand
from django.db import connection

from db.management.spinner import Spinner
from db.models import Latest


class Command(BaseCommand):
    help = "Outputs a data package of our best Latest data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            action="store",
            dest="dir",
            type=str,
            help="Destination of data output dir",
            default="grantnav_data",
        )

        parser.add_argument(
            "--indent-json",
            action="store",
            dest="indent",
            type=int,
            help="Indentation of JSON output",
            default=None,
        )

    def handle(self, *args, **options):
        """Create data package with the structure:

        - data_all.json (all sources)
        - json_all/
              |- grants.json (lists of grants)
              |- grants.json
              ...
        """
        spinner = Spinner()
        spinner.start()

        latest_data = Latest.objects.get(series=Latest.CURRENT)

        # Create the data_all json file
        os.makedirs("%s/json_all/" % options["dir"], mode=0o700)

        data_all = []
        data_all_file = "%s/data_all.json" % options["dir"]

        recipients_file = "%s/recipients.jl" % options["dir"]
        funders_file = "%s/funders.jl" % options["dir"]

        with connection.cursor() as cursor, open(
            recipients_file, "w"
        ) as recipientfp, open(funders_file, "w") as funderfp:
            cursor.execute(CREATE_RELATED_ORGIDS)

            cursor.execute(ORG_SELECT.format(org="recipient"))
            columns = [col[0] for col in cursor.description]
            rows = 0
            for row in cursor.fetchall():
                recipient = json.dumps(dict(zip(columns, row)))
                recipientfp.write(recipient)
                recipientfp.write("\r\n")
                rows += 1

            cursor.execute(ORG_SELECT.format(org="funding"))
            rows = 0
            for row in cursor.fetchall():
                funder = json.dumps(dict(zip(columns, row)))
                funderfp.write(funder)
                funderfp.write("\r\n")
                rows += 1

        def flatten_grant(in_grant):
            """Add the additional_data inside grant object"""
            out_grant = {}
            out_grant.update(in_grant["data"])
            try:
                out_grant["additional_data"] = in_grant["additional_data"]
            except KeyError:
                # additional_data isn't required and is not available
                pass

            return out_grant

        for source in latest_data.sourcefile_set.all():
            data_all.append(source.data)

            grant_file_name = "%s/json_all/%s.json" % (
                options["dir"],
                source.data["identifier"],
            )

            # Write out grant data
            with open(grant_file_name, "w") as grantfp:

                grants_list = list(
                    source.grant_set.all().values("data", "additional_data")
                )

                grants_list_flattened = map(flatten_grant, grants_list)

                grants = {"grants": list(grants_list_flattened)}

                grantfp.write(json.dumps(grants, indent=options["indent"]))

        with open(data_all_file, "w+") as data_all_fp:
            data_all_fp.write(json.dumps(data_all, indent=options["indent"]))

        spinner.stop()


CREATE_RELATED_ORGIDS = """
DROP TABLE IF EXISTS related_orgids;

CREATE TABLE related_orgids AS (    
    with org_name AS (SELECT                                                   
        data -> 'linked_orgs' ->> 0 AS canonical_orgid, 
        string_agg(data ->> 'name', '||') AS name,
        string_agg(org_id, '||') AS name_org_id
    FROM additional_data_orginfocache GROUP BY 1
    )
    SELECT                                                   
        linked_org ->> 0 org_id,
        data -> 'linked_orgs' related_orgids,
        data -> 'linked_orgs' ->> 0 AS canonical_orgid,
        max(name) AS name,
        max(name_org_id) AS name_org_id
    FROM 
        additional_data_orginfocache orgi 
    JOIN LATERAL
        jsonb_array_elements(data -> 'linked_orgs') linked_org ON true
    JOIN
        org_name orgn ON orgi.data -> 'linked_orgs' ->> 0 = canonical_orgid
    WHERE data -> 'linked_orgs' ->> 0 is not null 
    GROUP by 1,2,3
);
"""

ORG_SELECT = """
WITH latest_grant AS (
    SELECT 
        *
    FROM 
        db_grant 
    JOIN 
        db_grant_latest ON db_grant.id = db_grant_latest.grant_id
    JOIN
        db_latest on db_grant_latest.latest_id = db_latest.id
    WHERE
        db_latest.series = 'CURRENT'
),
{org}_by_currency AS (SELECT 
    coalesce(o.canonical_orgid, g.data -> '{org}Organization' -> 0 ->> 'id') org_id, 
    g.data ->> 'currency' AS currency,
    coalesce(related_orgids, to_jsonb(ARRAY[g.data -> '{org}Organization' -> 0 ->> 'id'])) AS orgids,
    max(coalesce(
        o.name || '||' || (g.data -> '{org}Organization' -> 0 ->> 'name'),
        g.data -> '{org}Organization' -> 0 ->> 'name')
    ) AS name,
    max(name_org_id) AS org_ids_charity_finder,
    max(o.name) AS name_charity_finder,
    count(*) AS grants,
    sum((g.data ->> 'amountAwarded')::numeric) total_amount,
    max((g.data ->> 'amountAwarded')::numeric) max_amount,
    min((g.data ->> 'amountAwarded')::numeric) min_amount,
    avg((g.data ->> 'amountAwarded')::numeric) avg_amount,
    max(g.data ->> 'awardDate') max_award_date,
    min(g.data ->> 'awardDate') min_award_date
FROM 
    latest_grant g 
LEFT JOIN 
    related_orgids o ON o.org_id = g.data -> '{org}Organization' -> 0 ->> 'id' 
GROUP BY 1, 2, 3)
SELECT 
    org_id as id, 
    string_to_array(string_agg(name, '||'), '||') AS "organizationName", 
    orgids AS "orgIDs", 
    coalesce(string_to_array(string_agg(org_ids_charity_finder, '||'), '||'), Array[]::text[]) AS "orgIDsCharityFinder", 
    coalesce(string_to_array(string_agg(name_charity_finder, '||'), '||'), Array[]::text[]) AS "nameCharityFinder", 
    sum(grants)::int AS grants,
    array_agg(currency) as currency,
    jsonb_object_agg(currency, grants) AS "currencyGrants",
    jsonb_object_agg(currency, total_amount) AS "currencyTotal",
    jsonb_object_agg(currency, max_amount) AS "currencyMaxAmount",
    jsonb_object_agg(currency, min_amount) AS "currencyMinAmount",
    jsonb_object_agg(currency, avg_amount) AS "currencyAvgAmount",
    max(max_award_date) "maxAwardDate",
    min(min_award_date) "minAwardDate"
FROM
    {org}_by_currency
GROUP BY org_id, orgids;
"""
