import csv
import requests
import logging

from additional_data.models import IMDWardLookup

logger = logging.getLogger(__name__)


class IMDSnapshotSource:
    SOURCE_URL = "https://raw.githubusercontent.com/ThreeSixtyGiving/grants-to-individuals-imd/live/datadump_ward_imd.csv"

    def _get_ward_imd_data(self, source_url):
        logger.info(f"Fetching IMD Ward Lookup Snapshot from {source_url}")

        r = requests.get(source_url, stream=True)
        r.encoding = "utf-8-sig"

        csv_reader = csv.DictReader(r.iter_lines(decode_unicode=True))
        return csv_reader

    def import_imd_snapshot(self, source_url=SOURCE_URL):
        ward_imd_rows = self._get_ward_imd_data(source_url)

        IMDWardLookup.objects.all().delete()
        created = IMDWardLookup.objects.bulk_create(
            IMDWardLookup(
                wd23cd=r["WD23CD"],
                wd23nm=r["WD23NM"],
                wd23nmw=r["WD23NMW"] if r["WD23NMW"] != "" else None,
                uk_imd_e_score=float(r["UK_IMD_E_score"]),
                original_decile=int(r["original_decile"]),
                e_expanded_decile=int(r["E_expanded_decile"]),
                uk_imd_e_rank=float(r["UK_IMD_E_rank"]),
                uk_imd_e_pop_decile=int(r["UK_IMD_E_pop_decile"]),
                uk_imd_e_pop_quintile=int(r["UK_IMD_E_pop_quintile"]),
                total_population=(
                    float(r["total_Population"])
                    if r["total_Population"] != ""
                    else None
                ),
            )
            for r in ward_imd_rows
        )

        logger.info(f"Loaded {len(created)} Wards from CSV")

    def update_additional_data(self, grant, additional_data):
        # TODO: Annotate additional_data with IMD & population values
        pass
