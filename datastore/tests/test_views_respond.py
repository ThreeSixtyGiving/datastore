from django.test import LiveServerTestCase
from django.urls import URLPattern, reverse_lazy
from django.core.management import call_command


import db.models as db
from api.urls import urlpatterns as api_urls
from prometheus.urls import urlpatterns as prom_urls
from ui.urls import urlpatterns as ui_urls
from urls import urlpatterns as root_urls

import time

# test urls/views Adapted from YQN by Michael Wood GPLv2


class UrlsTests(LiveServerTestCase):
    fixtures = ["test_data.json"]

    def _test_url(self, path, namespace=False):
        if type(path) is not URLPattern or path.name is None:
            return

        if namespace:
            path_name = "%s:%s" % (namespace, path.name)
        else:
            path_name = path.name

        if "<slug" in path.pattern.describe() and "<int" in path.pattern.describe():
            url = reverse_lazy(path_name, args=("test", 1))
        elif "<int" in path.pattern.describe():
            url = reverse_lazy(path_name, args=(1,))
        elif ":org_id>" in path.pattern.describe():
            url = reverse_lazy(
                path_name, kwargs={"org_id": "GB-CHC-9000006"}
            )  # org_id picked from test_data.json
        elif ":grant_id>" in path.pattern.describe():
            url = reverse_lazy(
                path_name, kwargs={"grant_id": "360G-kahM5Ooc2u"}
            )  # grant_id picked from test_data.json
        elif ":publisher_prefix>" in path.pattern.describe():
            url = reverse_lazy(path_name, args=("360g-Ahtahs5vaj",))
        elif ":log_name>" in path.pattern.describe():
            url = reverse_lazy(path_name, kwargs={"log_name": "data_run"})
        else:
            url = reverse_lazy(path_name)

        response = self.client.get(url, HTTP_HOST="localhost", follow=True)

        print("Tested %s = %s" % (url, response.status_code))

        self.assertTrue(
            response.status_code == 200, "Url %s did not return a 200 response" % url
        )

    def test_url_responds(self):
        """Basic test to make sure all urls/views return"""
        db.Status.objects.create(
            what=db.Statuses.GRANTNAV_DATA_PACKAGE, status=db.Statuses.READY
        )

        # For the quality dash data we need to have these objects present
        call_command("rewrite_quality_data", "latest")

        for path in root_urls:
            self._test_url(path)

        for path in api_urls:
            # Avoid hitting the throttle limit on the api
            # Tried to @override_settings this but doesn't work
            time.sleep(0.5)
            self._test_url(path, "api")

        for path in ui_urls:
            self._test_url(path, "ui")

        for path in prom_urls:
            self._test_url(path, "prometheus")
