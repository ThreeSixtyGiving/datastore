# flake8: noqa
import os
import socket
import hashlib
from settings.settings import *  # noqa F401, F403
from settings.settings import REST_FRAMEWORK

# This adds the CORS header to API calls for the django dev server

DEBUG = True


# Use combo of hostname+cwd to generate secret key, so that it's stable across reloads
def get_secret_key():
    secret_key_m = hashlib.sha256()
    secret_key_m.update(socket.gethostname().encode())
    secret_key_m.update(os.getcwd().encode())
    return secret_key_m.digest()


SECRET_KEY = get_secret_key()

INSTALLED_APPS = INSTALLED_APPS + ["corsheaders"]

MIDDLEWARE = MIDDLEWARE + [
    "corsheaders.middleware.CorsMiddleware",
]

CORS_ORIGIN_ALLOW_ALL = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} [{module}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "formatter": "simple",
            "propagate": True,
        },
    },
}

# Don't throttle in dev environment
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
REST_FRAMEWORK["DEFAULT_THROTTLE_RATE"] = {}
