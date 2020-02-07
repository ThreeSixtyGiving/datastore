import os
import signal
import subprocess

from django.conf import settings
from django.http.response import JsonResponse
from django.views.generic import View

import db.models as db


class StatusView(View):
    def get(self, *args, **kwargs):
        ret = {
            'statuses': list(db.Status.objects.all().values('what', 'status')),
        }

        return JsonResponse(ret, safe=False)


class TriggerDataGetter(View):
    def get(self, *args, **kwargs):
        AbortDataGetter.abort()

        with open(settings.DATA_RUN_PID_FILE, 'w+') as pidf:
            process = subprocess.Popen(["bash", settings.DATA_RUN_SCRIPT], start_new_session=True)
            pidf.write(str(process.pid))

        return JsonResponse({"error": "OK", "pid": process.pid})


class AbortDataGetter(View):
    @staticmethod
    def abort():
        try:
            with open(settings.DATA_RUN_PID_FILE, "r") as pidf:
                pid = pidf.read()
                process_group = os.getpgid(int(pid))
                os.killpg(process_group, signal.SIGTERM)

        except (FileNotFoundError, ProcessLookupError, ValueError):
            # Not already running
            pass

        # Reset all the statuses that might have been set
        for status_item in db.Status.objects.all():
            status_item.status = db.Statuses.IDLE
            status_item.save()

    def get(self, *args, **kwargs):
        AbortDataGetter.abort()
        return JsonResponse({"error": "OK"})
