from django.urls import path
from django.views.generic import TemplateView

from django.conf import settings
import api.grantnav.api
import api.experimental.api
import api.control.api

app_name = 'api'

urlpatterns = [
    path('', TemplateView.as_view(template_name="api.html"), name="index"),
   path('grantnav/updates',
         api.grantnav.api.GrantNavPollForNewData.as_view()),

    path('control/status', api.control.api.StatusView.as_view(),
         name="status"),
    path('control/trigger-datagetter',
         api.control.api.TriggerDataGetter.as_view(),
         name="trigger-datagetter"),
    path('control/abort-datagetter',
         api.control.api.AbortDataGetter.as_view(),
         name="abort-datagetter"),

]

if settings.DEBUG:
    experimental_stuff = [
        path('experimental/canonical',
            api.experimental.api.CanonicalDatasetAll.as_view()),
        path('experimental/canonical/publishers',
            api.experimental.api.CanonicalDatasetPublishers.as_view()),
        path('experimental/canonical/grants',
            api.experimental.api.CanonicalDatasetGrantsView.as_view()),
        path('experimental/canonical/datagetters',
            api.experimental.api.CanonicalDatasetDataGetters.as_view()),

        path('experimental/grantnav/data',
            api.grantnav.api.GrantNavApiView.as_view(),
            name="grantnav"),
    ]

    urlpatterns = urlpatterns + experimental_stuff


