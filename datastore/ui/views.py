from django.views.generic import TemplateView
from db.models import Publisher, GetterRun
from django.urls import reverse_lazy
import db.models as db

# To require login use LoginRequiredMixin
# from django.contrib.auth.mixins import LoginRequiredMixin
# and set login_url = reverse_lazy("admin:login")

class ExploreView(TemplateView):
    template_name = "explore.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['errors'] = []

        context['getter_runs'] = GetterRun.objects.order_by("-datetime")

        if "getter_run" in self.request.GET:
            try:
                getter_run = GetterRun.objects.get(
                        pk=self.request.GET['getter_run'])
            except GetterRun.DoesNotExist:
                context['errors'].append(
                    "Specified data getter run doesn't exist using latest")
                pass

        # If we don't have a getter run selected or there is an error
        if len(context['errors']) > 0 or "getter_run" not in self.request.GET:
            getter_run = context['getter_runs'][0]

        context['getter_run_selected'] = getter_run

        # -1 is  unset
        if "publisher" in self.request.GET and \
           "-1" not in self.request.GET['publisher']:

            try:
                publisher = getter_run.publisher_set.get(
                    prefix=self.request.GET['publisher'])

                context['publisher_selected'] = publisher
            except Publisher.DoesNotExist:
                context['errors'].append(
                    "Publisher doest not exist in the selected data getter run")
                pass

        return context


class DashBoardView(TemplateView):
    template_name = "dash.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['last_getter_run'] = db.GetterRun.objects.order_by("-datetime").first()

        return context
