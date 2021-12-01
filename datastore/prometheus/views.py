import re

from django.conf import settings
from django.http.response import HttpResponse
from django.views import View
from django.db.models import Q
from prometheus_client import Gauge
from prometheus_client.exposition import generate_latest

import db.models as db

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
        total = db.GetterRun.objects.last().grant_set.count()
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

    def get(self, *args, **kwargs):
        # Update gauges
        self._num_errors_log()
        self._total_latest_grants()
        self._total_datagetter_grants()
        self._total_num_sources_in_last_run()
        # Generate latest uses default of the global registry
        return HttpResponse(generate_latest(), content_type="text/plain")
