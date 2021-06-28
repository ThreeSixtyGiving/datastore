from django.contrib.postgres.fields import JSONField
from django.db import connection, models
from django.db.utils import DataError
from django.utils import timezone


class Latest(models.Model):
    """Latest best data we have"""

    NEXT = "NEXT"
    CURRENT = "CURRENT"
    PREVIOUS = "PREVIOUS"

    SERIES_CHOICES = [(NEXT, "Next"), (CURRENT, "Current"), (PREVIOUS, "Previous")]

    series = models.TextField(choices=SERIES_CHOICES)
    updated = models.DateTimeField(default=timezone.now)

    @staticmethod
    def update():
        latest_getter = GetterRun.objects.order_by("-datetime")[:1].get()

        # Delete any old nexts hanging around
        Latest.objects.filter(series=Latest.NEXT).delete()
        latest_next = Latest.objects.create(series=Latest.NEXT)

        grant_count = 0

        # All the good downloads
        for good_source in latest_getter.sourcefile_set.filter(
            downloads=True, data_valid=True, acceptable_license=True
        ):
            # Extra check make sure the source actually has grants.
            # It isn't much good if not.
            source_grant_count = good_source.grant_set.count()

            grant_count += source_grant_count

            if source_grant_count > 0:
                latest_next.sourcefile_set.add(good_source)

        for failed_source in latest_getter.sourcefile_set.filter(
            models.Q(downloads=False) | models.Q(data_valid=False)
        ):

            failed_id = failed_source.data["identifier"]
            print(
                "Processing the failed source %s\n%s" % (failed_id, failed_source.data)
            )
            replacement_found = False

            # Find a replacement source for a failed one
            for candidate_replacement_source in SourceFile.objects.filter(
                data__identifier=failed_id,
                data_valid=True,
                acceptable_license=True,
                downloads=True,
            ).order_by("-getter_run"):

                # Extra check make sure the source actually has grants.
                # It isn't much good if not.
                source_grant_count = candidate_replacement_source.grant_set.count()

                grant_count += source_grant_count

                if source_grant_count > 0:
                    print(
                        "Found new source for failed_source %s which is %s"
                        % (failed_id, candidate_replacement_source)
                    )
                    latest_next.sourcefile_set.add(candidate_replacement_source)
                    # We found a replacement:
                    replacement_found = True
                    break

            if not replacement_found:
                print("Warning - No replacement source available for %s" % failed_id)

        # Before we set this as current check that there are more than 0 grants
        # Do the switcher-round
        if grant_count > 0:
            # Delete the old previous
            Latest.objects.filter(series=Latest.PREVIOUS).delete()
            # Make the current the previous
            current, c_created = Latest.objects.get_or_create(series=Latest.CURRENT)
            current.series = Latest.PREVIOUS
            current.save()

            # Make the next the current
            latest_next.series = Latest.CURRENT
            latest_next.save()
            # Just to be less confusing later on
            latest_current = latest_next

            # Update our shortcut latest->grants
            # Access the through model (the m2m table) directly to do bulk update
            ThroughModel = Latest.grant_set.through
            grants_for_latest = []

            for grant in latest_next.sourcefile_set.values_list(
                "grant", flat=True
            ).iterator():
                grants_for_latest.append(
                    ThroughModel(grant_id=grant, latest_id=latest_current.pk)
                )

            ThroughModel.objects.bulk_create(grants_for_latest)

        else:
            raise Exception("The data provided no grants to generate an update")

    def __str__(self):
        return self.series


class GetterRun(models.Model):
    datetime = models.DateTimeField(default=timezone.now)
    archived = models.BooleanField(default=False)

    def delete_all_data_from_run(self):
        self.grant_set.all().delete()
        self.sourcefile_set.all().delete()
        self.publisher_set.all().delete()

    def archive_run(self):
        """Archive the run and delete grant data"""
        self.grant_set.all().delete()
        self.archived = True
        self.save()

    def __str__(self):
        return str(self.datetime)


class SourceFile(models.Model):
    data = JSONField()
    getter_run = models.ForeignKey(GetterRun, on_delete=models.CASCADE)
    latest = models.ManyToManyField(Latest)
    quality = JSONField(null=True)
    aggregate = JSONField(null=True)

    # Convenience fields
    datagetter_data = JSONField(null=True)
    data_valid = models.BooleanField(default=False)
    acceptable_license = models.BooleanField(default=False)
    downloads = models.BooleanField(default=False)

    # We have this as an array but for now we can assume it will only have
    # one item for the purposes of our api.
    def get_distribution(self):
        return self.data["distribution"][0]

    def get_publisher(self):
        return Publisher.objects.get(
            getter_run=self.getter_run, prefix=self.data["publisher"]["prefix"]
        )

    def save(self, *args, **kwargs):
        try:
            # These keys could be missing because the download failed
            # and therefore it can't validate or check the license
            self.data_valid = self.data["datagetter_metadata"]["valid"]
            self.acceptable_license = self.data["datagetter_metadata"][
                "acceptable_license"
            ]
        except KeyError:
            pass
        self.datagetter_data = self.data["datagetter_metadata"]
        self.downloads = self.data["datagetter_metadata"]["downloads"]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.data["datagetter_metadata"]["datetime_downloaded"]

    class Meta:
        ordering = ["data__publisher__prefix"]


class Publisher(models.Model):

    data = JSONField()
    quality = JSONField(null=True)
    aggregate = JSONField(null=True)

    getter_run = models.ForeignKey(GetterRun, on_delete=models.CASCADE)

    # Convenience fields
    name = models.TextField(null=True, blank=True)
    prefix = models.CharField(max_length=300)

    def get_sourcefiles(self):
        return SourceFile.objects.filter(
            getter_run=self.getter_run, data__publisher__prefix=self.prefix
        )

    def get_quality_stats(self):
        from data_quality import quality_data

        return quality_data.aggregated_stats(
            self.get_sourcefiles(),
            "publishers_list",
            "publishers_list_%s" % self.prefix,
        )

    #  Update the convenience fields
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.data["name"]

        if not self.prefix:
            self.prefix = self.data["prefix"]
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s (datagetter %s)" % (self.name, str(self.getter_run.datetime))

    class Meta:
        unique_together = ("getter_run", "prefix")
        ordering = ["prefix"]


class Grant(models.Model):
    grant_id = models.CharField(max_length=300)
    data = JSONField(verbose_name="Grant data")

    getter_run = models.ForeignKey(GetterRun, on_delete=models.CASCADE)
    publisher = models.ForeignKey(Publisher, on_delete=models.DO_NOTHING)
    source_file = models.ForeignKey(SourceFile, on_delete=models.DO_NOTHING)
    # Convenience shortcut to latest->grants
    latest = models.ManyToManyField(Latest)

    additional_data = JSONField(
        verbose_name="Additional Grant data", null=True, blank=True
    )

    @staticmethod
    def estimated_total():
        """Big table count() is expensive so estimate instead"""
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
