from django.db import models
from django.contrib.postgres.fields import ArrayField


class PublisherMetrics(models.Model):
    timestamp = models.DateTimeField()
    publisher_prefix = models.TextField()
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"<PublisherMetrics {self.timestamp} {self.publisher_prefix}>"


class SourceFileMetrics(models.Model):
    timestamp = models.DateTimeField()
    publisher_prefix = models.TextField()
    sourcefile_identifier = models.TextField()
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"<SourceFileMetrics {self.timestamp} {self.publisher_prefix} {self.sourcefile_identifier}>"


class FunderMetrics(models.Model):
    timestamp = models.DateTimeField()
    funder_org_id = models.TextField()
    funder_non_primary_org_ids = ArrayField(models.TextField())
    metrics = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"<FunderMetrics {self.timestamp} {self.funder_org_id} {self.funder_non_primary_org_ids}>"
