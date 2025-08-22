import argparse
from datetime import datetime
from typing import Type, Optional, Dict, Literal, List
from pathlib import Path
from rest_framework.serializers import BaseSerializer
from django.db import transaction
from django.db.models import Model
import monitoring.models as models
import monitoring.serializers as serializers
from django.core.management.base import BaseCommand
import json
import logging

from monitoring.models import AbstractMetricsRecord

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Export or Import monitoring data"

    RECORD_TYPE_OPTIONS = ["funder", "publisher", "sourcefile", "dataset"]

    def add_arguments(self, parser):
        def dir_path_type(path):
            if Path(path).is_dir() and Path(path).exists():
                return path
            else:
                raise argparse.ArgumentTypeError(
                    f"{path} is not a valid existing directory"
                )

        # Export to files
        parser.add_argument("--export-records-to-dir", default=None, type=dir_path_type)
        # Export options
        parser.add_argument(
            "--export-record-types",
            nargs="+",
            type=str,
            default=Command.RECORD_TYPE_OPTIONS,
            choices=Command.RECORD_TYPE_OPTIONS,
        )
        parser.add_argument("--export-start-date", default=None)
        parser.add_argument("--export-end-date", default=None)

        # Import from files
        parser.add_argument("--import-records-from-dir", default=None)
        # Import options
        parser.add_argument("--import-start-date", default=None)
        parser.add_argument("--import-end-date", default=None)
        parser.add_argument("--import-dry-run", default=False, action="store_true")

    def handle(self, *args, **options):

        # Export
        if options["export_records_to_dir"]:
            # Prepare filters
            start_date = options["export_start_date"]
            end_date = options["export_end_date"]

            start_date_dt = (
                datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            )

            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

            # Export by record type
            to_dir = Path(options["export_records_to_dir"])
            record_types: List[
                Literal["funder", "publisher", "sourcefile", "dataset"]
            ] = options["export_record_types"]

            if "funder" in record_types:
                export_funder_records(
                    to_dir / "monitoring-funder-records.jl", start_date_dt, end_date_dt
                )

            if "publisher" in record_types:
                export_publisher_records(
                    to_dir / "monitoring-publisher-records.jl",
                    start_date_dt,
                    end_date_dt,
                )

            if "sourcefile" in record_types:
                export_sourcefile_records(
                    to_dir / "monitoring-sourcefile-records.jl",
                    start_date_dt,
                    end_date_dt,
                )

            if "dataset" in record_types:
                export_dataset_records(
                    to_dir / "monitoring-dataset-records.jl", start_date_dt, end_date_dt
                )

        # Import
        if options["import_records_from_dir"]:
            from_dir = Path(options["import_records_from_dir"])

            # Prepare filters
            start_date = options["import_start_date"]
            end_date = options["import_end_date"]

            start_date_dt = (
                datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            )
            end_date_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

            with transaction.atomic():
                import_records(
                    funder_records_file=from_dir / "monitoring-funder-records.jl",
                    publisher_records_file=from_dir / "monitoring-publisher-records.jl",
                    sourcefile_records_file=from_dir
                    / "monitoring-sourcefile-records.jl",
                    dataset_records_file=from_dir / "monitoring-dataset-records.jl",
                    start_date=start_date_dt,
                    end_date=end_date_dt,
                )

                if options["import_dry_run"]:
                    transaction.set_rollback(True)


#
# Export
#

# Export functions are seperated by record type to support old codebase versions
# missing some Models e.g. don't have Dataset records


def _export_generic_jsonlines(
    record_model: Type[AbstractMetricsRecord],
    record_serialiser: Type[BaseSerializer],
    to_file: Path,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> int:
    records = record_model.objects.all()

    # Filter records for export
    if start_date:
        records = records.filter(timestamp__gte=start_date)

    if end_date:
        records = records.filter(timestamp__lte=end_date)

    count = 0
    with to_file.open(mode="w") as f:
        for record in records:
            data = record_serialiser(record).data
            json.dump(data, f, indent=None)
            f.write("\n")  # one record per line, jsonlines
            count += 1
    return count


def export_funder_records(
    to_file: Path, start_date: Optional[datetime], end_date: Optional[datetime]
):
    count = _export_generic_jsonlines(
        models.FunderMetricsRecord,
        serializers.FunderMetricsRecordSerializer,
        to_file,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info("Exported %s funder records", count)


def export_publisher_records(
    to_file: Path, start_date: Optional[datetime], end_date: Optional[datetime]
):
    count = _export_generic_jsonlines(
        models.PublisherMetricsRecord,
        serializers.PublisherMetricsRecordSerializer,
        to_file,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info("Exported %s publisher records", count)


def export_sourcefile_records(
    to_file: Path, start_date: Optional[datetime], end_date: Optional[datetime]
):
    count = _export_generic_jsonlines(
        models.SourceFileMetricsRecord,
        serializers.SourceFileMetricsRecordSerializer,
        to_file,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info("Exported %s source file records", count)


def export_dataset_records(
    to_file: Path, start_date: Optional[datetime], end_date: Optional[datetime]
):
    count = _export_generic_jsonlines(
        models.DatasetMetricsRecord,
        serializers.DatasetMetricsRecordSerializer,
        to_file,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info("Exported %s dataset records", count)


#
# Import
#


def _records_from_file(p: Path):
    """Load and iterably yield records from a jsonlines file"""
    with p.open(mode="r") as f:
        for line in f:
            yield json.loads(line)


def import_records(
    funder_records_file: Optional[Path],
    publisher_records_file: Optional[Path],
    sourcefile_records_file: Optional[Path],
    dataset_records_file: Optional[Path],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    # Find all record timestamps to create snapshots
    snapshots: Dict[datetime, models.MonitoringSnapshot] = dict()

    def get_or_create_snapshot(timestamp: datetime) -> models.MonitoringSnapshot:
        if timestamp in snapshots:
            return snapshots[timestamp]
        else:
            snapshot = models.MonitoringSnapshot(
                timestamp=timestamp,
                latest_getter_run_id=-1,  # Fake getter run ID for imported data
            )
            snapshot.save()
            snapshots[timestamp] = snapshot
            return snapshot

    def _load_records(
        p: Path, serialiser: Type[BaseSerializer], model: Type[Model]
    ) -> int:
        if not p.exists():
            logger.warning(f"Warning: No records file found at: {p}")
            return 0

        bulk_records = []
        count = 0
        for record in _records_from_file(p):
            timestamp = datetime.fromisoformat(record["timestamp"])
            snapshot = get_or_create_snapshot(timestamp)
            serialised_record = serialiser(data=record)

            if not serialised_record.is_valid():
                logger.warning(
                    "Invalid serialised record: %s - %s",
                    serialised_record.initial_data,
                    serialised_record.errors,
                )
                continue

            # Filter incoming records
            if start_date and timestamp < start_date:
                continue

            if end_date and timestamp > end_date:
                continue

            bulk_records.append(
                model(**serialised_record.validated_data, snapshot=snapshot)
            )
            count += 1

        model.objects.bulk_create(bulk_records)
        logger.info(f"Loaded {count} {model.__name__}")
        return count

    _load_records(
        funder_records_file,
        serializers.FunderMetricsRecordSerializer,
        models.FunderMetricsRecord,
    )

    _load_records(
        publisher_records_file,
        serializers.PublisherMetricsRecordSerializer,
        models.PublisherMetricsRecord,
    )

    _load_records(
        sourcefile_records_file,
        serializers.SourceFileMetricsRecordSerializer,
        models.SourceFileMetricsRecord,
    )

    _load_records(
        dataset_records_file,
        serializers.DatasetMetricsRecordSerializer,
        models.DatasetMetricsRecord,
    )

    logger.info(f"Created {len(snapshots)} snapshots from loaded data")
