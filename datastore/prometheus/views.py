import re

from django.conf import settings
from django.http.response import HttpResponse
from django.views import View
from prometheus_client import Gauge
from prometheus_client.exposition import generate_latest

import db.models as db

NUM_ERRORS_LOGGED = Gauge(
    "total_service_errors_logged", "Total number of errors logged by last service run"
)

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

    def get(self, *args, **kwargs):
        # Update gauges
        self._num_errors_log()
        self._total_latest_grants()
        self._total_datagetter_grants()
        # Generate latest uses default of the global registry
        return HttpResponse(generate_latest(), content_type="text/plain")
