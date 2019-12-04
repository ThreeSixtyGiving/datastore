from prometheus_client import Gauge
from prometheus_client.exposition import generate_latest

from django.http.response import HttpResponse
from django.views import View
from django.conf import settings

import db.models as db


class ServiceMetrics(View):

    def __init__(self, *args, **kwargs):
        self._num_errors_log()
        self._total_latest_grants()
        self._total_datagetter_grants()

    def _num_errors_log(self):
        errors = 0
        s = Gauge("total_service_errors_logged", "Total number of errors logged by last service run")
        log_file = getattr(settings, "DATA_RUN_LOG", "")

        try:
            with open(log_file, "r") as lf:
                for line in lf.readlines():
                    if "error" in line or "exception" in line or "failure" in line:
                        errors = errors + 1
        except FileNotFoundError:
            errors = -1
            pass

        s.set(errors)

    def _total_latest_grants(self):
        s = Gauge('total_latest_grants', 'Total number of latest grants in the system')
        total = db.Latest.objects.get(series=db.Latest.CURRENT).grant_set.count()
        s.set(total)

    def _total_datagetter_grants(self):
        s = Gauge('total_datagetter_grants', 'Total number of grants in the last datagetter run')
        total = db.GetterRun.objects.last().grant_set.count()
        s.set(total)

    def get(self, *args, **kwargs):
        # Generate latest uses default of the global registry
        return HttpResponse(generate_latest(), content_type="text/plain")
