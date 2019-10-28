from django.contrib import admin
from django.contrib.postgres.fields import JSONField
from prettyjson import PrettyJSONWidget
import db.models as db


class JSONFieldAdmin(admin.ModelAdmin):
    list_per_page = 20
    formfield_overrides = {
        JSONField: {'widget': PrettyJSONWidget(attrs={'initial': 'parsed'})}
    }


class PublisherAdmin(JSONFieldAdmin):
    search_fields = ['name']


class GrantAdmin(JSONFieldAdmin):
    search_fields = ['grant_id']


admin.site.site_header = "360 Giving Datastore Developer"
admin.site_site_title = admin.site.site_header

admin.site.register(db.Grant, JSONFieldAdmin)
admin.site.register(db.GetterRun, JSONFieldAdmin)
admin.site.register(db.Publisher, PublisherAdmin)
admin.site.register(db.SourceFile, JSONFieldAdmin)
admin.site.register(db.Status, JSONFieldAdmin)
admin.site.register(db.Latest)
