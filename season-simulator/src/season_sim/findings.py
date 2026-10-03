"""Hits, folded into findings: one record per (invariant, fake client).

A hit on a day is evidence; a finding is the run of days it held. Each record
keeps the FIRST day's evidence -- the call that was made and what came back --
because that is the one a person reproduces.

Two runs of the same seed must write byte-identical findings (a CI test).
So: sorted keys, sorted records, no run directory, no pid, no wall-clock time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from season_sim.invariants import REGISTRY


@dataclass
class Finding:
    invariant: str
    sim_client: str
    first_seen: str
    last_seen: str
    days: int
    output: str
    expected: str
    subject: str
    call: dict
    subjects: set = field(default_factory=set)

    def record(self, *, seed: int, ctx_env: dict, denominators: dict, clock_note: str,
               repro_extra: str = "") -> dict:
        inv = REGISTRY[self.invariant]
        fid = hashlib.sha1(f"{self.invariant}|{self.sim_client}|{self.first_seen}".encode()
                           ).hexdigest()[:16]
        call = dict(self.call or {"door": "function", "target": "(read pass)"})
        call.setdefault("clock", f"frozen@{self.first_seen}T14:00Z")
        route = str(call.get("target", "")).startswith(("GET ", "POST "))
        call.setdefault("today_arg", "(none: the route reads date.today(), frozen)" if route
                        else self.first_seen)
        return {
            "finding_id": fid, "kind": inv.kind, "invariant": self.invariant,
            "invariant_name": inv.name, "rule": inv.rule, "source": list(inv.sources),
            "note": inv.note, "seed": seed, "first_seen": self.first_seen,
            "last_seen": self.last_seen, "days": self.days, "sim_client": self.sim_client,
            "subject": self.subject, "subjects": len(self.subjects), "call": call,
            "output": self.output, "expected_per_source": self.expected,
            "denominators": denominators, "env": ctx_env,
            "repro": (f"python -B -m season_sim repro --seed {seed} --until {self.first_seen} "
                      + (f"--client {self.sim_client} " if self.sim_client.startswith("SIM-")
                         else "")
                      + f"--check {self.invariant}"
                      + (f" {repro_extra}" if repro_extra else "")),
            "clock": clock_note,
        }


class Ledger:
    def __init__(self):
        self.open: dict[tuple[str, str], Finding] = {}
        self.examined: dict[str, int] = {}
        self.days_with_subjects: dict[str, int] = {}
        self.days_checked: dict[str, int] = {}
        self.crashes: list[dict] = []

    def add_day(self, day: str, results: dict) -> None:
        for code, (hits, examined) in results.items():
            self.days_checked[code] = self.days_checked.get(code, 0) + 1
            self.examined[code] = self.examined.get(code, 0) + int(examined or 0)
            if examined:
                self.days_with_subjects[code] = self.days_with_subjects.get(code, 0) + 1
            for h in hits:
                if h.output.startswith("CHECKER CRASHED"):
                    self.crashes.append({"day": day, "invariant": code, "error": h.output})
                    continue
                key = (code, h.sim_client)
                f = self.open.get(key)
                if f is None:
                    f = Finding(code, h.sim_client, day, day, 0, h.output, h.expected,
                                h.subject, h.call)
                    self.open[key] = f
                if f.last_seen != day or f.days == 0:
                    f.days += 1
                f.last_seen = day
                f.subjects.add(h.subject)

    def records(self, *, seed: int, env: dict, clients: int, repro_extra: str = "") -> list[dict]:
        out = []
        for (code, _sim), f in self.open.items():
            den = {"clients": clients, "examined_total": self.examined.get(code, 0),
                   "days_checked": self.days_checked.get(code, 0),
                   "days_with_subjects": self.days_with_subjects.get(code, 0)}
            out.append(f.record(seed=seed, ctx_env=env, denominators=den,
                                clock_note="time-machine, tick=False", repro_extra=repro_extra))
        kind_order = {"failure": 0, "cross_store": 1, "known": 2, "recorded_deferral": 3}
        out.sort(key=lambda r: (kind_order.get(r["kind"], 9), r["invariant"],
                                r["first_seen"], r["sim_client"]))
        return out


def dumps(records: list[dict]) -> str:
    return "".join(json.dumps(r, sort_keys=True, default=str) + "\n" for r in records)
