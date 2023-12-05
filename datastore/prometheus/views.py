import re
import logging
import django.db

from django.conf import settings
from django.http.response import HttpResponse
from django.views import View
from django.db.models import (
    Q,
    F,
    BooleanField,
    IntegerField,
    Value as V,
    JSONField,
    Func,
)
from django.db.models.functions import Cast
from prometheus_client import Gauge
from prometheus_client.exposition import generate_latest

import db.models as db

logger = logging.getLogger(__name__)

NUM_ERRORS_LOGGED = Gauge(
    "total_service_errors_logged", "Total number of errors logged by last service run"
)

# These metrics don't start with datastore, for backwards compatibility.
TOTAL_CURRENT_LATEST_GRANTS = Gauge(
    "total_current_latest_grants", "Total number of current latest grants in the system"
)

TOTAL_PREVIOUS_LATEST_GRANTS = Gauge(
    "total_previous_latest_grants",
    "Total number of previous latest grants in the system",
)

TOTAL_DATAGETTER_GRANTS = Gauge(
    "total_datagetter_grants", "Total number of grants in the last datagetter run"
)

# New metrics we add start with datastore.
# It's a prometheus convention that metrics start with the name of the collector.
# This avoids problems with name collisions and different types of metrics.
NUM_PROBLEM_SOURCES_IN_LAST_RUN = Gauge(
    "datastore_num_problem_sources_in_last_run", "Number of problem sources in last run"
)

NUM_OK_SOURCES_IN_LAST_RUN = Gauge(
    "datastore_num_ok_sources_in_last_run", "Number of ok sources in last run"
)

NUM_CURRENT_GRANTS_WITH_BENEFICIARY_LOCATION_GEOCODE_WITHOUT_LOOKUP = Gauge(
    "datastore_num_current_grants_with_beneficiary_location_geocode_without_lookup",
    "The number of grants which explicitly specify a beneficiary location geocode, but for which we were unable to lookup the geocode. This suggests our geocode lookup information may be out of date, or that publishers have used an invalid geocode.",
)


class ServiceMetrics(View):
    def _num_errors_log(self):
        errors = 0
        log_file = getattr(settings, "DATA_RUN_LOG", "")
        search_term = re.compile("failure|failed|exception|error", re.IGNORECASE)

        try:
            with open(log_file, "r") as lf:
                log = lf.read()
                errors = len(search_term.findall(log))
        except FileNotFoundError:
            errors = -1
            pass

        NUM_ERRORS_LOGGED.set(errors)

    def _total_latest_grants(self):
        total_current = db.Latest.objects.get(
            series=db.Latest.CURRENT
        ).grant_set.count()

        TOTAL_CURRENT_LATEST_GRANTS.set(total_current)

        total_prev = db.Latest.objects.get(series=db.Latest.PREVIOUS).grant_set.count()
        TOTAL_PREVIOUS_LATEST_GRANTS.set(total_prev)

    def _total_datagetter_grants(self):
        total = db.GetterRun.latest().grant_set.count()
        TOTAL_DATAGETTER_GRANTS.set(total)

    def _total_num_sources_in_last_run(self):
        last_run = db.GetterRun.objects.order_by("-datetime").first()
        if last_run:
            problem_sources = last_run.sourcefile_set.filter(
                Q(data_valid=False) | Q(downloads=False) | Q(acceptable_license=False)
            )
            NUM_PROBLEM_SOURCES_IN_LAST_RUN.set(len(problem_sources))
            ok_sources = last_run.sourcefile_set.filter(
                Q(data_valid=True) & Q(downloads=True) & Q(acceptable_license=True)
            )
            NUM_OK_SOURCES_IN_LAST_RUN.set(len(ok_sources))
        else:
            NUM_PROBLEM_SOURCES_IN_LAST_RUN.set(-1)
            NUM_OK_SOURCES_IN_LAST_RUN.set(0)

    def _num_current_grants_with_beneficiary_location_geocode_without_lookup(self):
        current_grants = db.Latest.grants()

        # Thought: Shouldn't we check that there are the same number of lookup outputs as there are input geocodes?
        #  e.g. if a grant has two beneficiary locations w/ geocodes, they should both be represented in the output locationLookup
        # ... but lookup can also come from recipient org HQ location can't it? (but not for the case of grants to individuals)
        # TODO: investigate

        # Workaround, fixed in Django 5.0
        # See: https://stackoverflow.com/questions/42332304/django-an-equality-check-in-annotate-clause
        class GreaterThan(Func):
            arg_joiner = ">"
            arity = 2
            function = ""

        zero = Cast(0, output_field=IntegerField())

        # This query is a bit gnarley using postgres-specific JSON functions
        # See jsonb_... functions docs: https://www.postgresql.org/docs/12/functions-json.html
        try:
            annotated_grants = (
                current_grants.annotate(
                    geocodes=Func(
                        F("data"),
                        V("$.beneficiaryLocation[*] ? (exists(@.geoCode))"),
                        function="jsonb_path_query_array",
                        output_field=JSONField(),
                    ),
                    lookup_count=Func(
                        F("additional_data__locationLookup"),
                        function="jsonb_array_length",
                        output_field=IntegerField(),
                    ),
                )
                .annotate(
                    geocode_count=Func(
                        F("geocodes"),
                        function="jsonb_array_length",
                        output_field=IntegerField(),
                    ),
                )
                .annotate(
                    has_geocode=GreaterThan(
                        Cast(F("geocode_count"), output_field=IntegerField()),
                        zero,
                        output_field=BooleanField(),
                    ),
                    has_lookup=GreaterThan(
                        Cast(F("lookup_count"), output_field=IntegerField()),
                        zero,
                        output_field=BooleanField(),
                    ),
                )
            )

            result_grants = annotated_grants.filter(has_geocode=True, has_lookup=False)

            NUM_CURRENT_GRANTS_WITH_BENEFICIARY_LOCATION_GEOCODE_WITHOUT_LOOKUP.set(
                result_grants.count()
            )
        except django.db.Error as e:
            NUM_CURRENT_GRANTS_WITH_BENEFICIARY_LOCATION_GEOCODE_WITHOUT_LOOKUP.set(-1)
            logger.error(
                "Error calculating grants with beneficiary location without lookup",
                exc_info=e,
            )

    def get(self, *args, **kwargs):
        # Update gauges unless we're in the middle of processing/loading
        if db.Status.all_idle_and_ready():
            self._num_errors_log()
            self._total_latest_grants()
            self._total_datagetter_grants()
            self._total_num_sources_in_last_run()
            self._num_current_grants_with_beneficiary_location_geocode_without_lookup()

        # Generate latest uses default of the global registry
        return HttpResponse(generate_latest(), content_type="text/plain")
