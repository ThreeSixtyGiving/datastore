import datetime
from typing import Optional, TextIO

from django.db import connection, transaction

from db.models import Latest

EXTRACT_GRANTS_SQL = """
    SELECT (
        g.data || jsonb_build_object(
            'additional_data', COALESCE(g.additional_data, '{}'::jsonb) || jsonb_build_object(
                'GNCanonicalRecipientOrgId', COALESCE(
                    g.additional_data->'recipientOrgInfos'->0->>'id',
                    g.data->'recipientOrganization'->0->>'id'
                ),
                'GNCanonicalRecipientOrgName', COALESCE(
                    g.additional_data->'recipientOrgInfos'->0->>'name',
                    g.data->'recipientOrganization'->0->>'name'
                )
            )
        )
    )::text
    FROM db_grant g
    JOIN db_grant_latest gl ON gl.grant_id = g.id
    JOIN db_latest l ON l.id = gl.latest_id
    WHERE l.series = %s
      AND (g.data->>'awardDate')::date >= %s
"""

AWARD_DATE_RANGE_SQL = """
    SELECT MIN((g.data->>'awardDate')::date), MAX((g.data->>'awardDate')::date)
    FROM db_grant g
    JOIN db_grant_latest gl ON gl.grant_id = g.id
    JOIN db_latest l ON l.id = gl.latest_id
    WHERE l.series = %s
"""


def get_award_date_range():
    """Optional min/max award date across the current latest grants"""
    with connection.cursor() as cursor:
        cursor.execute(AWARD_DATE_RANGE_SQL, [Latest.CURRENT])
        min_date, max_date = cursor.fetchone()
    return min_date, max_date


def build_segments(
    min_date: datetime.date, max_date: datetime.date, segment_years: int = 5
):
    """Date segments, segment_years wide from min_date to max_date"""
    segments = []
    start = datetime.date(min_date.year, 1, 1)

    while start <= max_date:
        end = datetime.date(start.year + segment_years, 1, 1)
        segments.append((start, end))
        start = end

    return segments


def stream_segment_to_jsonl(
    start: datetime.date,
    end: Optional[datetime.date],
    out_fp: TextIO,
    itersize: int = 2000,
) -> int:
    count = 0
    sql = EXTRACT_GRANTS_SQL
    params = [Latest.CURRENT, start]

    if end is not None:
        sql += "  AND (g.data->>'awardDate')::date < %s\n"
        params.append(end)

    with transaction.atomic():
        with connection.connection.cursor(
            name=f"bulk_export_{start.isoformat()}"
        ) as cursor:
            cursor.itersize = itersize
            cursor.execute(sql, params)

            for (row_json,) in cursor:
                out_fp.write(row_json)
                out_fp.write("\n")
                count += 1

    return count
