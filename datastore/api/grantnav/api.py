from django.http.response import StreamingHttpResponse, JsonResponse
from django.views import View
import db.models as db
from django.conf import settings

import json


class GrantNavApiView(View):
    """ Special API endpoint to stream data to GrantNav """

    def get(self, *args, **kwargs):
        print(self.request.GET)
        limit = int(self.request.GET.get('limit', 400))

        def output_generator():
            grants = db.Grant.objects.all()[:limit]

            yield b'['

            for i, grant in enumerate(grants):
                data_item = {
                    'publisher': grant.publisher.data,
                    'grant': grant.data,
                }

                yield json.dumps(data_item)

                if i < (len(grants)-1):
                    yield ','

            yield b']'

        return StreamingHttpResponse(output_generator(),
                                     content_type='text/json; charset=UTF-8')


class GrantNavPollForNewData(View):
    """ API endpoint for GrantNav to poll to know that new data is available """

    def get(self, *args, **kwargs):
        statuses = db.Status.objects.all()

        ret = {}

        # Turn the status into a key val dict
        for status_ob in statuses:
            ret[status_ob.what] = { 'status': status_ob.status, 'when': status_ob.when }
            if db.Statuses.GRANTNAV_DATA_PACKAGE in status_ob.what:
                ret[status_ob.what]['download'] = settings.GRANTNAV_PACKAGE_DOWNLOAD_URL


        return JsonResponse(ret, safe=False)