from django.test import TestCase
import prometheus.views

import tempfile


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
