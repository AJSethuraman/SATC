"""The service catalogue and the rate plans — what work is worth, and what a
particular client pays for it.

Those are two separate facts and the design keeps them separate on purpose. A
service has a STANDARD RATE, which is what the work is worth. A client has a
RATE PLAN, which is what they can reasonably pay. An invoice shows both, so
somebody on a reduced rate can see what they were given rather than just
receiving a smaller number they cannot interpret.

The one thing that cannot be expressed here, structurally: a fee that depends on
the refund or on a tax position. Circular 230 §10.27 prohibits contingent fees
for return preparation, and a plan here is a percentage off a standard rate with
no access to the outcome of the return. The loader also refuses a service that
tries to describe itself that way, because the next person to add one will not
have read this docstring.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Literal

import yaml

from satc.config import CONFIG_ROOT, ConfigError

Unit = Literal["fixed", "per_form", "per_hour"]

_UNITS = {"fixed", "per_form", "per_hour"}

# Phrases that describe a contingent fee. A service matching one of these is
# refused at load rather than at invoice time — by then it is already policy.
_CONTINGENT = ("% of refund", "percent of refund", "contingent", "of the refund",
               "share of refund", "portion of the refund")


def billing_dir(config_root: Path | None = None) -> Path:
    return (config_root or CONFIG_ROOT) / "billing"


@dataclass(frozen=True, slots=True)
class Service:
    """One billable thing, and what it is worth at full rate."""

    code: str
    name: str
    client_label: str
    category: str
    unit: Unit
    standard_rate: Decimal
    description: str = ""

    @property
    def label_for_client(self) -> str:
        """What appears on the invoice — how a person reads it, not how it files."""
        return self.client_label or self.name

    @property
    def is_free(self) -> bool:
        return self.standard_rate == 0

    def amount_for(self, quantity: Decimal) -> Decimal:
        """Standard value of this service at a given quantity."""
        return _money(self.standard_rate * quantity)


@dataclass(frozen=True, slots=True)
class RatePlan:
    """What a client pays relative to standard, and why."""

    key: str
    name: str
    discount_pct: Decimal
    requires_basis: bool = False
    client_label: str = ""
    note: str = ""

    @property
    def is_full_rate(self) -> bool:
        return self.discount_pct == 0

    @property
    def is_free(self) -> bool:
        return self.discount_pct == 100

    def discount_on(self, standard: Decimal) -> Decimal:
        return _money(standard * self.discount_pct / Decimal(100))

    def charge_on(self, standard: Decimal) -> Decimal:
        return _money(standard - self.discount_on(standard))


def _money(value: Decimal) -> Decimal:
    """Round to cents, half-up. Money is never a float in this codebase."""
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _load(path: Path) -> dict:
    if not path.exists():
        raise ConfigError(f"Billing config not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ConfigError(f"Billing config must be a mapping: {path}")
    return data


def load_services(config_root: Path | None = None) -> dict[str, Service]:
    """Read ``configs/billing/services.yaml``."""
    data = _load(billing_dir(config_root) / "services.yaml")
    out: dict[str, Service] = {}
    for entry in data.get("services") or []:
        code = str(entry.get("code", "")).strip()
        if not code:
            raise ConfigError(f"A service has no code: {entry!r}")
        unit = str(entry.get("unit", "fixed")).strip()
        if unit not in _UNITS:
            raise ConfigError(f"Service {code!r} has an unknown unit: {unit!r}")

        blob = " ".join(str(entry.get(k, "")) for k in
                        ("name", "client_label", "description")).lower()
        if any(phrase in blob for phrase in _CONTINGENT):
            raise ConfigError(
                f"Service {code!r} describes a CONTINGENT FEE. Circular 230 §10.27 "
                f"prohibits contingent fees for return preparation. Price this as a "
                f"fixed, per-form or hourly amount instead.")

        try:
            rate = Decimal(str(entry.get("standard_rate", 0)))
        except Exception:  # noqa: BLE001
            raise ConfigError(f"Service {code!r} has a non-numeric rate") from None
        if rate < 0:
            raise ConfigError(f"Service {code!r} has a negative rate")

        out[code] = Service(
            code=code, name=str(entry.get("name", code)),
            client_label=" ".join(str(entry.get("client_label", "")).split()),
            category=str(entry.get("category", "Other")),
            unit=unit,  # type: ignore[arg-type]
            standard_rate=rate,
            description=" ".join(str(entry.get("description", "")).split()))
    if not out:
        raise ConfigError("The service catalogue is empty")
    return out


def load_plans(config_root: Path | None = None) -> dict[str, RatePlan]:
    """Read ``configs/billing/rate_plans.yaml``."""
    data = _load(billing_dir(config_root) / "rate_plans.yaml")
    out: dict[str, RatePlan] = {}
    for entry in data.get("plans") or []:
        key = str(entry.get("key", "")).strip()
        if not key:
            raise ConfigError(f"A rate plan has no key: {entry!r}")
        pct = Decimal(str(entry.get("discount_pct", 0)))
        if not 0 <= pct <= 100:
            raise ConfigError(
                f"Rate plan {key!r} has a discount of {pct}% — it must be between "
                f"0 and 100. A negative discount is a surcharge, which this "
                f"practice does not do; over 100 would pay the client.")
        out[key] = RatePlan(
            key=key, name=str(entry.get("name", key)), discount_pct=pct,
            requires_basis=bool(entry.get("requires_basis", False)),
            client_label=" ".join(str(entry.get("client_label", "")).split()),
            note=" ".join(str(entry.get("note", "")).split()))
    if not out:
        raise ConfigError("No rate plans are defined")
    return out


def default_plan_key(config_root: Path | None = None) -> str:
    """The plan that applies to a client nobody has priced.

    Goes through the same mtime cache as :func:`plans`. This is asked once per
    unpriced client, so on a list screen it is asked per row — and re-parsing
    the YAML each time costs milliseconds a row for an answer one line long.
    Sharing the cache also stops it reading a different version of the file
    than :func:`plans` did a moment earlier in the same request.
    """
    path = billing_dir(config_root) / "rate_plans.yaml"
    meta = _fresh(f"plans:meta:{path}", path, lambda: _load(path).get("meta") or {})
    return str(meta.get("default_plan", "standard"))


# --- reading the files, and noticing when they change ----------------------
#
# Prices are the part of this system the owner changes most often and by hand:
# a rate moves, a service gets added mid-March, a discount is renamed. Caching
# them for the life of the process means an edit appears to do nothing until
# someone remembers to restart the app — and the failure mode is silent, which
# is the worst kind. A price that quietly did not take effect is a client
# invoiced at the old rate.
#
# So the cache is keyed on what the FILES look like. Touch the YAML, and the
# next page load reads it.

_cache: dict[str, tuple[object, object]] = {}


def _stamp(path: Path) -> tuple:
    """A cheap fingerprint of a file: does it look the way it did last time?

    mtime and size together, because an editor that rewrites in place can leave
    a same-second mtime on a file whose contents changed.
    """
    try:
        st = path.stat()
    except OSError:
        return ()
    return (st.st_mtime_ns, st.st_size)


def _fresh(name: str, path: Path, loader):
    """Return the loaded config, re-reading it if the file has changed.

    A load that FAILS is not papered over with the previous good version.
    Serving the last-known-good prices after a bad edit would mean invoicing at
    a rate that is no longer in the file the owner is looking at — principle 5,
    refuse rather than default. The error names the file; fix it and reload.
    """
    stamp = _stamp(path)
    hit = _cache.get(name)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    value = loader()
    _cache[name] = (stamp, value)
    return value


def forget_prices() -> None:
    """Drop the cache. For tests, and for anything that edits config in-process."""
    _cache.clear()


def services() -> dict[str, Service]:
    return _fresh("services", billing_dir() / "services.yaml", load_services)


def plans() -> dict[str, RatePlan]:
    return _fresh("plans", billing_dir() / "rate_plans.yaml", load_plans)


def service(code: str) -> Service:
    found = services().get(code)
    if found is None:
        raise ConfigError(
            f"No service called {code!r}. Available: {', '.join(sorted(services()))}")
    return found


def plan(key: str) -> RatePlan:
    found = plans().get(key)
    if found is None:
        raise ConfigError(
            f"No rate plan called {key!r}. Available: {', '.join(sorted(plans()))}")
    return found


def by_category() -> list[tuple[str, list[Service]]]:
    """Services grouped for a picker, in catalogue order."""
    groups: list[tuple[str, list[Service]]] = []
    index: dict[str, int] = {}
    for svc in services().values():
        if svc.category not in index:
            index[svc.category] = len(groups)
            groups.append((svc.category, []))
        groups[index[svc.category]][1].append(svc)
    return groups
