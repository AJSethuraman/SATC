"""The method library: tested calculations an organization chooses and tunes but never rewrites.

Every method is a pure function of abstract inputs (rows and facts, not screen cells), and each declares, per input,
what every value state does. The declaration is data and the code consults it, so changing a treatment changes the
behaviour and the method's own test vectors (vectors/*.json) turn red. An incomplete calculation returns no number:
status "not_calculated", the missing inputs named. All methods here are fictional demonstrations, not policy.

A fact is {"state": "entered" | "missing" | "na" | "excluded", "value": ..., "reason": ...}. Zero is an entered value.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

VECTORS = Path(__file__).resolve().parent / "vectors"


@dataclass
class Result:
    status: str                      # calculated | not_calculated | no_result
    value: float | None
    parts: dict                      # ordered label -> number or None (withheld)
    missing: list = field(default_factory=list)       # what blocks the result, in words
    disclosures: list = field(default_factory=list)   # zero counted, rows left out


def blank(v):
    return v is None or v == ""


def num(v):
    return 0.0 if blank(v) else float(v)


class Method:
    name = code = version = ""
    treatment: dict = {}
    binds: dict = {}     # input name -> ("field" | "grid", required columns)

    def act(self, inp, state):
        return self.treatment[inp][state]

    def bind_errors(self, block, fields, grids):
        out = []
        inputs = block.get("inputs") or {}
        for nm, (kind, cols) in self.binds.items():
            ref = inputs.get(nm)
            if ref is None:
                out.append(("inputs", f"input '{nm}' is not bound to anything"))
            elif kind == "field" and ref not in fields:
                out.append((f"inputs.{nm}", f"'{ref}' is not a field in this tool"))
            elif kind == "grid":
                if ref not in grids:
                    out.append((f"inputs.{nm}", f"'{ref}' is not a table in this tool"))
                else:
                    have = {it["key"] for it in grids[ref]["cols"].get("items") or []}
                    lack = [c for c in cols if c not in have]
                    if lack:
                        out.append((f"inputs.{nm}", f"table '{ref}' has no column '{lack[0]}', which {self.code} needs"))
        return out

    def run(self, inputs) -> Result:
        raise NotImplementedError

    def fact(self, inp, f, label, missing, disclosures):
        """Apply the declared treatment to one fact. Returns the number to use, or None if it is left out."""
        st = f.get("state", "entered")
        if st == "entered" and blank(f.get("value")):
            st = "missing"
        if st == "entered" and num(f["value"]) == 0:
            st = "zero"
        a = self.act(inp, st)
        if a == "block":
            missing.append(f"{label} is missing")
        elif a == "reject":
            missing.append(f"{label} is marked not applicable, which this calculation cannot accept")
        elif a == "omit":
            disclosures.append(f"{label} left out: {f.get('reason') or 'no reason given'}")
            return None
        elif a == "counts":
            if st == "zero":
                disclosures.append(f"{label} entered as zero and counted as zero")
            return num(f.get("value"))
        return None


class DTI(Method):
    name, code, version = "Debt-to-income", "DTI-DEMO", "1.0"
    binds = {"income": ("grid", ["source", "amount", "per"]), "debts": ("grid", ["creditor", "payment"]), "proposed": ("field", [])}
    treatment = {
        "income":   {"missing": "block", "zero": "counts", "entered": "counts", "na": "reject", "excluded": "omit"},
        "debts":    {"missing": "block", "zero": "counts", "entered": "counts", "na": "reject", "excluded": "omit"},
        "proposed": {"missing": "block", "zero": "counts", "entered": "counts", "na": "reject", "excluded": "omit"},
    }

    def run(self, x):
        missing, disc = [], []
        income, used = 0.0, 0
        for r in x["income"]:
            if r.get("excluded"):
                self.fact("income", {"state": "excluded", "reason": r.get("reason")}, f'Income "{r.get("source") or r["label"]}"', missing, disc)
                continue
            if blank(r.get("source")) and blank(r.get("amount")) and blank(r.get("per")):
                continue
            used += 1
            lab = f'Income "{r.get("source") or r["label"]}"'
            if blank(r.get("per")):      # one problem per row, however many of its cells are empty
                missing.append(f"{lab}: " + ("the amount and whether it is monthly or annual are missing" if blank(r.get("amount")) else "whether it is monthly or annual is missing"))
                continue
            v = self.fact("income", {"value": r.get("amount")}, lab + " amount", missing, disc)
            if v is not None:
                income += v / 12 if r["per"] == "Annual" else v
        if used == 0:
            missing.append("No income has been entered")
        debts = 0.0
        for r in x["debts"]:
            lab = f'Debt "{r.get("creditor") or r["label"]}"'
            if r.get("excluded"):
                self.fact("debts", {"state": "excluded", "reason": r.get("reason")}, lab, missing, disc)
                continue
            if blank(r.get("creditor")) and blank(r.get("payment")):
                continue
            v = self.fact("debts", {"value": r.get("payment")}, lab + " payment", missing, disc)
            debts += v or 0.0
        prop = self.fact("proposed", x["proposed"], "Proposed monthly payment", missing, disc)
        n = len(missing)
        if n:
            parts = {"Monthly income": None, "Existing monthly debt payments": None, "Proposed monthly payment": None, "Inputs still missing": n}
            return Result("not_calculated", None, parts, missing, disc)
        parts = {"Monthly income": income, "Existing monthly debt payments": debts, "Proposed monthly payment": prop, "Inputs still missing": 0}
        if income == 0:
            return Result("no_result", None, parts, ["Monthly income is zero, so there is no ratio"], disc)
        return Result("calculated", (debts + prop) / income, parts, [], disc)


class DEV(Method):
    name, code, version = "Deviation rate", "DEV-DEMO", "1.0"
    binds = {}
    treatment = {"attribute": {"missing": "block", "zero": "counts", "entered": "counts", "na": "reject", "excluded": "omit"}}

    def bind_errors(self, block, fields, grids):
        g = block.get("grid")
        if g not in grids:
            return [("grid", f"'{g}' is not a table in this tool")]
        have = {it["key"] for it in grids[g]["cols"].get("items") or []}
        lack = [a for a in block.get("attributes") or [] if a not in have]
        if not block.get("attributes"):
            return [("attributes", "name the columns that are tested")]
        return [("attributes", f"table '{g}' has no column '{lack[0]}'")] if lack else []

    def run(self, x):
        missing, disc = [], []
        tested = exc = 0
        for r in x["rows"]:
            vals = r["attrs"]
            if r.get("excluded"):
                if self.act("attribute", "excluded") == "omit":
                    disc.append(f'{r["label"]} left out: {r.get("reason") or "no reason given"}')
                    continue
            filled = [v for v in vals if not blank(v)]
            if not filled:
                continue
            tested += 1
            if len(filled) < len(vals) and self.act("attribute", "missing") == "block":
                missing.append(f'{r["label"]}: {len(vals) - len(filled)} attribute(s) not marked')
            if any(v == "Exception" for v in vals):
                exc += 1
        n = len(missing)
        parts = {"Items tested": tested, "Items with an exception": exc, "Inputs still missing": n}
        if n or tested == 0:
            if tested == 0:
                missing.append("No items have been tested")
            return Result("not_calculated", None, parts, missing, disc)
        return Result("calculated", exc / tested, parts, [], disc)


class REC(Method):
    name, code, version = "Reconciliation", "REC-DEMO", "1.0"
    binds = {"items": ("grid", ["type", "amount"]), "bank": ("field", []), "books": ("field", [])}
    treatment = {
        "bank":  {"missing": "block", "zero": "counts", "entered": "counts", "na": "reject", "excluded": "omit"},
        "books": {"missing": "block", "zero": "counts", "entered": "counts", "na": "reject", "excluded": "omit"},
        "items": {"missing": "block", "zero": "counts", "entered": "counts", "na": "reject", "excluded": "omit"},
    }
    SIGN_BANK = {"Deposit in transit": 1, "Outstanding check": -1}
    SIGN_BOOKS = {"Bank fee not yet booked": -1, "Interest not yet booked": 1}

    def run(self, x):
        missing, disc = [], []
        bank = self.fact("bank", x["bank"], "Balance per bank statement", missing, disc)
        books = self.fact("books", x["books"], "Balance per ledger", missing, disc)
        adj_bank, adj_books = bank or 0.0, books or 0.0
        for r in x["items"]:
            lab = f'{r["label"]} ({r.get("type") or "no type"})'
            if r.get("excluded"):
                self.fact("items", {"state": "excluded", "reason": r.get("reason")}, lab, missing, disc)
                continue
            if blank(r.get("type")) and blank(r.get("amount")):
                continue
            if blank(r.get("type")):
                missing.append(f'{r["label"]}: the type is missing')
                continue
            v = self.fact("items", {"value": r.get("amount")}, lab + " amount", missing, disc)
            if v is None:
                continue
            adj_bank += self.SIGN_BANK.get(r["type"], 0) * v
            adj_books += self.SIGN_BOOKS.get(r["type"], 0) * v
        n = len(missing)
        if n:
            return Result("not_calculated", None, {"Adjusted bank": None, "Adjusted books": None, "Inputs still missing": n}, missing, disc)
        return Result("calculated", round(adj_bank - adj_books, 2) + 0.0,
                      {"Adjusted bank": round(adj_bank, 2), "Adjusted books": round(adj_books, 2), "Inputs still missing": 0}, [], disc)


METHODS = {"dti": DTI(), "devrate": DEV(), "recon": REC()}


def vectors(method_key):
    return json.loads((VECTORS / f"{method_key}.json").read_text())


def run_vector(method_key, v):
    return METHODS[method_key].run(v["inputs"])
