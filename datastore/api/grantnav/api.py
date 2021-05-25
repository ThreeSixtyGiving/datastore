from django.conf import settings
from django.http.response import JsonResponse
from django.views import View

import db.models as db


class GrantNavPollForNewData(View):
    """API endpoint for GrantNav to poll to know that new data is available"""

    def get(self, *args, **kwargs):
        statuses = db.Status.objects.all()

        ret = {}

        # Turn the status into a key val dict
        for status_ob in statuses:
            ret[status_ob.what] = {"status": status_ob.status, "when": status_ob.when}
            if db.Statuses.GRANTNAV_DATA_PACKAGE in status_ob.what:
                ret[status_ob.what]["download"] = settings.GRANTNAV_PACKAGE_DOWNLOAD_URL

        return JsonResponse(ret, safe=False)
