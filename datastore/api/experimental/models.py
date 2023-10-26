from typing import Optional
from dataclasses import dataclass

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
    funder: Optional[db.Funder]
    recipient: Optional[db.Recipient]
    publisher: Optional[db.Publisher]

    def __post_init__(self):
        if self.org_id == "":
            raise ValueError("org_id cannot be empty string")
