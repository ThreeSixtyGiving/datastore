from django.views.generic import TemplateView
from django.conf import settings

from db.models import Publisher, GetterRun
import db.models as db

import subprocess
import os
import datetime

# Note To require login use LoginRequiredMixin
# from django.contrib.auth.mixins import LoginRequiredMixin
# and set login_url = reverse_lazy("admin:login")
# from django.urls import reverse_lazy


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
            getter_run = context['getter_runs'].first()

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

    @staticmethod
    def git_revision():
        return subprocess.check_output(
            ['git show --format=format:%h  --no-patch'],
            shell=True).decode()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context['last_getter_run'] = db.GetterRun.objects.order_by("-datetime").first()
        context['total_grants'] = db.Grant.estimated_total()
        context['total_datagetter_runs'] = db.GetterRun.objects.count()

        # May not be generated yet
        try:
            context['latest_current'] = db.Latest.objects.get(series=db.Latest.CURRENT)
        except db.Latest.DoesNotExist:
            pass

        # Not critical if this fails e.g. git not installed
        try:
            context['git_rev'] = DashBoardView.git_revision()
        except Exception:
            pass

        return context


class LogView(TemplateView):
    template_name = "log.html"

    def read_log_file(self, log_file):
        """ Returns log content and datetime of modified """
        try:
            with open(log_file, 'r') as f:
                return f.read(), datetime.datetime.fromtimestamp(
                    int(os.stat(log_file).st_mtime))

        except FileNotFoundError:
            return "Error unable to read log file", ""

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        log_name = kwargs.get('log_name')

        context['log_content'] = "No valid log selected"

        if not log_name:
            return context

        if log_name == 'data_run':
            log_file = getattr(settings, "DATA_RUN_LOG", "")

            context['log_content'], context['date_modified'] = \
                self.read_log_file(log_file)

        return context
