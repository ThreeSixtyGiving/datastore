# flake8: noqa
from settings.settings import *

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "360givingdatastore",
        "USER": "",
        "PASSWORD": "",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
