from django.urls import path
from django.views.generic import TemplateView

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

import api.control.api
import api.experimental.api
import api.grantnav.api
import api.dashboard.api
import api.org.api_schema


app_name = "api"

urlpatterns = [
    path("", TemplateView.as_view(template_name="api.html"), name="index"),
    path(
        "dashboard/publishers",
        api.dashboard.api.Publishers.as_view(),
        name="publishers",
    ),
    path(
        "dashboard/overview",
        api.dashboard.api.Overview.as_view(),
        name="overview",
    ),
    path(
        "dashboard/publisher/<str:publisher_prefix>",
        api.dashboard.api.Publisher.as_view(),
        name="publisher",
    ),
    path(
        "grantnav/updates",
        api.grantnav.api.GrantNavPollForNewData.as_view(),
        name="grantnav-updates",
    ),
    path("control/status", api.control.api.StatusView.as_view(), name="status"),
    path(
        "control/trigger-datagetter",
        api.control.api.TriggerDataGetter.as_view(),
        name="trigger-datagetter",
    ),
    path(
        "control/abort-datagetter",
        api.control.api.AbortDataGetter.as_view(),
        name="abort-datagetter",
    ),
    path(
        "experimental/CurrentLatestGrants",
        api.experimental.api.CurrentLatestGrants.as_view(),
        name="current-latest-grants",
    ),
    path(
        "experimental/org/<path:org_id>/grants_made",
        api.experimental.api.OrganisationGrantsMadeView.as_view(),
        name="organisation-grants-made",
    ),
    path(
        "experimental/org/<path:org_id>/grants_received",
        api.experimental.api.OrganisationGrantsReceivedView.as_view(),
        name="organisation-grants-received",
    ),
    path(
        "experimental/org/<path:org_id>",
        api.experimental.api.OrganisationDetailView.as_view(),
        name="organisation-detail",
    ),
    path(
        "experimental/org",
        api.experimental.api.OrganisationListView.as_view(),
        name="organisation-list",
    ),
    path(
        "experimental/grant/<str:grant_id>",
        api.experimental.api.GrantDetailView.as_view(),
        name="grant-detail",
    ),
    # Schema UI
    path(
        "experimental/schema/",
        api.org.api_schema.APISchemaView.as_view(),
        name="schema",
    ),
    # Optional UI:
    path(
        "swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="api:schema"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="api:schema"),
        name="redoc",
    ),
]
