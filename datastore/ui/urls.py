from django.urls import path
from django.views.generic import TemplateView

import ui.views

app_name = "ui"

urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html"), name="index"),
    path("explore", TemplateView.as_view(template_name="explore.html"), name="explore"),
    path("explore/latest", ui.views.ExploreLatestView.as_view(), name="explore-latest"),
    path(
        "explore/datagetter",
        ui.views.ExploreDatagetterView.as_view(),
        name="explore-datagetter",
    ),
    path("dashboard", ui.views.DashBoardView.as_view(), name="dashboard"),
    path("dashboard/log/<slug:log_name>", ui.views.LogView.as_view(), name="log"),
]
