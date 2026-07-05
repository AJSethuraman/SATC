"""URCCP classification floors and the clock resolver — the single source.

Uniform Retail Credit Classification and Account Management Policy
(65 FR 36903, June 12, 2000; OCC Bulletin 2000-20; FDIC FIL-40-2000):

- Open- and closed-end retail loans 90 cumulative days past due -> Substandard.
- Closed-end 120 days / open-end 180 days -> Loss (charge off).

These are regulatory **floors**. A bank's own policy may *tighten* the clock
(classify/charge off sooner) but may never *loosen* it past the floor — the
resolver enforces exactly that. Both ``credit-review-os`` (live Excel formulas)
and ``credit-population-bench`` (loan-level pandas) resolve the clock through
this one function so a change here flows to both, and neither can fork the
constants.
"""

from __future__ import annotations


class URCCPError(ValueError):
    """An override would loosen the URCCP floor, or names a non-bucket boundary."""


# DPD at which each canonical delinquency bucket begins.
BUCKET_START_DPD: dict[str, int] = {
    "current": 0, "dpd_30_59": 30, "dpd_60_89": 60,
    "dpd_90_119": 90, "dpd_120_179": 120, "dpd_180_plus": 180,
}

# The interagency floors, by closed/open-end classification type.
URCCP_FLOORS: dict[str, dict[str, int]] = {
    "closed_end": {"substandard_from_dpd": 90, "loss_from_dpd": 120},
    "open_end": {"substandard_from_dpd": 90, "loss_from_dpd": 180},
}

_BOUNDARIES = sorted(set(BUCKET_START_DPD.values()))


def resolve_classification_dpd(classification_type: str,
                               overrides: dict | None = None) -> dict[str, int]:
    """Resolve the Substandard/Loss DPD clock: URCCP floor, tightened by overrides.

    ``classification_type`` is ``"closed_end"`` or ``"open_end"``. ``overrides``
    may map ``substandard_from_dpd`` / ``loss_from_dpd`` to an earlier bucket
    boundary. Raises :class:`URCCPError` if the type is unknown, an override is
    not a bucket boundary, or an override would push the clock *later* than the
    floor (a loosening — forbidden).
    """
    if classification_type not in URCCP_FLOORS:
        raise URCCPError(
            f"unknown classification_type {classification_type!r} "
            f"(expected one of {sorted(URCCP_FLOORS)})")
    floors = URCCP_FLOORS[classification_type]
    overrides = overrides or {}
    resolved: dict[str, int] = {}
    for key, floor in floors.items():
        value = overrides.get(key, floor)
        if value not in _BOUNDARIES:
            raise URCCPError(
                f"classification_overrides.{key}: {value!r} must be a bucket "
                f"boundary ({_BOUNDARIES})")
        if value > floor:
            raise URCCPError(
                f"classification_overrides.{key}={value} would LOOSEN the URCCP "
                f"floor of {floor} days for {classification_type} — bank policy "
                f"may only tighten the interagency standard (65 FR 36903)")
        resolved[key] = value
    return resolved
