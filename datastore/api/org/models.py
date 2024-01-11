from typing import Optional, List
from dataclasses import dataclass
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models.query import QuerySet

import db.models as db


@dataclass
class OrganisationRef:
    """
    Represents a link/reference to an Organisation.
    """

    org_id: str

    def __post_init__(self):
        if self.org_id == "":
            raise ValueError("org_id cannot be empty string")


@dataclass
class Organisation:
    """
    Represents an Organisation, including org id and the roles it takes.
    """

    org_id: str
    name: str
    funder: Optional[db.Funder]
    recipient: Optional[db.Recipient]
    publisher: Optional[db.Publisher]

    def __post_init__(self):
        if self.org_id == "":
            raise ValueError("org_id cannot be empty string")

    # Add Model.DoesNotExist and MultipleObjectsReturned exceptions to mimic Django models
    class DoesNotExist(ObjectDoesNotExist):
        pass

    class MultipleObjectsReturned(MultipleObjectsReturned):
        pass

    @staticmethod
    def get(
        org_id: str,
        funder_queryset: Optional[QuerySet[db.Funder]] = None,
        recipient_queryset: Optional[QuerySet[db.Recipient]] = None,
        publisher_queryset: Optional[QuerySet[db.Publisher]] = None,
    ) -> "Organisation":
        """
        Retrieve a single Organisation by org_id.
        This combines queries of the Funder, Recipient and Publisher sub-models.

        By default will query the current set of each sub-model, but each queryset can be overridden by passing the *_queryset kwargs.

        Returns an instance of Organisation if found, otherwise raises Organisation.DoesNotExist if not found.
        """
        if not funder_queryset:
            funder_queryset = db.Funder.objects.all()

        if not recipient_queryset:
            recipient_queryset = db.Recipient.objects.all()

        if not publisher_queryset:
            publisher_queryset = db.Publisher.objects.filter(
                getter_run__in=db.GetterRun.objects.in_use()
            )

        name = None

        # is org a Recipient?
        try:
            recipient = recipient_queryset.get(org_id=org_id)
            name = recipient.name

        except db.Recipient.DoesNotExist:
            recipient = None

        # is org a Funder?
        try:
            funder = funder_queryset.get(org_id=org_id)
            name = funder.name

        except db.Funder.DoesNotExist:
            funder = None

        # is org a Publisher?
        try:
            publisher = publisher_queryset.filter(org_id=org_id).order_by(
                "-getter_run__datetime"
            )[0]
            name = publisher.name
        except IndexError:
            publisher = None

        if funder is None and recipient is None and publisher is None:
            raise Organisation.DoesNotExist

        return Organisation(
            org_id=org_id,
            name=name,
            funder=funder,
            recipient=recipient,
            publisher=publisher,
        )
