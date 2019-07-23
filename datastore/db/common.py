from django.core.cache import cache
from db import models as db
from django.core.paginator import Paginator


class CanonicalDataset(object):
    """ Returns a dataset that represents the best data available
    {
     datagetters_used : [],
     publishers : [ ],
     grants: [],
     total_grants,
    }
    """

    CANONICAL_DATASET_CACHE_KEY = 'canonical-cache-key'
    MAX_PAGE_SIZE = 100

    def __init__(self, *args, **kwargs):
        self.datagetters_used = []
        self.grants = []
        self.sources = []
        self.publishers = {}
        self.disable_cache = False

        if self._load_from_cache() is False:
            self.get()
            self._store_cache()

        print("setting up paginator")
        self.paginated_grants = Paginator(self.grants, self.MAX_PAGE_SIZE)
        print("end setting up paginator")

        super().__init__(*args, **kwargs)

    def _add_source(self, source):
        grant_fields = ('id', 'publisher_id', 'grant_id', 'source_file_id', 'data')

        publisher = db.Publisher.objects.get(
            prefix=source.data['publisher']['prefix'],
            getter_run=self.datagetters_used[0],
        )

        self.sources.append({
            'id': source.id,
            'data': source.data
        })

        self.publishers[publisher.id] = publisher.data

        self.grants = self.grants + list(source.grant_set.all().values(*grant_fields))

    def _load_from_cache(self):
        import time

        print("fetching cache from store")
        print(time.time())
        data_cache = cache.get(self.CANONICAL_DATASET_CACHE_KEY)
        print("done fetching cache from store")
        print(time.time())

        if data_cache and self.disable_cache is not True and len(data_cache['grants']) > 0:
            print("CACHE HIT - Loading cache")
            self.datagetters_used = data_cache['datagetters_used']
            self.grants = data_cache['grants']
            self.sources = data_cache['sources']
            self.publishers = data_cache['publishers']
            self.total_grants = data_cache['total_grants']
            print("FINSHED LOADING cache")

            return True

        return False

    def _store_cache(self):
        data_cache = {
            'datagetters_used': self.datagetters_used,
            'grants': self.grants,
            'publishers': self.publishers,
            'total_grants': self.total_grants,
            'sources': self.sources,
        }
        print("Storing cache")
        cache.set(self.CANONICAL_DATASET_CACHE_KEY, data_cache, timeout=None)

    def get(self):
        latest_getter = db.GetterRun.objects.order_by("-datetime")[:1].get()
        self.datagetters_used.append(latest_getter.id)

        print("Using datetime %s" % latest_getter.datetime)

        for good_source in latest_getter.sourcefile_set.filter(downloads=True,
                                                               data_valid=True,
                                                               acceptable_license=True):
            self._add_source(good_source)

        for failed_source in latest_getter.sourcefile_set.filter(downloads=False,
                                                                 data_valid=True,
                                                                 acceptable_license=True):
            failed_id = failed_source.data['identifier']
            new_source = db.SourceFile.objects.filter(data__identifier=failed_id,
                                                      downloads=True)[:1].get()
            self.datagetters_used.append(new_source.getter_run.id)

            self._add_source(new_source)

            print("found new source for failed_source %s which is %s" % (failed_id, new_source))

        self.total_grants = len(self.grants)
