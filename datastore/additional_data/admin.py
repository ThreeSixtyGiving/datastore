from django.contrib import admin
from django.contrib.postgres.fields import JSONField
from prettyjson import PrettyJSONWidget

import additional_data.models as db


class JSONFieldAdmin(admin.ModelAdmin):
    list_per_page = 20
    formfield_overrides = {
        JSONField: {"widget": PrettyJSONWidget(attrs={"initial": "parsed"})}
    }


admin.site.register(db.OrgInfoCache, JSONFieldAdmin)

admin.site.register(db.TSGOrgType)
