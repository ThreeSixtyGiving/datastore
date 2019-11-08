from django.urls import path
from django.views.generic import TemplateView

import api.grantnav.api
import api.control.api

app_name = 'api'

urlpatterns = [
    path('', TemplateView.as_view(template_name="api.html"), name="index"),
    path('grantnav/updates',
         api.grantnav.api.GrantNavPollForNewData.as_view(),
         name="updates"),
    path('control/status', api.control.api.StatusView.as_view(),
         name="status"),
    path('control/trigger-datagetter',
         api.control.api.TriggerDataGetter.as_view(),
         name="trigger-datagetter"),
    path('control/abort-datagetter',
         api.control.api.AbortDataGetter.as_view(),
         name="abort-datagetter"),
]
