"""
WSGI config for datastore project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/howto/deployment/wsgi/
"""

import atexit
import os

from django.core.wsgi import get_wsgi_application
from prometheus_client import multiprocess

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.settings")

application = get_wsgi_application()

# If application is running via uWSGI register atext() handler to clean up prometheus
# metric files when process dies.
try:
    from uwsgidecorators import postfork

    @postfork
    def setup_prometheus_cleanup():
        def cleanup_worker_metrics():
            multiprocess.mark_process_dead(os.getpid())

        atexit.register(cleanup_worker_metrics)

except ImportError:
    pass
