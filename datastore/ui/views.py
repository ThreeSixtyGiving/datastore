import datetime
import os
import subprocess

from django.conf import settings
from django.db.models import Q
from django.views.generic import TemplateView

import db.models as db

# Note To require login use LoginRequiredMixin
# from django.contrib.auth.mixins import LoginRequiredMixin
# and set login_url = reverse_lazy("admin:login")
# from django.urls import reverse_lazy


class ExploreDatagetterView(TemplateView):
    template_name = "explore_datagetter.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["errors"] = []

        context["getter_runs"] = db.GetterRun.objects.order_by("-datetime")

        try:

            if (
                "getter_run" in self.request.GET
                and "-1" not in self.request.GET["getter_run"]
            ):
                getter_run = context["getter_runs"].get(
                    pk=self.request.GET["getter_run"]
                )

                context["getter_run_selected"] = getter_run

                if (
                    "publisher" in self.request.GET
                    and "-1" not in self.request.GET["publisher"]
                ):
                    publisher = getter_run.publisher_set.get(
                        prefix=self.request.GET["publisher"]
                    )

                    context["publisher_selected"] = publisher
        except (db.GetterRun.DoesNotExist, db.Publisher.DoesNotExist) as e:
            context["errors"].append(str(e))
            pass

        return context


class ExploreLatestView(TemplateView):
    template_name = "explore_latest.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        context["errors"] = []

        context["latests"] = db.Latest.objects.all()

        try:

            if "latest" in self.request.GET and "-1" not in self.request.GET["latest"]:
                context["latest_selected"] = context["latests"].get(
                    pk=self.request.GET["latest"]
                )

                if (
                    "source" in self.request.GET
                    and "-1" not in self.request.GET["source"]
                ):
                    context["source_selected"] = context[
                        "latest_selected"
                    ].sourcefile_set.get(pk=self.request.GET["source"])

        except (db.Latest.DoesNotExist, db.SourceFile.DoesNotExist) as e:
            context["errors"].append(str(e))
            pass

        return context


class DashBoardView(TemplateView):
    template_name = "dash.html"

    @staticmethod
    def git_revision():
        return subprocess.check_output(
            ["git show --format=format:%h  --no-patch"], shell=True
        ).decode()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        context["last_datagetter_run"] = db.GetterRun.objects.order_by(
            "-datetime"
        ).first()
        context["total_grants"] = db.Grant.estimated_total()
        context["total_datagetter_runs"] = db.GetterRun.objects.count()

        # May not be generated yet
        try:
            context["latest_current"] = db.Latest.objects.get(series=db.Latest.CURRENT)
        except db.Latest.DoesNotExist:
            pass

        # May not be generated yet
        try:
            context["latest_previous"] = db.Latest.objects.get(
                series=db.Latest.PREVIOUS
            )
        except db.Latest.DoesNotExist:
            pass

        # May not be generated yet
        try:
            context["problem_sources"] = context[
                "last_datagetter_run"
            ].sourcefile_set.filter(
                Q(data_valid=False) | Q(downloads=False) | Q(acceptable_license=False)
            )
        except AttributeError:
            pass

        # Not critical if this fails e.g. git not installed
        try:
            context["git_rev"] = DashBoardView.git_revision()
        except Exception:
            pass

        return context


class LogView(TemplateView):
    template_name = "log.html"

    def read_log_file(self, log_file):
        """Returns log content and datetime of modified"""
        try:
            with open(log_file, "r") as f:
                return (
                    f.read(),
                    datetime.datetime.fromtimestamp(int(os.stat(log_file).st_mtime)),
                )

        except FileNotFoundError:
            return "Error unable to read log file", ""

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)

        log_name = kwargs.get("log_name")

        context["log_content"] = "No valid log selected"

        if not log_name:
            return context

        if log_name == "data_run":
            log_file = getattr(settings, "DATA_RUN_LOG", "")

            context["log_content"], context["date_modified"] = self.read_log_file(
                log_file
            )

        return context
