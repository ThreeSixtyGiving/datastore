from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

import chromedriver_autoinstaller

chromedriver_autoinstaller.install()


class BrowserTests(StaticLiveServerTestCase):
    """Browser test using latest Chrome/Chromium stable"""

    def setUp(self, *args, **kwargs):
        capabilities = DesiredCapabilities.CHROME
        capabilities["loggingPrefs"] = {"browser": "ALL"}

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        # uncomment this if "DevToolsActivePort" error
        # chrome_options.add_argument("--remote-debugging-port=9222")

        self.driver = webdriver.Chrome(
            service_args=["--verbose", "--log-path=selenium.log"],
            desired_capabilities=capabilities,
            chrome_options=chrome_options,
        )
        self.driver.set_page_load_timeout(15)

    def get(self, url):
        self.driver.get("%s%s" % (self.live_server_url, url))

    def test_page_loads(self):
        self.get("/")

    def tearDown(self):
        self.driver.quit()
