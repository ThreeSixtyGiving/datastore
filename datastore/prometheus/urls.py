from django.urls import path

import prometheus.views

app_name = 'prometheus'

urlpatterns = [
    path('metrics', prometheus.views.ServiceMetrics.as_view(), name="service-metrics"),
]
