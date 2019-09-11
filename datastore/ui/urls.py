from django.urls import path
from django.views.generic import TemplateView
import ui.views

app_name = 'ui'

urlpatterns = [
    path('', TemplateView.as_view(template_name='index.html'), name="index"),
    path('explore', ui.views.ExploreView.as_view(), name="explore"),
    path('dashboard', ui.views.DashBoardView.as_view(), name="dashboard")
]
