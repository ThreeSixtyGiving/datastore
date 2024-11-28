from django.contrib import admin

from monitoring.models import (
    PublisherMetricsRecord,
    FunderMetricsRecord,
    SourceFileMetricsRecord,
)

# Register your models here.
admin.site.register(PublisherMetricsRecord)
admin.site.register(FunderMetricsRecord)
admin.site.register(SourceFileMetricsRecord)
