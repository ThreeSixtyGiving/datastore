import datetime
from typing import Dict, Any

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex, BTreeIndex
from django.db import connection, models
from django.db.models import JSONField, Index
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

    @classmethod
    def grants(cls):
        """Return the QuerySet of latest best Grants."""
        return cls.objects.get(series=cls.CURRENT).grant_set.all()

    @classmethod
    def sourcefiles(cls):
        """Return the QuerySet of latest best SourceFiles."""
        return cls.objects.get(series=cls.CURRENT).sourcefile_set.all()

    @staticmethod
    def update(force_with_zero_grants: bool = False):
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
        if grant_count > 0 or force_with_zero_grants:
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


class GetterRunManager(models.Manager):
    def in_use(self):
        """Return the QuerySet of all GetterRuns in-use by any Latest best."""
        return self.filter(sourcefile__latest__isnull=False).distinct()

    def not_in_use(self):
        """Return the QuerySet of all GetterRuns NOT in-use by any Latest best. Inverse of in_use()."""
        return self.exclude(sourcefile__latest__isnull=False).distinct()


class GetterRun(models.Model):
    objects = GetterRunManager()

    datetime = models.DateTimeField(default=timezone.now)
    archived = models.BooleanField(default=False)

    def delete_all_data_from_run(self):
        # Delete the Grants one SourceFile at a time to save on memory usage
        # because Django loads objects into memory before deleting them in
        # order to trigger signals, cascade deletes etc.
        for sourcefile in self.sourcefile_set.all():
            sourcefile.grant_set.all().delete()
            sourcefile.delete()

    def archive_run(self):
        """Archive the run and delete grant data"""
        self.grant_set.all().delete()
        self.archived = True
        self.save()

    @classmethod
    def latest(cls):
        """Get the most recent GetterRun instance"""
        return cls.objects.latest("datetime")

    def __str__(self):
        return "%s - %s" % (self.pk, self.datetime)

    def is_in_use(self):
        """Check if this GetterRun is included in any Latest best."""
        return GetterRun.objects.in_use().filter(pk=self.pk).exists()


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
        """returns the Publisher object for this source file"""
        return Publisher.objects.get(prefix=self.data["publisher"]["prefix"])

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


def new_default_entity_aggregate_data():
    return {
        "grants": 0,
        "grants_ind": 0,
        "grants_org": 0,
        "minAwardDate": None,
        "maxAwardDate": None,
        "currencies": {},
    }


def new_default_entity_additional_data():
    return {
        "alternative_names": [],
    }


class Entity(models.Model):
    """All the entities that are identified in 360Giving Data"""

    class Meta:
        abstract = True

    org_id = models.CharField(max_length=200)  # Primary Org ID, Unique

    # Allowed to be null or blank for progressive building of the record
    name = models.TextField(null=True, blank=True)

    aggregate = JSONField(default=new_default_entity_aggregate_data)
    additional_data = JSONField(default=new_default_entity_additional_data)

    # Where the org data came from
    GRANT = "GRANT"
    PUBLISHER = "PUBLISHER"
    SOURCES_CHOICES = [(GRANT, "Grant"), (PUBLISHER, "Publisher")]
    source = models.TextField(choices=SOURCES_CHOICES)

    def __str__(self):
        return "%s %s)" % (self.org_id, self.name)

    def add_name(self, name):
        """Adds the primary name and if one already exists adds to the additional_data block"""
        name = name.strip()

        if self.name is None:
            self.name = name
            return

        # Alternative names are ones which are used for this org-id but appear in the grant data
        if self.name != name and name not in self.additional_data["alternative_names"]:
            self.additional_data["alternative_names"].append(name)

    def update_aggregate(self, grant):
        ## Aggregate data
        # {
        #  "grants": 0,
        #  "grants_ind": 0,
        #  "grants_org": 0,
        #  "minAwardDate": yyyy-mm-dd,
        #  "maxAwardDate": yyyy-mm-dd,
        #  "currencies": {
        #       "recipient_org": {
        #         "GBP": { "grants": 0, "total": 0, "min": 0, "max": 0, "avg":0 },
        #         ...
        #       },
        #       "recipient_ind": {
        #         "GBP": { "grants": 0, "total": 0, "min": 0, "max": 0, "avg":0 },
        #         ...
        #       }
        #  },
        # },

        C = "currencies"
        amount = grant["amountAwarded"]
        currency = grant["currency"]

        if grant.get("recipientIndividual"):
            recipient_type = "recipient_ind"
            self.aggregate["grants_ind"] += 1
        else:
            recipient_type = "recipient_org"
            self.aggregate["grants_org"] += 1

        try:
            award_date = datetime.date.fromisoformat(grant["awardDate"][:10])
        except ValueError:
            pass

        self.aggregate["grants"] += 1

        if self.aggregate["minAwardDate"]:
            current_min = datetime.date.fromisoformat(self.aggregate["minAwardDate"])
            if award_date < current_min:
                self.aggregate["minAwardDate"] = award_date.isoformat()
        else:
            self.aggregate["minAwardDate"] = award_date.isoformat()

        if self.aggregate["maxAwardDate"]:
            current_max = datetime.date.fromisoformat(self.aggregate["maxAwardDate"])
            if award_date > current_max:
                self.aggregate["maxAwardDate"] = award_date.isoformat()

        else:
            self.aggregate["maxAwardDate"] = award_date.isoformat()

        # In the chain self.aggregate[C][currency][recipient_type]
        # Any combination of currency and recipient may not have been initialised
        # as a dict so we have to check first.
        if self.aggregate[C].get(currency) == None:
            self.aggregate[C][currency] = {}

        # This is the first grant to create a currency and recipient_type
        # All values can be intialised to this particular grant.
        if self.aggregate[C][currency].get(recipient_type) == None:
            self.aggregate[C][currency][recipient_type] = {
                "total": amount,
                "min": amount,
                "max": amount,
                "avg": amount,
                "grants": 1,
            }
        else:
            # Otherwise add to the existing aggregate data

            self.aggregate[C][currency][recipient_type]["grants"] += 1
            self.aggregate[C][currency][recipient_type]["total"] += amount

            # Important that the avg is calculated _after_ the total number
            # of grants for the currency has been accumulated.
            # NOTE: avg currency amount to be deprecated
            # https://github.com/ThreeSixtyGiving/datastore/issues/292
            self.aggregate[C][currency][recipient_type]["avg"] = (
                self.aggregate[C][currency][recipient_type]["total"]
                / self.aggregate[C][currency][recipient_type]["grants"]
            )

            if self.aggregate[C][currency][recipient_type]["max"] < amount:
                self.aggregate[C][currency][recipient_type]["max"] = amount

            if self.aggregate[C][currency][recipient_type]["min"] > amount:
                self.aggregate[C][currency][recipient_type]["min"] = amount


class Publisher(Entity):
    data = JSONField()
    quality = JSONField(null=True)

    # Convenience fields
    prefix = models.CharField(max_length=300, unique=True)

    def get_latest_sourcefiles(self):
        return Latest.objects.get(series=Latest.CURRENT).sourcefile_set.filter(
            data__publisher__prefix=self.prefix
        )

    @classmethod
    def get_most_recent(cls, org_id: str, queryset=None) -> "Publisher":
        if not queryset:
            queryset = Publisher.objects.all().order_by()
        publishers = queryset.filter(org_id=org_id)
        if len(publishers) == 1:
            return publishers[0]
        elif len(publishers) == 0:
            raise cls.DoesNotExist
        else:
            # Find the publisher with the most recently fetched sourcefile
            def _get_dt(p: Publisher) -> datetime.datetime:
                return (
                    p.get_latest_sourcefiles()
                    .order_by("getter_run__datetime")[0]
                    .getter_run.datetime
                )

            return sorted(list(publishers), key=_get_dt)[-1]

    #  Update the convenience fields
    def save(self, *args, **kwargs):
        if not self.name:
            self.name = self.data["name"]

        if not self.prefix:
            self.prefix = self.data["prefix"]
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s (%s)" % (self.name, self.prefix)

    class Meta:
        ordering = ["prefix"]
        indexes = [Index(fields=["org_id", "name"])]


class Recipient(Entity):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["org_id"], name="recipient_unique_org_id")
        ]
        indexes = [
            GinIndex(fields=["non_primary_org_ids"]),
            Index(fields=["org_id", "name"]),
        ]

    non_primary_org_ids = ArrayField(models.TextField())


class Funder(Entity):
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["org_id"], name="funder_unique_org_id")
        ]
        indexes = [
            GinIndex(fields=["non_primary_org_ids"]),
            Index(fields=["org_id", "name"]),
        ]

    non_primary_org_ids = ArrayField(models.TextField())


class Grant(models.Model):
    grant_id = models.CharField(max_length=300)
    data = JSONField(verbose_name="Grant data")

    getter_run = models.ForeignKey(GetterRun, on_delete=models.CASCADE)
    source_file = models.ForeignKey(SourceFile, on_delete=models.DO_NOTHING)
    # Convenience shortcut to latest->grants
    latest = models.ManyToManyField(Latest)

    additional_data = JSONField(
        verbose_name="Additional Grant data", null=True, blank=True
    )

    # Convenience denormalised fields to aid creating indexes and speedup queries
    publisher_org_id = models.TextField()
    recipient_org_ids = ArrayField(models.TextField())
    funding_org_ids = ArrayField(models.TextField())

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

    class Meta:
        # Indexes on convenience fields to speed up API queries
        # The source_file field in the indexes aims to speed up queries against CURRENT Latest
        indexes = [
            BTreeIndex(fields=["publisher_org_id"]),
            GinIndex(fields=["recipient_org_ids"]),
            GinIndex(fields=["source_file", "recipient_org_ids"]),
            GinIndex(fields=["funding_org_ids"]),
            GinIndex(fields=["source_file", "funding_org_ids"]),
        ]

    @staticmethod
    def from_data(
        data: Dict[str, Any],
        getter_run: GetterRun,
        source_file: SourceFile,
        additional_data: Dict[str, Any],
    ):
        """Make a Grant instance from JSON/dict data and fill out the denormalised convenience fields."""

        return Grant(
            grant_id=data["id"],
            data=data,
            getter_run=getter_run,
            source_file=source_file,
            additional_data=additional_data,
            publisher_org_id=source_file.data["publisher"].get("org_id", "unknown"),
            recipient_org_ids=[
                org["id"]
                # recipientOrganization isn't present in grants to individuals
                for org in data.get("recipientOrganization", list())
                if "id" in org
            ],
            funding_org_ids=[
                org["id"] for org in data["fundingOrganization"] if "id" in org
            ],
        )


class Statuses(object):
    COMPLETE = "complete"
    IDLE = "idle"
    IN_PROGRESS = "in progress"
    LOADING_DATA = "loading data"
    READY = "ready"

    DATAGETTER = "datagetter"
    DATASTORE = "datastore"
    GRANTNAV_DATA_PACKAGE = "grantnav_data_package"
    MONITORING_SNAPSHOT = "monitoring_snapshot"


class Status(models.Model):
    what = models.CharField(max_length=200)
    status = models.CharField(max_length=200, default=Statuses.IDLE)
    when = models.DateTimeField(auto_now=True)

    @staticmethod
    def all_idle_and_ready():
        try:
            return (
                Status.objects.get(what=Statuses.DATAGETTER).status == Statuses.IDLE
                and Status.objects.get(what=Statuses.GRANTNAV_DATA_PACKAGE).status
                == Statuses.READY
                and Status.objects.get(what=Statuses.DATASTORE).status == Statuses.IDLE
                and Status.objects.get(what=Statuses.MONITORING_SNAPSHOT).status
                == Statuses.READY
            )
        except Status.DoesNotExist:
            # We have no status set so we consider this as idle and ready
            return True
