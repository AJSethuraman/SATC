"""Domain models for the SATC system.

Two physically separated layers:
  * :mod:`satc.models.identity` — the external identity vault (SENSITIVE; never
    serialized into the workbook).
  * :mod:`satc.models.mart` — the de-identified working data mart (the workbook
    now; a SQL database later).

Plus the supporting schemas: :mod:`satc.models.provenance`,
:mod:`satc.models.staging`, and :mod:`satc.models.review`.
"""

from __future__ import annotations

from satc.models.identity import (
    IdentityRecord,
    PublicClient,
    VaultAddress,
    VaultContact,
)
from satc.models.mart import (
    Carryforward,
    DataMart,
    EngagementRecord,
    EstimatePayment,
    LineItem,
    OwnerBasis,
    ReturnRecord,
)
from satc.models.provenance import Provenance, SourceRef
from satc.models.review import Checklist, ReviewItem, completion_pct, open_exceptions
from satc.models.staging import StagedDocument, StagedField

__all__ = [
    "IdentityRecord",
    "PublicClient",
    "VaultAddress",
    "VaultContact",
    "Carryforward",
    "DataMart",
    "EngagementRecord",
    "EstimatePayment",
    "LineItem",
    "OwnerBasis",
    "ReturnRecord",
    "Provenance",
    "SourceRef",
    "Checklist",
    "ReviewItem",
    "completion_pct",
    "open_exceptions",
    "StagedDocument",
    "StagedField",
]
