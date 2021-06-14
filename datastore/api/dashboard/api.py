from django.http.response import JsonResponse
from django.views import View
from django.db.models import Sum, Q
from django.db.models.expressions import RawSQL
from django.core.cache import cache

import django_filters.rest_framework
from rest_framework import filters, generics

import db.models as db
from api.dashboard import serializers
from api.dashboard.permissions import ReadOnly
from data_quality import quality_data

import datetime


class PublisherFilters(django_filters.rest_framework.FilterSet):
    quality__hasGrantProgrammeTitle = django_filters.CharFilter(
        method="hasGrantProgrammeTitle_filter", label="hasGrantProgrammeTitle"
    )

    def hasGrantProgrammeTitle_filter(self, queryset, name, value):
        return queryset.filter(quality__hasGrantProgrammeTitle__iexact=value)

    class Meta:
        model = db.Publisher
        fields = ["quality__hasGrantProgrammeTitle"]


class Publishers(generics.ListAPIView):
    serializer_class = serializers.PublishersSerializer
    permission_classes = [ReadOnly]

    filter_backends = (
        filters.SearchFilter,
        django_filters.rest_framework.DjangoFilterBackend,
        filters.OrderingFilter,
    )

    filterset_class = PublisherFilters
    search_fields = ("^data__name",)
    ordering_fields = ["data__name", "aggregate__publishedThisYear"]

    def get_queryset(self):
        return db.Publisher.objects.filter(getter_run=db.GetterRun.objects.last())


class Sources(generics.ListAPIView):
    serializer_class = serializers.SourcesSerializer
    #  pagination_class = CurrentLatestGrantsPaginator

    def get_queryset(self):
        return db.SourceFile.objects.filter(getter_run=db.GetterRun.objects.last())


class Overview(View):
    @staticmethod
    def stats(source_file_set, mode, total_grants, latest):
        total_publishers = source_file_set.distinct("data__publisher__prefix").count()

        # The quality metrics we have are based on "Not" having something and we want to know if they DO have something
        # later we process the counts and filters to do total_publishers - not xyz / total_publishers
        # to give the total publishers that do have it.

        has_no_location_codes = source_file_set.filter(
            Q(quality__BeneficiaryLocationCountryCodeNotPresent__count__gte=1)
            | Q(quality__BeneficiaryLocationGeoCodeNotPresent__count__gte=1)
        )

        # TODO There is a more clever way to pass the filter field names in using **kwargs
        has_no_location_names = source_file_set.filter(
            quality__BeneficiaryLocationNameNotPresent__count__gte=1
        )

        has_no_recipient_org_location = source_file_set.filter(
            quality__IncompleteRecipientOrg__count__gte=1
        )
        has_no_grant_duration = source_file_set.filter(
            quality__PlannedDurationNotPresent__count__gte=1
        )
        has_no_grant_programme_title = source_file_set.filter(
            quality__GrantProgrammeTitleNotPresent__count__gte=1
        )
        has_no_grant_classification = source_file_set.filter(
            quality__ClassificationNotPresent__count__gte=1
        )

        json_files = source_file_set.exclude(
            data__datagetter_metadata__file_type__contains="json"
        )
        csv_files = source_file_set.exclude(
            data__datagetter_metadata__file_type__contains="csv"
        )
        xlsx_files = source_file_set.exclude(
            data__datagetter_metadata__file_type__contains="xlsx"
        )
        ods_files = source_file_set.exclude(
            data__datagetter_metadata__file_type__contains="ods"
        )

        this_month = datetime.datetime.now().strftime("%Y-%m")
        this_year = datetime.datetime.now().strftime("%Y")

        published_data_this_year = source_file_set.exclude(
            data__modified__startswith=this_year
        )
        published_data_this_month = source_file_set.exclude(
            data__modified__startswith=this_month
        )

        ret = {
            "hasBeneficiaryLocationCodes": has_no_location_codes,
            "hasRecipientOrgLocations": has_no_recipient_org_location,
            "hasBeneficiaryLocationName": has_no_location_names,
            "hasGrantDuration": has_no_grant_duration,
            "hasGrantProgrammeTitle": has_no_grant_programme_title,
            "hasGrantClassification": has_no_grant_classification,
        }

        # We look at the distinct publishers so that if any source file from a publisher
        # contains a quality problem in any of their source files then that publisher is counted
        # as not having that value
        if mode == "publishers":
            ret.update(
                {
                    "publishedThisYear": published_data_this_year,
                    "publishedThisMonth": published_data_this_month,
                    "jsonFiles": json_files,
                    "csvFiles": csv_files,
                    "xlsxFiles": xlsx_files,
                    "odsFiles": ods_files,
                }
            )

            for metric, query in ret.items():
                ret[metric] = (
                    total_publishers - query.distinct("data__publisher__prefix").count()
                ) / total_publishers

            # Awarded in these years
            award_years = {}
            this_year_int = int(this_year)

            for i in range(0, 10):
                year_str = str(this_year_int - i)
                award_years[year_str] = (
                    source_file_set.filter(
                        aggregate__min_award_date__startswith=year_str
                    )
                    .distinct("data__publisher__prefix")
                    .count()
                    / total_publishers
                )

            ret.update({"minAwardYears": award_years})

        elif mode == "grants":
            # We want to SUM the counts in the metric to know how many grants had quality issues
            count_field = RawSQL(
                "((quality->'BeneficiaryLocationCountryCodeNotPresent'->>'count')::numeric)",
                (),
            )
            count_field_two = RawSQL(
                "((quality->'BeneficiaryLocationGeoCodeNotPresent'->>'count')::numeric)",
                (),
            )
            all_code_counts = (
                has_no_location_codes.annotate(count=count_field)
                .annotate(count_two=count_field_two)
                .aggregate(Sum("count"), Sum("count_two"))
            )
            ret["hasBeneficiaryLocationCodes"] = (
                all_code_counts["count__sum"] + all_code_counts["count_two__sum"]
            ) / (total_grants * 2)

            # TODO more clever way of doing this with a mapping of test names then loop over them
            count_field = RawSQL(
                "((quality->'IncompleteRecipientOrg'->>'count')::numeric)", ()
            )
            ret["hasRecipientOrgLocations"] = has_no_recipient_org_location.annotate(
                count=count_field
            )

            count_field = RawSQL(
                "((quality->'BeneficiaryLocationNameNotPresent'->>'count')::numeric)",
                (),
            )
            ret["hasBeneficiaryLocationName"] = has_no_location_names.annotate(
                count=count_field
            )

            count_field = RawSQL(
                "((quality->'PlannedDurationNotPresent'->>'count')::numeric)", ()
            )
            ret["hasGrantDuration"] = has_no_grant_duration.annotate(count=count_field)

            count_field = RawSQL(
                "((quality->'GrantProgrammeTitleNotPresent'->>'count')::numeric)", ()
            )
            ret["hasGrantProgrammeTitle"] = has_no_grant_programme_title.annotate(
                count=count_field
            )

            count_field = RawSQL(
                "((quality->'ClassificationNotPresent'->>'count')::numeric)", ()
            )
            ret["hasGrantClassification"] = has_no_grant_classification.annotate(
                count=count_field
            )

            for metric, query in ret.items():
                # Skip this one has it is handled already due to being a special case
                if metric == "hasBeneficiaryLocationCodes":
                    continue

                ret[metric] = (
                    total_grants - query.aggregate(Sum("count"))["count__sum"]
                ) / total_grants

            # Awarded in these years
            award_years = {}
            this_year_int = int(this_year)

            from django.db.models import Count

            query_args = {}

            grant_set = latest.grant_set.all()
            sums = []

            # Build query parameters
            for i in range(0, 10):
                # Alternatively we could do a query for each year need to test if this is faster:
                # award_years[year_str] = latest.grant_set.filter(data__awardDate__startswith=year_str).count()
                year_str = str(this_year_int - i)
                query_args[year_str] = Count(
                    "data", filter=Q(data__awardDate__startswith=year_str)
                )
                sums.append(Sum(year_str))

            # Format the data
            for year_sum, total_year_grants in (
                grant_set.annotate(**query_args).aggregate(*sums).items()
            ):
                award_years[year_sum.replace("__sum", "")] = total_year_grants

            ret.update({"grantsByYear": award_years})

        else:
            return {}

        return ret

    def get(self, *args, **kwargs):
        # If we have a cache of this uri then return that.
        # All caches are cleared if the dataload happens
        full_request_uri = self.request.build_absolute_uri()
        ret = cache.get(full_request_uri)

        if ret:
            return JsonResponse(ret, safe=False)

        mode = "overview_%s" % self.request.GET.get("mode")

        latest = db.Latest.objects.get(series=db.Latest.CURRENT)
        source_file_set = latest.sourcefile_set.all()

        ret = quality_data.aggregated_stats(source_file_set, mode)
        cache.set(full_request_uri, ret)

        return JsonResponse(ret, safe=False)
