from django.contrib.postgres.fields import ArrayField, JSONField
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
        models.CharField(max_length=100, blank=True), blank=True, null=True
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
