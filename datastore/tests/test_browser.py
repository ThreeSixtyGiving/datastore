from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

import chromedriver_autoinstaller

chromedriver_autoinstaller.install()


class BrowserTests(StaticLiveServerTestCase):
    """Browser test using latest Chrome/Chromium stable"""

    def setUp(self, *args, **kwargs):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
        # uncomment this if "DevToolsActivePort" error
        # chrome_options.add_argument("--remote-debugging-port=9222")

        chrome_service = Service(service_args=["--verbose", "--log-path=selenium.log"])

        self.driver = webdriver.Chrome(
            options=chrome_options,
            service=chrome_service,
            #    desired_capabilities=capabilities,
        )
        self.driver.set_page_load_timeout(15)

    def get(self, url):
        self.driver.get("%s%s" % (self.live_server_url, url))

    def test_page_loads(self):
        self.get("/")

    def tearDown(self):
        self.driver.quit()
