from django.db import models
from django.db.utils import DataError
from db.common import CanonicalDataset
from django.db import connection
from django.utils import timezone
from django.contrib.postgres.fields import JSONField
import django.db.models.signals
from django.core.cache import cache


class GetterRun(models.Model):
    datetime = models.DateTimeField(default=timezone.now)

    def delete_all_data_from_run(self):
        self.grant_set.all().delete()
        self.sourcefile_set.all().delete()
        self.publisher_set.all().delete()

    def __str__(self):
        return str(self.datetime)


class SourceFile(models.Model):
    data = JSONField()
    getter_run = models.ForeignKey(GetterRun, on_delete=models.CASCADE)

    # Convenience fields
    datagetter_data = JSONField(null=True)
    data_valid = models.BooleanField(default=False)
    acceptable_license = models.BooleanField(default=False)
    downloads = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        try:
            # These keys could be missing because the download failed
            # and therefore it can't validate or check the license
            self.data_valid = self.data['datagetter_metadata']['valid']
            self.acceptable_license = self.data['datagetter_metadata']['acceptable_license']
        except KeyError:
            pass
        self.datagetter_data = self.data['datagetter_metadata']
        self.downloads = self.data['datagetter_metadata']['downloads']
        super().save(*args, **kwargs)

    def __str__(self):
        return self.data['datagetter_metadata']['datetime_downloaded']


class Publisher(models.Model):

    data = JSONField()

    getter_run = models.ForeignKey(GetterRun, on_delete=models.CASCADE)

    # Convenience fields
    name = models.TextField(null=True, blank=True)
    prefix = models.CharField(max_length=300)

    #  Update the convenience fields
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.data['name']

        if not self.prefix:
            self.prefix = self.data['prefix']
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s (datagetter %s)" % (self.name, str(self.getter_run.datetime))

    class Meta:
        unique_together = ("getter_run", "prefix")


class Grant(models.Model):
    grant_id = models.CharField(max_length=300)
    data = JSONField(verbose_name="Grant data")

    getter_run = models.ForeignKey(GetterRun, on_delete=models.CASCADE)
    publisher = models.ForeignKey(Publisher, on_delete=models.DO_NOTHING)
    source_file = models.ForeignKey(SourceFile, on_delete=models.DO_NOTHING)

    @staticmethod
    def estimated_total():
        """ Big table count() is expensive so estimate instead """
        try:
            with connection.cursor() as c:
                # https://www.citusdata.com/blog/2016/10/12/count-performance/
                c.execute(
                    " SELECT (reltuples/relpages) * (pg_relation_size('db_grant') / "
                    " (current_setting('block_size')::integer)) "
                    " FROM pg_class where relname = 'db_grant'"
                    )
                return int(c.fetchone()[0])
        except DataError:
            return Grant.objects.count()

    def __str__(self):
        return self.grant_id


class Statuses(object):
    COMPLETE = "complete"
    IDLE = "idle"
    IN_PROGRESS = "in progress"
    LOADING_DATA = "loading data"
    READY = "ready"

    DATAGETTER = "datagetter"
    DATASTORE = "datastore"
    GRANTNAV_DATA_PACKAGE = "grantnav_data_package"


class Status(models.Model):
    what = models.CharField(max_length=200)
    status = models.CharField(max_length=200, default=Statuses.IDLE)
    when = models.DateTimeField(auto_now=True)


def invalidate_cache(**kwargs):
    # Ignore these models as they don't affect the core data directly
    if type(kwargs.get('instance')) is Status:
        return

    cache.delete(CanonicalDataset.CANONICAL_DATASET_CACHE_KEY)


django.db.models.signals.post_save.connect(invalidate_cache)
django.db.models.signals.post_delete.connect(invalidate_cache)
django.db.models.signals.m2m_changed.connect(invalidate_cache)
