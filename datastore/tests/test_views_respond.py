from django.test import LiveServerTestCase
from django.urls import URLPattern, reverse_lazy

import db.models as db
from api.urls import urlpatterns as api_urls
from prometheus.urls import urlpatterns as prom_urls
from ui.urls import urlpatterns as ui_urls
from urls import urlpatterns as root_urls


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

        if "slug" in path.pattern.describe() and "int" in path.pattern.describe():
            url = reverse_lazy(path_name, args=("test", 1))
        elif "int" in path.pattern.describe():
            url = reverse_lazy(path_name, args=(1,))
        elif "slug" in path.pattern.describe():
            url = reverse_lazy(path_name, args=("test",))
        else:
            url = reverse_lazy(path_name)

        response = self.client.get(url, HTTP_HOST="localhost", follow=True)

        print("Tested %s = %s" % (url, response.status_code))

        self.assertTrue(
            response.status_code == 200, "Url %s did not return a 200 response" % url
        )

    def test_url_responds(self):
        """ Basic test to make sure all urls/views return """
        for path in root_urls:
            self._test_url(path)

        for path in api_urls:
            db.Status.objects.create(
                what=db.Statuses.GRANTNAV_DATA_PACKAGE, status=db.Statuses.READY
            )

            self._test_url(path, "api")

        for path in ui_urls:
            self._test_url(path, "ui")

        for path in prom_urls:
            self._test_url(path, "prometheus")
