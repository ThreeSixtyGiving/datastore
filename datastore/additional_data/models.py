import re

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db.models import JSONField
from django.db import models


class OrgInfoCache(models.Model):
    # List generated from https://github.com/drkane/find-that-charity-scrapers/#spiders

    CASC = "casc"
    CCEW = "ccew"
    CCNI = "ccni"
    OSCR = "oscr"
    COMPANIES = "companies"
    MUTUALS = "mutuals"
    GOR = "gor"
    GRID = "grid"
    HESA = "hesa"
    LAE = "lae"
    LANI = "lani"
    LAS = "las"
    PLA = "pla"
    NHSODS = "nhsods"
    RSL = "rsl"
    SCHOOLS_GIAS = "schools_gias"
    SCHOOLS_NI = "schools_ni"
    SCHOOLS_SCOTLAND = "schools_scotland"
    SCHOOLS_WALES = "schools_wales"

    ORG_TYPE = [
        (CASC, "Community Amateur Sports Clubs regulated by HMRC"),
        (CCEW, "Registered charities in England and Wales"),
        (CCNI, "Registered charities in Northern Ireland"),
        (OSCR, "Registered charities in Scotland"),
        (
            COMPANIES,
            "Companies registered with Companies House (the scraper only imports non-profit company types)",
        ),
        (MUTUALS, "Mutual societies registered with the Financial Conduct Authority"),
        (GOR, "A register of government organisations"),
        (
            GRID,
            "Entries from the Global Research Identifier Database - only those that are based in the UK and are not a registered company are included.",
        ),
        (HESA, "Organisations covered by the Higher Education Statistics Agency."),
        (LAE, "Register of local authorities in England"),
        (LANI, "Register of local authorities in Northern Ireland"),
        (LAS, "Register of local authorities in Scotland"),
        (PLA, "Register of principal local authorities in Wales"),
        (NHSODS, "NHS organisations"),
        (RSL, "Registered social landlords"),
        (SCHOOLS_GIAS, "Schools in England (also includes Universities)"),
        (SCHOOLS_NI, "Schools in Northern Ireland"),
        (SCHOOLS_SCOTLAND, "Schools in Scotland"),
        (SCHOOLS_WALES, "Schools in Wales"),
    ]

    # These fields are all allowed to be empty on create method and then updated
    # automatically when save() is called.
    # Convenience fields
    org_id = models.CharField(max_length=200, unique=True)

    # organisations can have multiple org_ids for example if they're comprised of a charity and
    # a limited company.
    org_ids = ArrayField(
        models.CharField(max_length=100, blank=True),
        blank=True,
        null=True,
        db_index=True,
    )

    # Future convert to models.TextChoices
    org_type = models.CharField(max_length=20, choices=ORG_TYPE)

    # When this data was loaded
    fetched = models.DateTimeField(auto_now=True)

    data = JSONField()

    # USE org_id as the main identifier
    # we can attempt to construct an org-id
    # import all the sources from ftc.ftc

    def __str__(self):
        if "name" in self.data:
            return "%s - %s" % (self.data["name"], self.org_id)
        else:
            return "%s" % self.org_id

    class Meta:
        indexes = [GinIndex(fields=["org_ids"])]


class NSPL(models.Model):
    # Postcode without whitespaces and uppercase.
    postcode = models.CharField(max_length=7, db_index=True)
    data = JSONField()

    def __str__(self):
        return f"NSPL {self.postcode}"


class GeoCodeName(models.Model):
    code = models.CharField(max_length=9, db_index=True)
    data = JSONField()


class GeoLookup(models.Model):

    LSOA = "lsoa"
    MSOA = "msoa"
    LA = "la"
    WARD = "ward"

    AREA_TYPE = [
        (LSOA, "Lower Super Output Area"),
        (MSOA, "Middle Super Output Area"),
        (LA, "Local Authority"),
        (WARD, "Ward"),
    ]

    areacode = models.CharField(max_length=200, unique=True, db_index=True)
    areatype = models.CharField(max_length=20, choices=AREA_TYPE, db_index=True)
    data = JSONField()


class TSGOrgType(models.Model):
    """ThreeSixtyGiving Org Type mappings"""

    def validate_regex(value):
        """Check that the input regex is valid"""
        try:
            re.compile(value)
        except re.error as e:
            raise ValidationError(e.msg)

    regex = models.CharField(
        max_length=200,
        help_text="Regex pattern to match the funder org-id",
        validators=[validate_regex],
    )
    priority = models.IntegerField(
        unique=True,
        help_text="Which pattern will take precedence (Higher number = higher priority)",
    )
    tsg_org_type = models.CharField(
        max_length=200,
        unique=True,
        verbose_name="ThreeSixtyGiving Org Type",
        help_text="Value that will be added to the additional data",
    )

    class Meta:
        verbose_name = "ThreeSixtyGiving Org Type"
        ordering = ["priority"]

    def __str__(self):
        return self.tsg_org_type


class CodelistCode(models.Model):
    """360Giving standard code lists codes and titles"""

    list_name = models.CharField(
        max_length=200, help_text="The name of the codelist the code belongs to"
    )
    code = models.CharField(max_length=200, help_text="The code")
    title = models.CharField(max_length=200, help_text="The title of the code")
    description = models.TextField(help_text="The long description of the code")

    class Meta:
        unique_together = ("list_name", "code")
