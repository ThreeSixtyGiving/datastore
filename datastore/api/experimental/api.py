from django.views import View
from django.http import JsonResponse
from db.common import CanonicalDataset

import json
import time



class CanonicalDatasetAll(View):
    def get(self, *args, **kwargs):
        dataset = CanonicalDataset()
        if len(dataset.grants) > 100:
            return JsonResponse({'error': 'dataset too large! use paginated api'})

        data = {
            'datagetters_used': dataset.datagetters_used,
            'grants': dataset.grants,
            'publishers': dataset.publishers,
            'total_grants': dataset.total_grants,
            'sources': dataset.sources,
        }

        return JsonResponse(data)

class CanonicalDatasetPublishers(View):
    def get(self, *args, **kwargs):
        data = CanonicalDataset()
        return JsonResponse(data.publishers)


class CanonicalDatasetDataGetters(View):
    def get(self, *args, **kwargs):
        data = CanonicalDataset()
        return JsonResponse(data.datagetters_used)


class CanonicalDatasetGrantsView(View):
    """ Experimental API endpoint to paginate the CanonicalDataset """

    def get(self, *args, **kwargs):
        print("GET %s", time.time())
        page = int(self.request.GET.get('page', 1))
        canonical_data = CanonicalDataset()
        print("DEF %s", time.time())
        grants = canonical_data.paginated_grants.get_page(page)
        print("GEF %s", time.time())

        data = {
            'grants': grants.object_list,
        }

        if grants.has_next():
            data['next_page']: grants.next_page_number()
        if grants.has_previous():
            data['prev_page']: grants.previous_page_number()


        return JsonResponse(data)
