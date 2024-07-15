from dataclasses import dataclass
from typing import Optional, List

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models.query import QuerySet, Q

import db.models as db


@dataclass
class OrganisationRef:
    """
    Represents a reference to an Organisation, i.e. an object with an org_id.
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
    linked_orgs: List[OrganisationRef]

    def __post_init__(self):
        if self.org_id == "":
            raise ValueError("org_id cannot be empty string")

    # Add Model.DoesNotExist and MultipleObjectsReturned exceptions to mimic Django models
    class DoesNotExist(ObjectDoesNotExist):
        pass

    class MultipleObjectsReturned(MultipleObjectsReturned):
        pass

    @staticmethod
    def exists(
        org_id: str,
        funder_queryset: Optional[QuerySet[db.Funder]] = None,
        recipient_queryset: Optional[QuerySet[db.Recipient]] = None,
        publisher_queryset: Optional[QuerySet[db.Publisher]] = None,
    ) -> bool:
        """
        Checks if an Organisation with this Org ID exists, returns True if exists, False if not.
        """
        if funder_queryset is None:
            funder_queryset = db.Funder.objects.all()

        if recipient_queryset is None:
            recipient_queryset = db.Recipient.objects.all()

        if publisher_queryset is None:
            # Empty order_by to cancel default sort
            publisher_queryset = db.Publisher.objects.order_by().filter(
                getter_run__in=db.GetterRun.objects.in_use()
            )

        id_query = Q(org_id=org_id) | Q(non_primary_org_ids__contains=[org_id])

        if funder_queryset.filter(id_query).exists():
            return True

        if recipient_queryset.filter(id_query).exists():
            return True

        if publisher_queryset.order_by().filter(org_id=org_id).exists():
            return True

        return False

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
        if funder_queryset is None:
            funder_queryset = db.Funder.objects.all()

        if recipient_queryset is None:
            recipient_queryset = db.Recipient.objects.all()

        if publisher_queryset is None:
            # Empty order_by to cancel default sort
            publisher_queryset = db.Publisher.objects.order_by().filter(
                getter_run__in=db.GetterRun.objects.in_use()
            )

        name = None
        primary_org_id = org_id
        linked_org_ids = set()

        id_query = Q(org_id=org_id) | Q(non_primary_org_ids__contains=[org_id])

        # Note that we are searching by both org_id (Primary Org ID) and Non-primary Org IDs
        # If the user searches by a non-primary ID, we will instead show info about the Primary Org.
        # (Recipient and Funder objects are only created for primary IDs)

        # is org a Recipient?
        try:
            recipients = recipient_queryset.filter(id_query)
            # For now, replicate GrantNav behaviour by taking the first filter result as Primary
            # https://github.com/ThreeSixtyGiving/grantnav/blob/ee696779d110ab491daa6694f5344c07dbbf98d2/grantnav/frontend/views.py#L1196
            recipient = recipients[0]
            name = recipient.name
            primary_org_id = recipient.org_id

            for rt in recipients:
                linked_org_ids.add(rt.org_id)
                linked_org_ids.update(rt.non_primary_org_ids)

        except IndexError:
            recipient = None

        # is org a Funder?
        try:
            funders = funder_queryset.filter(id_query)
            # For now, replicate GrantNav behaviour by taking the first filter result as Primary
            # https://github.com/ThreeSixtyGiving/grantnav/blob/ee696779d110ab491daa6694f5344c07dbbf98d2/grantnav/frontend/views.py#L1205
            funder = funders[0]
            name = funder.name
            primary_org_id = funder.org_id

            for fr in funders:
                linked_org_ids.add(fr.org_id)
                linked_org_ids.update(fr.non_primary_org_ids)

        except IndexError:
            funder = None

        # is org a Publisher?
        try:
            publisher = publisher_queryset.filter(org_id=org_id).order_by(
                "-getter_run__datetime"
            )[0]
            name = publisher.name
            # Publishers take precedence over Funders / Recipients when it comes to primary vs non-primary ID priority
            primary_org_id = publisher.org_id
        except IndexError:
            publisher = None

        if funder is None and recipient is None and publisher is None:
            raise Organisation.DoesNotExist

        # Don't include the primary org itsself in linked_orgs
        linked_org_ids.discard(primary_org_id)

        return Organisation(
            org_id=primary_org_id,
            name=name,
            funder=funder,
            recipient=recipient,
            publisher=publisher,
            linked_orgs=list(OrganisationRef(org_id=oid) for oid in linked_org_ids),
        )


@dataclass
class GrantLicense:
    url: str
    name: str
