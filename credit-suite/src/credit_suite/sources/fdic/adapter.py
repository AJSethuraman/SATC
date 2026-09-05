"""The FDIC provider adapter: the only FDIC-specific code that touches a network.

Two implementations, as the contract requires (section 6): the live BankFind
adapter and a deterministic offline `FdicDemoProvider` that needs no key and no
network. Every test uses the demo one.

Both are extracted unchanged from the monitor this replaces. The demo profile
especially is left alone on purpose: its stress tiers and injected nulls are
calibrated so the demo workbook lights a realistic mix of flags, and the parity
golden pins the exact numbers it produces. A "tidier" generator is a different
workbook.

FDIC-specific behaviour that stays on this side of the seam: the ONE bulk
BankFind call for the whole peer set, the double-wrapped `data[i].data`
response shape, the refusal to accept a truncated response, the roster lookup
for merger/closure detection, and the `--lookup` name-to-CERT helper. The engine
sees only NormalizedRows.
"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from datetime import date
from typing import Dict, List, Optional, Sequence

import pandas as pd

from credit_suite.engine.config import Config, norm_key
from credit_suite.engine.provider import (FieldSpec, NormalizedRow, Provider,
                                          resolve_secret)
from credit_suite.sources.fdic import mergers as _mergers
from credit_suite.sources.fdic.fields import (FIELD_UNITS, MAX_REQUEST_FIELDS,
                                              PCT_FIELDS, RAW_FIELDS)

def _iso_day(yyyymmdd: str) -> str:
    """'20220901' -> '2022-09-01' (the history endpoint dates are ISO)."""
    s = str(yyyymmdd)
    return "%s-%s-%s" % (s[0:4], s[4:6], s[6:8])


FDIC_FIN_URL = "https://api.fdic.gov/banks/financials"
FDIC_INST_URL = "https://api.fdic.gov/banks/institutions"

class FdicDemoProvider(Provider):
    """Deterministic offline stand-in (BUILD SPEC 0.7). Seeded per (cert,
    field) -- the SAME bank yields the SAME history in any slot, so a [PEERS]
    swap visibly moves data between slots (the flexibility test). Realistic
    ranges per metric; the seed profile puts one illustrative bank in a
    Texas-ALERT tier and one in a Texas-WATCH tier; one bank's BRO is null
    for the whole series (trap F3); every series carries one interior None.
    NO network, NO key; never stale at its own asof.

    Asked for a merger record it answers "I did not ask anyone" (`mergers`
    stays None), never "there are none" -- two different facts, printed
    differently on the `_mergers` tab. The runner's merger block is exercised
    offline by injecting a provider that carries a real record
    (tests/test_mergers.py)."""
    mergers = None

    source_class = "A"

    def __init__(self, asof: Optional[date] = None,
                 raw_slots: int = 16):
        super().__init__()
        self.asof = asof or date(2026, 3, 31)
        self.raw_slots = raw_slots
        self.vintage = "demo data (FdicDemoProvider -- no live vintage)"
        self._profiles: Dict[str, List[Tuple[str, Dict[str, Optional[float]]]]] = {}

    def prime(self, certs, asof=None, names=None):
        names = names or {}
        for c in certs:
            self.roster[str(c)] = {
                "CERT": str(c), "NAME": names.get(str(c), f"Bank {c}"),
                "ACTIVE": 1, "BKCLASS": "N", "ENDEFYMD": None,
                "FED_RSSD": None}

    @staticmethod
    def _seed(cert: str) -> int:
        try:
            n = int(cert)
        except ValueError:
            n = sum((i + 1) * ord(c) for i, c in enumerate(cert))
        return (n * 2654435761) % (2 ** 32)

    def _periods(self) -> List[str]:
        idx = pd.period_range(end=pd.Period(self.asof, freq="Q"),
                              periods=self.raw_slots, freq="Q")
        return [p.to_timestamp(how="end").date().isoformat() for p in idx]

    def _profile(self, cert: str):
        """Full consistent quarter-by-quarter field history for one bank:
        dollar fields derive from the SAME wobbled ratios the ratio fields
        report, so every derived metric (Texas, coverage, CRE) is internally
        consistent -- the parity tests lean on that."""
        if cert in self._profiles:
            return self._profiles[cert]
        s = self._seed(cert)
        n = self.raw_slots
        tier = s % 13                       # 0 = ALERT tier, 1 = WATCH tier
        # newest-quarter targets per tier (ratios in percent)
        if tier == 0:      # deep-stress illustrative bank: Texas > 100
            eq_r, ncl, res_r, p3, nco = 0.035, 13.0, 6.5, 3.4, 2.3
            roaq, nimy, eeffr = -0.6, 1.9, 88.0
        elif tier == 1:    # stressed illustrative bank: Texas 50-100
            eq_r, ncl, res_r, p3, nco = 0.055, 8.6, 6.4, 2.1, 1.3
            roaq, nimy, eeffr = 0.3, 2.35, 74.0
        else:              # healthy ranges
            eq_r = 0.092 + (s % 25) * 0.001
            ncl = 0.35 + (s % 14) * 0.09
            res_r = 1.05 + (s % 9) * 0.09
            p3 = 0.5 + (s % 9) * 0.1
            nco = 0.12 + (s % 10) * 0.05
            roaq = 0.85 + (s % 8) * 0.09
            nimy = 2.65 + (s % 14) * 0.11
            eeffr = 52.0 + (s % 17)
        asset0 = 2.0e6 + (s % 400) * 1.0e6          # $000: $2B - $402B
        loans_r = 0.55 + (s % 18) * 0.01
        dep_r = 0.72 + (s % 9) * 0.01
        bro_r = ((s >> 4) % 29) / 200.0     # 0-14%: a couple of WATCHes, no ALERT
        bro_none = (s % 17) == 3                     # whole-series null BRO
        cre_c = 0.02 + (s % 6) * 0.005
        cre_n = 0.10 + (s % 12) * 0.01
        cre_m = 0.03 + (s % 7) * 0.01
        # ---- v1.1 pack seeding (per class; newest-quarter targets, pct) ----
        # The stress tiers trip the new bands (spec sec 3: 1-2 demo banks);
        # healthy ranges sit under the ALERT bands (a few WATCHes by design).
        # Class rates: {class: (PD30-89, PD90+, nonaccrual, NCOq annualized)}
        if tier == 0:      # deep-stress: trips ALERT across headline + classes
            rate = {"crcd": (6.0, 4.5, 2.5, 9.5), "auto": (7.0, 2.5, 3.5, 5.0),
                    "conoth": (6.0, 3.5, 4.5, 5.0), "reres": (5.0, 3.5, 3.5, 2.0),
                    "reloc": (5.0, 3.5, 3.5, 0.0), "recons": (5.0, 3.5, 8.0, 3.5),
                    "renres": (5.0, 3.5, 8.0, 3.5), "remult": (5.0, 3.5, 6.0, 3.5),
                    "ci": (3.5, 2.5, 3.5, 3.5)}
            unins, unrlz, fhlb = 80.0, 60.0, 25.0
        elif tier == 1:    # moderate-stress: mostly WATCH under calibrated bands
            rate = {"crcd": (2.6, 1.7, 0.4, 6.5), "auto": (4.5, 1.2, 1.8, 2.8),
                    "conoth": (3.2, 1.7, 2.7, 2.4), "reres": (2.4, 1.6, 1.7, 0.9),
                    "reloc": (2.2, 1.6, 1.7, 0.0), "recons": (2.4, 1.6, 4.5, 1.7),
                    "renres": (2.2, 1.6, 4.5, 1.7), "remult": (2.1, 1.6, 3.5, 1.6),
                    "ci": (1.6, 1.1, 1.7, 1.7)}
            unins, unrlz, fhlb = 65.0, 30.0, 12.0
        else:
            rate = {
                "crcd": (0.9 + (s % 7) * 0.13, 0.7 + (s % 5) * 0.11,
                         0.1 + (s % 4) * 0.09, 1.2 + (s % 10) * 0.18),
                "auto": (1.0 + (s % 8) * 0.14, 0.15 + (s % 4) * 0.07,
                         0.2 + (s % 5) * 0.09, 0.3 + (s % 6) * 0.09),
                "conoth": (1.0 + (s % 7) * 0.12, 0.3 + (s % 5) * 0.09,
                           0.3 + (s % 4) * 0.11, 1.0 + (s % 8) * 0.11),
                "reres": (0.8 + (s % 6) * 0.13, 0.3 + (s % 4) * 0.1,
                          0.4 + (s % 5) * 0.09, 0.02 + (s % 5) * 0.02),
                "reloc": (0.5 + (s % 5) * 0.12, 0.2 + (s % 4) * 0.08,
                          0.3 + (s % 4) * 0.09, 0.0),
                "recons": (0.4 + (s % 6) * 0.12, 0.2 + (s % 4) * 0.09,
                           0.4 + (s % 6) * 0.12, 0.05 + (s % 5) * 0.06),
                "renres": (0.3 + (s % 5) * 0.11, 0.15 + (s % 4) * 0.07,
                           0.3 + (s % 5) * 0.11, 0.1 + (s % 4) * 0.07),
                "remult": (0.3 + (s % 4) * 0.11, 0.15 + (s % 3) * 0.07,
                           0.3 + (s % 4) * 0.1, 0.1 + (s % 3) * 0.07),
                "ci": (0.3 + (s % 5) * 0.1, 0.15 + (s % 4) * 0.06,
                       0.3 + (s % 5) * 0.1, 0.1 + (s % 5) * 0.07)}
            unins = 22.0 + (s % 11) * 2.0            # 22-42: WATCH edge only
            unrlz = 6.0 + (s % 10) * 2.0             # 6-24: under the 25 WATCH
            fhlb = 1.0 + (s % 9)                     # 1-9: under the 10 WATCH
        # class balance shares of total loans / assets
        cc_sh = 0.01 + (s % 6) * 0.01                # cards 1-6% of loans
        au_sh = 0.02 + (s % 5) * 0.01                # auto 2-6%
        oc_sh = 0.02 + (s % 4) * 0.01                # other consumer 2-5%
        rr_sh = 0.18 + (s % 8) * 0.02                # 1-4 family 18-32%
        ci_sh = 0.18 + (s % 9) * 0.02                # C&I 18-34%
        htm_sh = 0.10 + (s % 6) * 0.02               # HTM securities / assets
        afs_sh = 0.12 + (s % 7) * 0.02               # AFS securities / assets
        # F-trap vintages/coverage: one bank reports NO auto book (fields null
        # from 2011 only / not a lender) and one bank's DEPUNINS is null for
        # the whole series (RC-O Mem 2 is filed by $1B+ reporters only) --
        # blanks, never zeros (F3).
        auto_none = (s % 19) == 9
        depunins_none = (s % 23) == 7
        periods = self._periods()
        quarters = []
        for i, iso in enumerate(periods):            # i=0 oldest .. n-1 newest
            ramp = 0.7 + 0.3 * (i / max(1, n - 1))   # deterioration narrative
            wob = 1.0 + 0.04 * math.sin((i + s % 7) / 2.1)
            a = asset0 * ((1.009) ** i) * (1.0 + 0.008 * math.sin((i + s % 9) / 2.7))
            loans = loans_r * a
            ncl_i = ncl * ramp * wob
            res_i = res_r * (0.9 + 0.1 * ramp) * wob
            f: Dict[str, Optional[float]] = {}
            f["ASSET"] = round(a)
            f["DEP"] = round(dep_r * a)
            f["LNLSGR"] = round(loans)
            f["LNLSNET"] = round(loans * (1.0 - res_i / 100.0))
            f["BRO"] = None if bro_none else round(bro_r * dep_r * a)
            f["EQ"] = round(eq_r * a)
            f["NCLNLS"] = round(ncl_i / 100.0 * loans)
            f["LNATRES"] = round(res_i / 100.0 * loans)
            f["P3LNLS"] = round(p3 * ramp / 100.0 * loans)
            f["LNRECONS"] = round(cre_c * loans)
            f["LNRENRES"] = round(cre_n * loans)
            f["LNREMULT"] = round(cre_m * loans)
            f["NCLNLSR"] = round(ncl_i, 4)
            f["NTLNLSQR"] = round(nco * ramp * wob, 4)
            f["LNATRESR"] = round(res_i, 4)
            f["LNRESNCR"] = round(res_i / ncl_i * 100.0, 4)
            f["RBC1AAJ"] = round(eq_r * 100.0 - 0.3 + 0.2 * math.sin(i + s), 4)
            # CBLR-elector shape: risk-based ratio can be null (trap F3)
            f["RBCRWAJ"] = round(eq_r * 100.0 + 5.2 + 0.3 * math.sin(i + s), 4)
            f["EQV"] = round(eq_r * 100.0, 4)
            f["ROAQ"] = round(roaq * (0.85 + 0.15 * ramp) * wob, 4)
            f["NIMY"] = round(nimy * wob, 4)
            f["EEFFR"] = round(eeffr * wob, 4)
            # ---- v1.1 pack fields (internally consistent: dollar triples
            # derive from the SAME wobbled class rates the R-twins report,
            # so Python/Excel parity holds on the landed values) ----
            bal = {"crcd": round(cc_sh * loans), "auto": round(au_sh * loans),
                   "conoth": round(oc_sh * loans), "reres": round(rr_sh * loans),
                   "ci": round(ci_sh * loans),
                   "recons": f["LNRECONS"], "renres": f["LNRENRES"],
                   "remult": f["LNREMULT"]}
            f["LNCRCD"], f["LNAUTO"] = bal["crcd"], bal["auto"]
            f["LNCONOTH"], f["LNRERES"] = bal["conoth"], bal["reres"]
            f["LNCI"] = bal["ci"]

            def rw(cls, k):                          # ramped+wobbled class rate
                return rate[cls][k] * ramp * wob
            # verified R-twin rate fields land as percents directly
            for cls, pre in (("crcd", "CRCD"), ("auto", "AUTO"),
                             ("reres", "RERES"), ("reloc", "RELOC"),
                             ("ci", "CI")):
                f["P3" + pre + "R"] = round(rw(cls, 0), 4)
                f["P9" + pre + "R"] = round(rw(cls, 1), 4)
                f["NA" + pre + "R"] = round(rw(cls, 2), 4)
            # computed classes land the dollar triple off the same rates
            for cls, suf in (("conoth", "CONOTH"), ("recons", "RECONS"),
                             ("renres", "RENRES"), ("remult", "REMULT")):
                f["P3" + suf] = round(rw(cls, 0) / 100.0 * bal[cls])
                f["P9" + suf] = round(rw(cls, 1) / 100.0 * bal[cls])
                f["NA" + suf] = round(rw(cls, 2) / 100.0 * bal[cls])
            # quarterly NCO dollars: rate is ANNUALIZED, flow = rate/400 * bal
            for cls, fld in (("crcd", "NTCRCDQ"), ("auto", "NTAUTOQ"),
                             ("conoth", "NTCONOTQ"), ("reres", "NTRERESQ"),
                             ("recons", "NTRECONQ"), ("renres", "NTRENREQ"),
                             ("remult", "NTREMULQ"), ("ci", "NTCIQ")):
                f[fld] = round(rw(cls, 3) / 400.0 * bal[cls])
            if auto_none:                            # not an auto lender
                for fld in ("LNAUTO", "P3AUTOR", "P9AUTOR", "NAAUTOR",
                            "NTAUTOQ"):
                    f[fld] = None
            # SVB pack: uninsured share, HTM/AFS unrealized (60/40 split so
            # ((SCHA-SCHF)+(SCAA-SCAF))/(EQ+LNATRES) == the seeded target),
            # FHLB advances
            f["DEPUNINS"] = (None if depunins_none
                             else round(unins * ramp * wob / 100.0 * f["DEP"]))
            cushion = f["EQ"] + f["LNATRES"]
            loss = unrlz * ramp * wob / 100.0 * cushion
            f["SCHA"] = round(htm_sh * a)
            f["SCHF"] = round(htm_sh * a - 0.6 * loss)
            f["SCAA"] = round(afs_sh * a)
            f["SCAF"] = round(afs_sh * a - 0.4 * loss)
            f["OTHBFHLB"] = round(fhlb * ramp * wob / 100.0 * a)
            quarters.append((iso, f))
        # one interior None per (cert, field) series -- exercises the
        # missing-value path deterministically, at offsets >= 2 from newest so
        # the latest-quarter headline formulas never see it.
        n_q = len(quarters)
        if n_q >= 6:
            for j, fname in enumerate(RAW_FIELDS):
                k_from_new = 2 + (s + 7 * j) % (n_q - 3)
                quarters[n_q - 1 - k_from_new][1][fname] = None
        self._profiles[cert] = quarters
        return quarters

    def fetch_series(self, spec: FieldSpec, secret=None) -> List[NormalizedRow]:
        quarters = self._profile(spec.key)          # oldest-first
        return [NormalizedRow(id=spec.id, period=iso, value=f[spec.fname],
                              geo_segment=spec.geo_segment,
                              source_class=self.source_class, units=spec.units)
                for iso, f in quarters]


class FdicProvider(Provider):
    """Live Class A provider: plain urllib REST against api.fdic.gov (BUILD
    SPEC 0.3 -- KEYLESS: the FDIC BankFind API needs no API key; swagger marks
    api_key optional and every observed client is keyless). ONE bulk
    /financials request per refresh covers the whole peer set (30 banks x
    banks x 16 quarters = ~640 rows << the 10,000-row cap; ~70 fields <<
    the 250-field cap), plus one /institutions
    roster call for identity + merger detection (trap F2). Rate limit is
    UNDOCUMENTED -- be polite: min_interval throttle, 429/5xx backoff,
    per-URL cache."""

    source_class = "A"

    def __init__(self, min_interval: float = 0.6, max_retries: int = 4,
                 raw_slots: int = 16, limit: int = 10000):
        super().__init__()
        self._min_interval = float(min_interval)
        self._max_retries = int(max_retries)
        self._raw_slots = int(raw_slots)
        self._limit = int(limit)
        self._last = 0.0
        self._cache: Dict[str, bytes] = {}
        self._bulk: Optional[Dict[str, Dict[str, Dict[str, Optional[float]]]]] = None

    def _throttle(self):
        gap = time.time() - self._last
        if gap < self._min_interval:
            time.sleep(self._min_interval - gap)
        self._last = time.time()

    def _http_get(self, url: str) -> bytes:
        """The one real network call -- isolated so tests can stub it."""
        import urllib.request
        with urllib.request.urlopen(url, timeout=60) as resp:
            return resp.read()

    def _download(self, url: str, label: str) -> bytes:
        """Cache + throttle + backoff. 429/5xx retry with backoff; other HTTP
        codes fail fast (bad filter syntax / bad field name)."""
        if url in self._cache:                       # repeat fetch == cache hit
            return self._cache[url]
        import urllib.error
        for attempt in range(self._max_retries + 1):
            self._throttle()
            try:
                data = self._http_get(url)
                self._cache[url] = data
                return data
            except urllib.error.HTTPError as exc:
                if exc.code == 429 or exc.code >= 500:
                    if attempt < self._max_retries:
                        time.sleep(2.0 * (attempt + 1))
                        continue
                raise RuntimeError(f"FDIC fetch failed for {label}: "
                                   f"HTTP {exc.code}")
            except Exception as exc:
                if attempt < self._max_retries:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"FDIC fetch failed for {label}: "
                                   f"{type(exc).__name__}")

    @staticmethod
    def _iso(repdte: str) -> str:
        r = str(repdte).strip()
        if len(r) == 8 and r.isdigit():              # "20260331" -> ISO
            return f"{r[0:4]}-{r[4:6]}-{r[6:8]}"
        return r

    @staticmethod
    def _oldest_repdte(asof: date, raw_slots: int) -> str:
        """Lower REPDTE bound: raw_slots quarters back from asof (fetch only
        what lands)."""
        months = raw_slots * 3
        y = asof.year - (months // 12)
        m = asof.month - (months % 12)
        if m < 1:
            m += 12
            y -= 1
        return f"{y:04d}{m:02d}01"

    def prime(self, certs, asof, names=None):
        """The ONE bulk /financials call + the /institutions roster call.
        Guard: meta.total > limit errors CLEARLY -- silent truncation would
        quietly drop whole banks (BUILD SPEC sec 1)."""
        certs = [str(c) for c in certs if str(c)]
        self._bulk = {}
        if not certs:
            return
        from urllib.parse import urlencode
        filt = ("CERT:(" + " OR ".join(certs) + ") AND REPDTE:["
                + self._oldest_repdte(asof, self._raw_slots) + " TO *]")
        field_list = ["CERT", "REPDTE"] + list(RAW_FIELDS)
        if len(field_list) >= MAX_REQUEST_FIELDS:    # spec sec 3 guard
            raise RuntimeError(
                f"fields= list has {len(field_list)} entries -- the FDIC "
                f"bulk endpoint caps at {MAX_REQUEST_FIELDS}.")
        url = FDIC_FIN_URL + "?" + urlencode({
            "filters": filt,
            "fields": ",".join(field_list),
            "sort_by": "REPDTE", "sort_order": "DESC",
            "limit": str(self._limit), "format": "json"})
        payload = json.loads(self._download(url, "financials bulk").decode("utf-8"))
        meta = payload.get("meta") or {}
        total = meta.get("total")
        if isinstance(total, dict):                  # ES-style nested total
            total = total.get("value")
        if total is not None and int(total) > self._limit:
            raise RuntimeError(
                f"FDIC bulk response reports {total} rows but the request "
                f"limit is {self._limit}: the peer set x quarter window "
                f"exceeds one page. Narrow raw_slots or the peer list -- "
                f"refusing silent truncation.")
        self.vintage = str((meta.get("index") or {}).get("createTimestamp")
                           or "")
        for rec in payload.get("data", []):
            d = rec.get("data") or {}                # DOUBLE WRAP: data[i].data
            cert = norm_key(d.get("CERT"))
            iso = self._iso(d.get("REPDTE", ""))
            if not cert or not iso:
                continue
            entry = {}
            for f in RAW_FIELDS:
                v = d.get(f)
                # JSON null -> None, NEVER zero (trap F3: CBLR risk-based
                # ratios and non-applicable items are genuinely null)
                entry[f] = None if v is None else float(v)
            self._bulk.setdefault(cert, {})[iso] = entry
        # roster: identity + merger detection (ACTIVE/ENDEFYMD -- trap F2)
        rurl = FDIC_INST_URL + "?" + urlencode({
            "filters": "CERT:(" + " OR ".join(certs) + ")",
            "fields": "CERT,NAME,FED_RSSD,ACTIVE,BKCLASS,ENDEFYMD",
            "limit": str(max(len(certs), 10)), "format": "json"})
        try:
            rp = json.loads(self._download(rurl, "institutions roster").decode("utf-8"))
            for rec in rp.get("data", []):
                d = rec.get("data") or {}
                c = norm_key(d.get("CERT"))
                if c:
                    self.roster[c] = d
        except Exception:
            # roster is advisory (merger notes); the financials landing and
            # the staleness guard still protect the run without it
            self.roster = self.roster or {}

        # The merger record: which quarters' FLOWS span two banks. One more
        # request for the whole peer set. A failure here leaves `mergers` at
        # None -- UNKNOWN, which the tab and the tools report as its own
        # answer, because an empty record read as "no mergers" is precisely
        # the 670% chart this exists to prevent (sources/fdic/mergers.py).
        try:
            found, unclassified = _mergers.fetch(
                certs, self._download,
                # only the charted window can contaminate a charted quarter,
                # and the endpoint otherwise returns a bank's whole life
                # (Wells Fargo back to 1972)
                since=_mergers.quarter_start(
                    _iso_day(self._oldest_repdte(asof, self._raw_slots))))
            self.mergers = _mergers.by_cert(found)
            self.merger_note = ""
            if unclassified:
                codes = sorted({str(r.get("CHANGECODE")) for r in unclassified})
                self.merger_note = (
                    "%d FDIC history rows carry change codes this template "
                    "does not classify (%s); they are reported rather than "
                    "assumed harmless."
                    % (len(unclassified), ", ".join(codes)))
        except Exception as exc:                      # network, or a refusal
            self.mergers = None
            self.merger_note = "merger record unavailable: %s" % exc

    def fetch_series(self, spec: FieldSpec, secret=None) -> List[NormalizedRow]:
        if self._bulk is None:
            raise RuntimeError("FdicProvider.fetch_series before prime(): the "
                               "bulk request must run once per refresh.")
        quarters = self._bulk.get(spec.key, {})
        rows = []
        for iso in sorted(quarters):                 # oldest-first, like demo
            rows.append(NormalizedRow(
                id=spec.id, period=iso, value=quarters[iso].get(spec.fname),
                geo_segment=spec.geo_segment, source_class=self.source_class,
                units=spec.units))
        return rows

    def lookup(self, name: str) -> List[dict]:
        """--lookup support (USER REQUIREMENT): fuzzy /institutions search so
        the user can find CERTs from PowerShell. LIVE-ONLY."""
        from urllib.parse import urlencode
        url = FDIC_INST_URL + "?" + urlencode({
            "search": name,
            "fields": "NAME,CERT,CITY,STALP,ASSET,ACTIVE",
            "limit": "15", "format": "json"})
        payload = json.loads(self._download(url, f'lookup "{name}"').decode("utf-8"))
        return [rec.get("data") or {} for rec in payload.get("data", [])]


def make_provider(cfg: Config, demo: bool, asof: Optional[date]) -> Provider:
    if demo or cfg.demo_mode:
        return FdicDemoProvider(asof=asof, raw_slots=cfg.raw_slots)
    # KEYLESS live provider -- no env var, no secret, nothing to fail fast on.
    return FdicProvider(
        min_interval=float(cfg.setting("http_min_interval", 0.6) or 0.6),
        max_retries=int(float(cfg.setting("fdic_max_retries", 4) or 4)),
        raw_slots=cfg.raw_slots)
