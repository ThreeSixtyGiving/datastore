from typing import Optional
from dataclasses import dataclass

import db.models as db


@dataclass
class Organisation:
    """
    Represents an Organisation, including org id and the roles it takes.
    """

    org_id: str
    funder: Optional[db.Funder]
    recipient: Optional[db.Recipient]
    publisher: Optional[db.Publisher]
