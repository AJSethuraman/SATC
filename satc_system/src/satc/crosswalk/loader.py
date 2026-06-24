"""Dated, versioned tax-law reference layer (the "crosswalk").

Keyed by **tax_year x jurisdiction** (Federal = ``US``, plus OH/MI/MA first). A
workpaper for (tax year Y, jurisdiction J) pulls the parameters *in force* for
(Y, J). Every parameter carries a citation and a status:

  * ``in_force``           — published, verified value
  * ``scheduled_reversion``— a value that changes under a scheduled sunset
                             (the TCJA-after-2025 versioning test fixture)
  * ``pending``            — no value published yet; recorded as a GAP, never guessed

Configs live in ``configs/crosswalk/<JURIS>/<YEAR>.yaml``. This loader reads them,
resolves (Y, J), and exposes typed parameter access. Where a future value is not
published, the loader returns a ``pending`` :class:`Param` rather than inventing a
number — satisfying the build standard "never guess a tax-law value".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from satc.config import CONFIG_ROOT
from satc.ids import normalize_jurisdiction

ParamStatus = str  # "in_force" | "scheduled_reversion" | "pending"

# Frozen-aware: CONFIG_ROOT resolves to sys._MEIPASS/configs inside a PyInstaller
# bundle (and to satc_system/configs in a dev/test install), so the crosswalk is
# found in the packaged .exe instead of pointing outside the bundle.
_DEFAULT_CONFIG_DIR = CONFIG_ROOT / "crosswalk"


class CrosswalkError(Exception):
    """Raised when a crosswalk config is missing or malformed."""


@dataclass(slots=True)
class Param:
    """One resolved tax-law parameter with full provenance."""

    name: str
    tax_year: int
    jurisdiction: str
    value: Any = None
    unit: str = ""
    citation: str = ""
    source_label: str = ""
    status: ParamStatus = "in_force"
    pending_reason: str = ""

    @property
    def is_pending(self) -> bool:
        return self.status == "pending" or self.value is None

    @property
    def is_gap(self) -> bool:
        """A gap is any parameter not firmly in force (pending or sunset-affected)."""
        return self.status != "in_force"


@dataclass(slots=True)
class Crosswalk:
    """All parameters in force for one (tax_year, jurisdiction)."""

    tax_year: int
    jurisdiction: str
    source_label: str = ""
    retrieved: str = ""
    status: str = "in_force"
    notes: str = ""
    params: dict[str, Param] = field(default_factory=dict)

    def param(self, name: str) -> Param:
        """Return the parameter, or a ``pending`` gap if it is not published."""
        existing = self.params.get(name)
        if existing is not None:
            return existing
        return Param(
            name=name,
            tax_year=self.tax_year,
            jurisdiction=self.jurisdiction,
            value=None,
            status="pending",
            pending_reason=(
                f"No value for '{name}' published for {self.jurisdiction} {self.tax_year}; "
                "record pending IRS/state guidance."
            ),
        )

    def value(self, name: str, default: Any = None) -> Any:
        p = self.params.get(name)
        return default if p is None or p.is_pending else p.value

    def gaps(self) -> list[Param]:
        """All parameters that are pending or affected by a scheduled reversion."""
        return [p for p in self.params.values() if p.is_gap]


def _coerce_param(name: str, raw: Any, tax_year: int, jurisdiction: str,
                  default_source: str) -> Param:
    if not isinstance(raw, dict):
        # Shorthand: a bare scalar is treated as an in-force value with no citation.
        return Param(name=name, tax_year=tax_year, jurisdiction=jurisdiction, value=raw)
    return Param(
        name=name,
        tax_year=tax_year,
        jurisdiction=jurisdiction,
        value=raw.get("value"),
        unit=str(raw.get("unit", "")),
        citation=str(raw.get("citation", "")),
        source_label=str(raw.get("source_label", default_source)),
        status=str(raw.get("status", "in_force")),
        pending_reason=str(raw.get("pending_reason", "")),
    )


def load_crosswalk_file(path: str | Path) -> Crosswalk:
    """Load and validate one crosswalk YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        raise CrosswalkError(f"Crosswalk file not found: {config_path}")
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise CrosswalkError(f"Invalid YAML in {config_path}: {exc}") from exc

    meta = raw.get("meta", {})
    if not isinstance(meta, dict):
        raise CrosswalkError(f"meta must be a mapping in {config_path}")
    try:
        tax_year = int(meta["tax_year"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CrosswalkError(f"meta.tax_year (int) is required in {config_path}") from exc
    jurisdiction = normalize_jurisdiction(str(meta.get("jurisdiction", "US")))
    source_label = str(meta.get("source_label", ""))

    raw_params = raw.get("parameters", {})
    if not isinstance(raw_params, dict):
        raise CrosswalkError(f"parameters must be a mapping in {config_path}")

    params: dict[str, Param] = {}
    for name, body in raw_params.items():
        params[str(name)] = _coerce_param(str(name), body, tax_year, jurisdiction, source_label)

    return Crosswalk(
        tax_year=tax_year,
        jurisdiction=jurisdiction,
        source_label=source_label,
        retrieved=str(meta.get("retrieved", "")),
        status=str(meta.get("status", "in_force")),
        notes=str(meta.get("notes", "")),
        params=params,
    )


class CrosswalkLibrary:
    """All crosswalk files, indexed by (tax_year, jurisdiction)."""

    def __init__(self, config_dir: str | Path | None = None) -> None:
        self.config_dir = Path(config_dir) if config_dir else _DEFAULT_CONFIG_DIR
        self._by_key: dict[tuple[int, str], Crosswalk] = {}
        self._loaded = False

    def load(self) -> CrosswalkLibrary:
        if not self.config_dir.exists():
            raise CrosswalkError(f"Crosswalk config dir not found: {self.config_dir}")
        for path in sorted(self.config_dir.rglob("*.yaml")):
            xwalk = load_crosswalk_file(path)
            self._by_key[(xwalk.tax_year, xwalk.jurisdiction)] = xwalk
        self._loaded = True
        return self

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def available(self) -> list[tuple[int, str]]:
        self._ensure_loaded()
        return sorted(self._by_key.keys())

    def resolve(self, tax_year: int, jurisdiction: str) -> Crosswalk:
        """Return the crosswalk for (Y, J). Raises if no config exists."""
        self._ensure_loaded()
        key = (int(tax_year), normalize_jurisdiction(jurisdiction))
        xwalk = self._by_key.get(key)
        if xwalk is None:
            raise CrosswalkError(
                f"No tax-law crosswalk published for {key[1]} {key[0]}. "
                "Add configs/crosswalk/<JURIS>/<YEAR>.yaml or record a pending gap."
            )
        return xwalk

    def resolve_or_none(self, tax_year: int, jurisdiction: str) -> Crosswalk | None:
        try:
            return self.resolve(tax_year, jurisdiction)
        except CrosswalkError:
            return None
