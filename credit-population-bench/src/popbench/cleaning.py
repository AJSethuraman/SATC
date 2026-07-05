"""The population-validation / cleaning gate.

Nothing is computed on a dirty population. This gate takes the raw frame plus a
confirmed :class:`~popbench.mapping.Mapping`, renames columns to canonical ids,
runs the *safe, declared* normalizations (whitespace trim, unit rescale), and
**refuses on hard errors** — nulls in a required field, unparseable numerics or
weights, duplicate loan ids — with a per-issue report. Every automatic change
is recorded so the reviewer can show exactly what was done to clean the file
(the ``_cleaning`` tab). Nothing is silently imputed or dropped.

Returns the canonical frame and a list of :class:`CleaningRecord`. Raises
:class:`CleaningError` (carrying a structured report) on any hard error.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from popbench import contract
from popbench.mapping import Mapping


@dataclass(frozen=True)
class CleaningRecord:
    """One applied normalization — a row in the ``_cleaning`` audit tab."""

    rule: str            # e.g. "trim_whitespace", "rescale_percent_to_fraction"
    column: str          # canonical field id
    rows_affected: int
    detail: str = ""


@dataclass(frozen=True)
class Issue:
    """One hard error — a row in the refusal report."""

    kind: str            # "missing_required" | "unparseable" | "duplicate_id" | ...
    column: str
    count: int
    detail: str = ""


class CleaningError(ValueError):
    """The population is not clean enough to analyze. Carries the full report so
    the reviewer can fix the file upstream and reload."""

    def __init__(self, issues: list[Issue]):
        self.issues = issues
        lines = [f"  - [{i.kind}] {i.column}: {i.count} row(s){' — ' + i.detail if i.detail else ''}"
                 for i in issues]
        super().__init__("population failed validation; refusing to compute:\n"
                         + "\n".join(lines))


def _to_numeric(series: pd.Series) -> pd.Series:
    """Parse a column to numeric, tolerating thousands separators, $, %, and
    parenthesized negatives — but marking anything else as NaN so the gate can
    count unparseable values (it does not silently drop them)."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype("float64")
    cleaned = (series.astype("string").str.strip()
               .str.replace(",", "", regex=False)
               .str.replace("$", "", regex=False)
               .str.replace("%", "", regex=False))
    neg = cleaned.str.match(r"^\(.*\)$").fillna(False)
    cleaned = cleaned.str.replace(r"^\((.*)\)$", r"-\1", regex=True)
    out = pd.to_numeric(cleaned, errors="coerce")
    out = out.where(~neg, -out.abs())
    # A blank string is a genuine null, not an unparseable value.
    out = out.mask(cleaned.isin(["", "<NA>", "nan", "NaN", "None"]))
    return out.astype("float64")


def validate_and_clean(
    raw: pd.DataFrame,
    mapping: Mapping,
    required_fields: tuple[str, ...] = (),
) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Refuse-on-hard-error, log-every-fix. ``required_fields`` is the set the
    requested analysis needs present-and-non-null (universal fields are always
    required); a missing one is a hard error, not a silent gap."""
    issues: list[Issue] = []
    records: list[CleaningRecord] = []

    # 1. Rename mapped columns to canonical ids, and RETAIN unmapped columns as
    #    ad-hoc slice dimensions (the open-ended tail) rather than dropping them.
    rename = {h: fid for h, fid in mapping.rename_map().items() if h in raw.columns}
    canon_cols = list(rename.values())
    adhoc: list[tuple[str, str]] = []   # (original header, retained column name)
    for h in raw.columns:
        if h in rename:
            continue
        name = h if h not in canon_cols else f"{h}__adhoc"
        adhoc.append((h, name))
    df = raw.rename(columns=rename).copy()
    for h, name in adhoc:
        if name != h:
            df = df.rename(columns={h: name})
    df = df[canon_cols + [name for _, name in adhoc]].copy()

    required = set(contract.universal_ids()) | set(required_fields)

    # 2. Every required field must be mapped at all.
    for fid in sorted(required):
        if fid not in canon_cols:
            issues.append(Issue("missing_required", fid, 0, "field not mapped"))

    # 3. Trim canonical text (safe, recorded).
    for fid in canon_cols:
        if contract.get(fid).dtype == contract.TEXT:
            before = df[fid].astype("string")
            trimmed = before.str.strip()
            n = int((before != trimmed).fillna(False).sum())
            if n:
                records.append(CleaningRecord("trim_whitespace", fid, n))
            df[fid] = trimmed

    # 4. Parse canonical numerics/usd/ratio; rescale percent->fraction if declared.
    for fid in canon_cols:
        f = contract.get(fid)
        if f.dtype in (contract.NUM, contract.USD, contract.RATIO):
            parsed = _to_numeric(df[fid])
            unparseable = int((parsed.isna() & df[fid].notna()
                               & (df[fid].astype("string").str.strip() != "")).sum())
            if unparseable:
                issues.append(Issue("unparseable", fid, unparseable,
                                    f"non-numeric values in a {f.dtype} field"))
            if f.dtype == contract.RATIO and mapping.unit(fid) == contract.UNIT_PERCENT:
                n = int(parsed.notna().sum())
                parsed = parsed / 100.0
                records.append(CleaningRecord(
                    "rescale_percent_to_fraction", fid, n, "divided by 100"))
            df[fid] = parsed

    # 4b. Parse canonical dates; an unparseable non-blank value is a hard error.
    for fid in canon_cols:
        if contract.get(fid).dtype == contract.DATE:
            nonblank = df[fid].notna() & (df[fid].astype("string").str.strip() != "")
            parsed = pd.to_datetime(df[fid], errors="coerce")
            unparseable = int((parsed.isna() & nonblank).sum())
            if unparseable:
                issues.append(Issue("unparseable", fid, unparseable,
                                    "non-date values in a date field"))
            df[fid] = parsed

    # 4c. Coerce ad-hoc tail columns: numeric where they parse cleanly (so they
    #     can drive cohort rules like "tradelines < 3"), else trimmed strings (a
    #     group-by slice dimension). Never a hard error — the tail is optional.
    for _, name in adhoc:
        col = df[name]
        nonblank = col.notna() & (col.astype("string").str.strip() != "")
        n_nb = int(nonblank.sum())
        parsed = _to_numeric(col)
        if n_nb and int((parsed.notna() & nonblank).sum()) >= 0.8 * n_nb:
            df[name] = parsed
            records.append(CleaningRecord("coerce_adhoc_numeric", name,
                                          int(parsed.notna().sum())))
        else:
            df[name] = col.astype("string").str.strip()

    # 5. Required fields must be non-null after parsing.
    for fid in sorted(required):
        if fid in df.columns:
            n_null = int(df[fid].isna().sum())
            if n_null:
                issues.append(Issue("null_in_required", fid, n_null,
                                    "required field has missing values"))

    # 6. Loan id must be unique.
    if "loan_id" in df.columns:
        dup = int(df["loan_id"].duplicated(keep=False).sum())
        if dup:
            issues.append(Issue("duplicate_id", "loan_id", dup,
                                "loan_id must uniquely identify a row"))

    if issues:
        raise CleaningError(issues)
    return df.reset_index(drop=True), records
