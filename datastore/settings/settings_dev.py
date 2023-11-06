# flake8: noqa
<<<<<<< Updated upstream
=======
import os
import socket
import hashlib
>>>>>>> Stashed changes
from settings.settings import *

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
