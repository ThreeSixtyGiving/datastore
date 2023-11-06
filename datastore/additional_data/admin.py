from django.contrib import admin
from django.db.models import JSONField
from prettyjson import PrettyJSONWidget

import additional_data.models as db


class JSONFieldAdmin(admin.ModelAdmin):
    list_per_page = 20
    formfield_overrides = {
        JSONField: {"widget": PrettyJSONWidget(attrs={"initial": "parsed"})}
    }


admin.site.register(db.OrgInfoCache, JSONFieldAdmin)
admin.site.register(db.TSGOrgType)
admin.site.register(db.NSPL)
admin.site.register(db.GeoCodeName)
admin.site.register(db.GeoLookup)
admin.site.register(db.CodelistCode)
