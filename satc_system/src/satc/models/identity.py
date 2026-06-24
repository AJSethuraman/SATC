"""IDENTITY VAULT schema (external / access-controlled).

THIS DATA NEVER LIVES IN THE WORKBOOK. The identity vault maps an opaque
``client_id`` to the sensitive standing data (legal name, full SSN/EIN, addresses,
contacts). In production this is the firm's Teams/SharePoint + an access-controlled
store; here it is modeled so the seam is explicit and testable with synthetic data.

The working data mart references clients ONLY by ``client_id`` and stores only the
non-sensitive public projection produced by :meth:`IdentityRecord.to_public`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from satc.masking import last4, mask_ein, mask_ssn

EntityType = Literal["INDIVIDUAL", "SCORP", "PARTNERSHIP", "CCORP"]

# Which masking applies and which return type an entity files by default.
_ENTITY_RETURN: dict[str, str] = {
    "INDIVIDUAL": "1040",
    "SCORP": "1120S",
    "PARTNERSHIP": "1065",
    "CCORP": "1120",
}


@dataclass(slots=True)
class VaultAddress:
    line1: str
    city: str
    state: str
    zip: str
    line2: str = ""


@dataclass(slots=True)
class VaultContact:
    name: str
    email: str = ""
    phone: str = ""
    role: str = ""           # e.g. "Taxpayer", "Spouse", "Officer", "Partner", "POC"


@dataclass(slots=True)
class PublicClient:
    """The de-identified projection that is safe to store in the data mart."""

    client_id: str
    entity_type: EntityType
    display_label: str       # e.g. "Client SATC-001000 (INDIVIDUAL)" — NOT a real name
    tin_last4: str           # last 4 of SSN/EIN only
    tin_masked: str          # ***-**-1234 / **-***1234
    default_return_type: str
    home_state: str = ""     # USPS code (non-sensitive; drives default state return)
    filing_status: str = ""  # last-known filing status (non-PII tax attribute; "" if unknown)


@dataclass(slots=True)
class IdentityRecord:
    """A full vault record. Sensitive — never serialized into the workbook."""

    client_id: str
    entity_type: EntityType
    legal_name: str          # SENSITIVE
    tin: str                 # SENSITIVE full SSN/EIN
    addresses: list[VaultAddress] = field(default_factory=list)
    contacts: list[VaultContact] = field(default_factory=list)

    def default_return_type(self) -> str:
        return _ENTITY_RETURN[self.entity_type]

    def home_state(self) -> str:
        return self.addresses[0].state.strip().upper() if self.addresses else ""

    def to_public(self) -> PublicClient:
        """Project to the non-sensitive record stored in the working data mart."""
        masked = mask_ssn(self.tin) if self.entity_type == "INDIVIDUAL" else mask_ein(self.tin)
        return PublicClient(
            client_id=self.client_id,
            entity_type=self.entity_type,
            display_label=f"Client {self.client_id} ({self.entity_type})",
            tin_last4=last4(self.tin),
            tin_masked=masked,
            default_return_type=self.default_return_type(),
            home_state=self.home_state(),
        )
