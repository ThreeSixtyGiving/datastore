import tempfile
import time

from django.core import management
from django.test import TestCase

import prometheus.views
from db.models import Status, Statuses


class TestMetrics(TestCase):
    def test_num_of_errors(self):
        view = prometheus.views.ServiceMetrics()

        with tempfile.NamedTemporaryFile() as log_file:
            log_file.write(b"Abcdef error\nException: test\n one two")
            log_file.flush()
            with self.settings(DATA_RUN_LOG=log_file.name):
                view._num_errors_log()

        suffix, labels, value = prometheus.views.NUM_ERRORS_LOGGED._samples()[0]

        self.assertEqual(value, 2.0, "unexpected number of errors in metrics")

    def test_status_durations(self):
        view = prometheus.views.ServiceMetrics()

        Status.objects.create(what="datagetter", status=Statuses.IDLE)
        Status.objects.create(what="datastore", status=Statuses.IDLE)
        Status.objects.create(what="grantnav_data_package", status=Statuses.READY)
        Status.objects.create(what="monitoring_snapshot", status=Statuses.READY)

        management.call_command("set_status", what="datagetter", status="IN_PROGRESS")
        time.sleep(2)
        management.call_command("set_status", what="datagetter", status="IDLE")
        (
            suffix,
            labels,
            value,
        ) = prometheus.views.DURATION_OF_LAST_RUN_FOR_DATAGETTER._samples()[0]
        self.assertAlmostEqual(value, 2, places=1)

        management.call_command("set_status", what="datastore", status="IN_PROGRESS")
        time.sleep(2)
        management.call_command("set_status", what="datastore", status="IDLE")
        (
            suffix,
            labels,
            value,
        ) = prometheus.views.DURATION_OF_LAST_RUN_FOR_DATASTORE_LOAD._samples()[0]
        self.assertAlmostEqual(value, 2, places=1)

        management.call_command(
            "set_status", what="grantnav_data_package", status="IN_PROGRESS"
        )
        time.sleep(2)
        management.call_command(
            "set_status", what="grantnav_data_package", status="READY"
        )
        (
            suffix,
            labels,
            value,
        ) = prometheus.views.DURATION_OF_LAST_RUN_FOR_GRANTNAV_DATA_PACKAGE_BUILD._samples()[
            0
        ]
        self.assertAlmostEqual(value, 2, places=1)

        time.sleep(2)
        view._time_since_last_grantnav_data_package_build()
        (
            suffix,
            labels,
            value,
        ) = prometheus.views.TIME_SINCE_LAST_GRANTNAV_DATA_PACKAGE_BUILD._samples()[0]
        self.assertAlmostEqual(value, 2, places=1)

        management.call_command(
            "set_status", what="monitoring_snapshot", status="IN_PROGRESS"
        )
        time.sleep(2)
        management.call_command(
            "set_status", what="monitoring_snapshot", status="READY"
        )
        (
            suffix,
            labels,
            value,
        ) = prometheus.views.DURATION_OF_LAST_RUN_FOR_MONITORING_SNAPSHOT._samples()[0]
        self.assertAlmostEqual(value, 2, places=1)
