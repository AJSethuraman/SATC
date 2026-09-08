"""The provider seam: the only place a monitor's data source shows through.

TEMPLATE_CONTRACT section 6. One provider per source behind
``fetch_series(spec, secret=None) -> list[NormalizedRow]``, and two
implementations are mandatory: the live adapter and a deterministic offline
``DemoProvider`` that needs no key and no network. Every test uses the demo one,
which is why a monitor's whole verification bar runs on an aeroplane.

Everything source-specific lives behind this seam -- FDIC's one bulk BankFind
call, EDGAR's two-stage submissions-then-XBRL fetch, CFPB's page-scrape into a
CSV download, FRED's "."-means-missing coercion and rate-limit backoff. The
engine on this side of the seam sees only :class:`NormalizedRow`.

**Licensed (Class C) adapters are a module swap, and a live Class C call is
forbidden until a contract exists.** :class:`ClassCStubProvider` exists so the
seam is rehearsed rather than theoretical: it proves an unauthorised adapter is
refused by the gate rather than by the absence of code.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Sequence

from credit_suite.engine.config import Config, EntityRow


@dataclass
class NormalizedRow:
    """The contract's fixed row shape. Every adapter returns these and nothing else."""

    id: str
    period: str            # ISO date string
    value: Optional[float]
    geo_segment: str       # the entity key: "cert:628"
    source_class: str
    units: str = ""


@dataclass
class FieldSpec:
    """One expanded fetch/land unit: (entity slot, key) x raw field.

    The id scheme ``s{slot:02d}_{FIELD}`` mirrors the digest's units, and every
    anchor derives from ``(slot, field)`` alone -- never from which entity
    occupies the slot.
    """

    slot: int
    key: str
    fname: str
    id: str
    geo_segment: str
    units: str
    source_class: str = "A"


def make_field_spec(row: EntityRow, fname: str,
                    field_units: Dict[str, str]) -> FieldSpec:
    return FieldSpec(slot=row.slot, key=row.key, fname=fname,
                     id="s%02d_%s" % (row.slot, fname),
                     geo_segment=row.entity_key, units=field_units[fname])


class Provider:
    """The adapter interface.

    ``prime`` exists because the shape of an efficient fetch differs by source:
    FDIC answers one bulk request for the whole peer set, so priming once and
    slicing per unit is the difference between 1 request and 680. A source with
    no such call implements it as a no-op.
    """

    source_class = "A"
    vintage: Optional[str] = None      # data age as the source reports it

    def __init__(self) -> None:
        self.roster: Dict[str, dict] = {}
        #: {entity key: [source-specific merger records]}. Empty means the
        #: source was asked and reported none; a source that cannot answer
        #: leaves it None, which is a different fact and is reported as one.
        self.mergers: Optional[Dict[str, list]] = {}

    def prime(self, keys: Sequence[str], asof: date,
              names: Optional[Dict[str, str]] = None) -> None:  # pragma: no cover
        raise NotImplementedError

    def fetch_series(self, spec: FieldSpec,
                     secret: Optional[str] = None) -> List[NormalizedRow]:  # pragma: no cover
        raise NotImplementedError


class MissingSecret(SystemExit):
    """A licensed adapter was asked to run without its key.

    ``SystemExit`` on purpose: the runner contract maps it to exit code 3,
    which is a different thing from a run error (1) or a gate refusal (2).
    """


def resolve_secret(cfg: Config) -> Optional[str]:
    """Read the secret named by ``[SETTINGS] secret_env`` from the environment.

    The *name* of the variable is config; the value is never stored in a tab, a
    bundle or a workbook (contract section 3). A monitor whose source is keyless
    leaves ``secret_env`` empty and gets ``None``.
    """
    name = (cfg.setting("secret_env") or "").strip()
    if not name:
        return None
    return os.environ.get(name) or None


class ClassCStubProvider(Provider):
    """In-process OAuth client_credentials STUB for the licensed-feed seam.

    Makes NO live request, ever. Kept wired up rather than deleted so the Class
    C path is rehearsed: the gate must refuse this because its ``source_class``
    is not admitted, not because nobody wrote the adapter. Delete it and the
    gate can only be proven by the absence of code, and an untested gate is the
    one that opens.

    ``secret_env`` stays wired per contract for a hypothetical authenticated v2.
    The secret itself arrives per call, matching the ``fetch_series(spec,
    secret)`` seam, so nothing licensed is ever held on the instance.
    """

    source_class = "C"

    def __init__(self, secret_env: str) -> None:
        super().__init__()
        self.secret_env = secret_env
        self._token: Optional[str] = None

    def _authenticate(self, secret: Optional[str]) -> str:
        if not secret:
            raise PermissionError("HTTP 401: missing/invalid access token "
                                  "(client_credentials not supplied).")
        self._token = "stub-token"
        return self._token

    def prime(self, keys, asof, names=None) -> None:
        return None

    def fetch_series(self, spec: FieldSpec,
                     secret: Optional[str] = None) -> List[NormalizedRow]:
        self._authenticate(secret)
        # A schema-shaped, VALUELESS row: proves the seam contract without
        # fabricating licensed data.
        return [NormalizedRow(id=spec.id, period="1900-01-01", value=None,
                              geo_segment=spec.geo_segment, source_class="C",
                              units=spec.units)]
