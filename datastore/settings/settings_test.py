import os

from settings.settings import *  # noqa F401, F403
from settings.settings import REST_FRAMEWORK

# Don't throttle in test environment
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
REST_FRAMEWORK["DEFAULT_THROTTLE_RATE"] = {}

# Set default directory for prometheus multiprocessing.
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", "/tmp/prom-multiprocess-dir")
os.makedirs(os.environ.get("PROMETHEUS_MULTIPROC_DIR"), exist_ok=True)
