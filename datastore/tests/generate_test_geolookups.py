#!/usr/bin/env python3

import argparse
import csv
import requests
import logging
from typing import Set, Optional, Iterator, Mapping, Sequence
from contextlib import closing
from codecs import iterdecode
from pathlib import Path

# "generates" test data for geolookups
# by downloading the data from the geo-lookups repo,
# and selecting a sample.
#
# Note: if you regenerate this test data, you'll probably also have to update
#       some values in test_additional_data_geolookups.py

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("./files/geolookups/")

DOWNLOAD_URL_PREFIX = "https://raw.githubusercontent.com/drkane/geo-lookups/master/"

DOWNLOAD_CSV_TIMEOUT = 60

LSOA_KEY = "lsoacd"
MSOA_KEY = "msoacd"
WARD_KEY = "wdcd"

# Extra LSOAs to include in the sample dataset,
# i.e. the ones explicitly referenced in tests
EXTRA_LSOAS = set(["E01011964"])


def geo_csv(csv_name: str):
    with closing(
        requests.get(
            DOWNLOAD_URL_PREFIX + csv_name + ".csv", timeout=DOWNLOAD_CSV_TIMEOUT
        )
    ) as r:
        r.raise_for_status()
        return csv.DictReader(iterdecode(r.iter_lines(), "utf-8"))


def filter_csv(reader: csv.DictReader, field: str, is_in: Set[str]):
    return [row for row in reader if row[field] in is_in]


def sample(
    iter: Iterator[Mapping[str, str]],
    include_key: Optional[str] = None,
    include_values: Optional[Set[str]] = None,
    ratio: int = 100,
):
    """
    Take a sample of values, plus include extra values that match given key/values.
    """
    for i, v in enumerate(iter):
        if include_key and v[include_key] in include_values:
            yield v
        elif i % ratio == 0:
            yield v


def write_csv(path: Path, rows: Iterator[Mapping[str, str]], fieldnames: Sequence[str]):
    with path.open(mode="w") as f:
        writer = csv.DictWriter(f, fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sample_data(output_dir: Optional[str] = None):
    output_path = Path(output_dir) if output_dir else DEFAULT_OUTPUT_PATH
    output_path.mkdir(exist_ok=True)

    # Load input CSVs
    area_all_codes = geo_csv("area_all_codes")

    lsoa_la = geo_csv("lsoa_la")
    lsoa_latlong = geo_csv("lsoa_latlong")

    msoa_la = geo_csv("msoa_la")
    msoa_latlong = geo_csv("msoa_latlong")

    ward_all_codes = geo_csv("ward_all_codes")
    ward_latlong = geo_csv("ward_latlong")

    # Take test samples
    sample_lsoa_la = list(
        sample(
            lsoa_la, include_key=LSOA_KEY.upper(), include_values=EXTRA_LSOAS, ratio=400
        )
    )
    sample_msoa_la = list(sample(msoa_la, ratio=100))
    sample_ward_all_codes = list(sample(ward_all_codes, ratio=100))

    lsoa_codes = set(row[LSOA_KEY.upper()] for row in sample_lsoa_la)
    msoa_codes = set(row[MSOA_KEY.upper()] for row in sample_msoa_la)
    ward_codes = set(row[WARD_KEY.upper()] for row in sample_ward_all_codes)

    sample_lsoa_latlong = filter_csv(lsoa_latlong, LSOA_KEY.upper(), lsoa_codes)
    sample_msoa_latlong = filter_csv(msoa_latlong, MSOA_KEY.upper(), msoa_codes)
    # ward_latlong.csv uses lowercase keys
    sample_ward_latlong = filter_csv(ward_latlong, WARD_KEY.lower(), ward_codes)

    logger.info(f"{len(lsoa_codes)=} {len(msoa_codes)=} {len(ward_codes)=}")

    # Write sample outputs
    write_csv(
        output_path / "area_all_codes.csv", area_all_codes, area_all_codes.fieldnames
    )
    write_csv(output_path / "lsoa_la.csv", sample_lsoa_la, lsoa_la.fieldnames)
    write_csv(
        output_path / "lsoa_latlong.csv", sample_lsoa_latlong, lsoa_latlong.fieldnames
    )
    write_csv(output_path / "msoa_la.csv", sample_msoa_la, msoa_la.fieldnames)
    write_csv(
        output_path / "msoa_latlong.csv", sample_msoa_latlong, msoa_latlong.fieldnames
    )
    write_csv(
        output_path / "ward_all_codes.csv",
        sample_ward_all_codes,
        ward_all_codes.fieldnames,
    )
    write_csv(
        output_path / "ward_latlong.csv", sample_ward_latlong, ward_latlong.fieldnames
    )


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output_dir",
        type=str,
        action="store",
        default=DEFAULT_OUTPUT_PATH.as_posix(),
        help="The location of the geolookup data output",
        required=False,
    )

    args = parser.parse_args()

    sample_data(args.output_dir)
