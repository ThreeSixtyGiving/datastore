from settings.settings import *  # noqa F401, F403
from settings.settings import REST_FRAMEWORK

# Don't throttle in test environment
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
REST_FRAMEWORK["DEFAULT_THROTTLE_RATE"] = {}
