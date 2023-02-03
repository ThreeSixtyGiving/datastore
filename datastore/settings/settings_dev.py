# flake8: noqa
from settings.settings import *

# This adds the CORS header to API calls for the django dev server

DEBUG = True

INSTALLED_APPS = INSTALLED_APPS + ["corsheaders"]

MIDDLEWARE = MIDDLEWARE + [
    "corsheaders.middleware.CorsMiddleware",
]

CORS_ORIGIN_ALLOW_ALL = True
