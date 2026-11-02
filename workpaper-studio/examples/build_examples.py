"""Build the example outputs for Workpaper Studio from one synthetic dataset.

Run:  python3 workpaper-studio/examples/build_examples.py
Then: node workpaper-studio/examples/print_pdfs.js      (HTML -> PDF)
      python3 workpaper-studio/examples/check_workbook.py (LibreOffice recalculates the workbook; asserts no errors)

Everything here is synthetic. Methods and limits are fictional demonstrations.
This script is an illustration of what the product would produce. It is not the
product engine, and a real build must generate these from the engine itself
(TENETS S3: two halves of one tool must make the same call).
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import random
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
E = html.escape

ORG = "Lakeshore Community Bank (synthetic)"
PACK = {"name": "Credit file review pack", "version": "1.1", "fingerprint": "pack 7c1e04a2"}
QUARTER = "2026-Q3"
RATINGS = ["Effective", "Partially effective", "Not effective", "Not applicable"]

QUESTIONS = [
    ("1.01", "Risk rating", "Is the assigned risk rating supported by the credit file?",
     "Read the approval document and its attachments. Using your rating guidance and judgment, conclude whether the rating is reasonable."),
    ("1.02", "Risk rating", "Is each facility rating consistent with the borrower rating?",
     "Compare the two and note any difference that the file does not explain."),
    ("2.01", "Data accuracy", "Does the rating in the system of record match the approval document?",
     "Compare the two. If you cannot reach the system, use the most recent account report."),
    ("2.02", "Data accuracy", "Is the industry code correct in the system of record?",
     "Compare the code with the approval document."),
    ("3.01", "Policy exceptions", "Are all policy exceptions noted and mitigated in the approval document?",
     "Read the exceptions section. Confirm each one has a documented mitigant, or that none was needed."),
    ("4.01", "Approval authority", "Was the credit approved by someone with enough authority?",
     "Compare the total commitment with the approval authority table for the line of business."),
    ("5.01", "Repayment analysis", "Were all liabilities considered in the repayment analysis?",
     "Compare the liabilities in the analysis with the credit report and the borrower statement."),
    ("5.02", "Repayment analysis", "For a new money request, was the required analysis completed with current information?",
     "Confirm the analysis was required, was completed, and used current information."),
    ("6.01", "Collateral", "Was the collateral eligible, valued and documented?",
     "Confirm the collateral type is allowed, the valuation is current and the lien is documented."),
]

# ---------------------------------------------------------------- the one finished case
CASE = {
    "id": "CR-2026Q3-07", "borrower": "Harbor Millwork LLC", "tester": "A. Rivera", "reviewer": "D. Patel",
    "review_date": "2026-10-14", "quarter_end": "2026-09-30", "scope": "New money, secured, small business",
    "security": "Secured", "new_money": "Yes", "status": "Signed off", "signed": "2026-10-16",
    "qualified": "Yes",
    "summary": ("The credit is qualified and the rating is supported. Two weaknesses: the industry code in the "
                "system does not match the approval document, and the recomputed debt-to-income is above the "
                "limit without an explanation in the file. One policy exception lacked a mitigant."),
    "facilities": [("Term loan", 5, 285000, 285000), ("Line of credit", 5, 75000, 22500)],
    "ratings": {
        "1.01": ("Effective", "Rating supported by cash flow and collateral coverage."),
        "1.02": ("Effective", ""),
        "2.01": ("Effective", ""),
        "2.02": ("Not effective", "System shows a different industry code from the approval document."),
        "3.01": ("Partially effective", "One exception (collateral advance) noted without a mitigant."),
        "4.01": ("Effective", ""),
        "5.01": ("Effective", "Credit report liabilities match the analysis."),
        "5.02": ("Partially effective", "Recomputed debt-to-income is 51.3% against a 40% limit (fictional). The file does not explain the difference."),
        "6.01": ("Effective", "Appraisals on file, liens recorded."),
    },
    "cashflow_people": ["J. Hale (owner)", "M. Hale (guarantor)"],
    "cashflow": {"inc": [96000, 41000], "debt": [18600, 6200]},
    "valuation": [("Equipment", 190000, 70), ("Real estate", 240000, 80)],
    "dti": {"income": [("Owner salary", 96000, "Annual"), ("Rental, 14 Dock St", 1450, "Monthly"), ("Spouse wages", 3200, "Monthly")],
            "debts": [("Auto loan", 612), ("Credit card", 95), ("Student loan (deferred)", 0)],
            "proposed": 5780, "limit": 0.40},
    "review_points": [
        ("5.02", "D. Patel", "Did you count the rental income? The return shows a loss.",
         "A. Rivera", "Yes, at lease rent. The loss was depreciation. Kept as partially effective.", "Cleared"),
        ("2.02", "D. Patel", "Which code is right?",
         "A. Rivera", "The approval document. The system needs correcting; the owner has been told.", "Cleared"),
    ],
}


def dti(case):
    d = case["dti"]
    inc = sum(a / 12 if per == "Annual" else a for _, a, per in d["income"])
    debt = sum(p for _, p in d["debts"])
    return inc, debt, d["proposed"], (debt + d["proposed"]) / inc


INC, DEBT, PROP, DTI = dti(CASE)
assert abs(DTI - 0.51281) < 1e-4  # (707 + 5,780) / 12,650


def fingerprint(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:12]


def pct_half_up(x):
    # 0.625 -> 63%. Python's round() sends halves to the even number (62%), which a reader checking by hand would call wrong.
    from decimal import Decimal, ROUND_HALF_UP
    return f"{(Decimal(str(x)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)}%"


def money(n):
    return f"${n:,.0f}"


# ---------------------------------------------------------------- the quarter's sample (synthetic)
BORROWERS = ["Alder Lane Bakery", "Birchwood Dental Group", "Cedar & Stone Landscaping", "Delta Supply Co.",
             "Eastside Auto Repair", "Fairview Veterinary", "Granite Peak Builders", "Harbor Millwork LLC",
             "Ironwood Logistics", "Juniper Cafe & Catering", "Kestrel Print Shop", "Lakeview Pharmacy"]
TESTERS = ["A. Rivera", "B. Chen", "C. Okafor"]
COMMENTS = {
    "1.01": ["Rating one grade too favourable for leverage shown.", "Rating not justified in the write-up."],
    "1.02": ["Facility rating differs from borrower rating without explanation."],
    "2.01": ["System rating not updated after approval."],
    "2.02": ["Industry code differs between system and approval."],
    "3.01": ["Exception noted without a mitigant.", "Exception not noted."],
    "4.01": ["Approved one level below the required authority."],
    "5.01": ["A guarantor's personal debt was left out."],
    "5.02": ["Analysis used financial statements older than required.", "Debt-to-income above the limit without explanation."],
    "6.01": ["Valuation older than allowed.", "Lien not recorded at review date."],
}
WEIGHTS = {"1.01": (82, 12, 6), "1.02": (90, 8, 2), "2.01": (88, 6, 6), "2.02": (70, 10, 20), "3.01": (64, 26, 10),
           "4.01": (94, 4, 2), "5.01": (80, 15, 5), "5.02": (66, 24, 10), "6.01": (78, 16, 6)}


def build_sample():
    rng = random.Random(2026)
    cases = []
    for i, b in enumerate(BORROWERS, start=1):
        cid = f"CR-2026Q3-{i:02d}"
        if cid == CASE["id"]:
            cases.append({"id": cid, "borrower": b, "tester": CASE["tester"], "ratings": CASE["ratings"],
                          "new_money": "Yes", "security": "Secured", "dti": round(DTI, 4), "qualified": "Yes"})
            continue
        new_money = rng.choice(["Yes", "Yes", "No"])
        security = rng.choice(["Secured", "Secured", "Unsecured"])
        ratings = {}
        for n, *_ in QUESTIONS:
            if n == "5.02" and new_money == "No" or n == "6.01" and security == "Unsecured":
                ratings[n] = ("Not applicable", "")
                continue
            r = rng.choices(RATINGS[:3], weights=WEIGHTS[n])[0]
            ratings[n] = (r, rng.choice(COMMENTS[n]) if r != "Effective" else "")
        cases.append({"id": cid, "borrower": b, "tester": TESTERS[i % 3], "ratings": ratings, "new_money": new_money,
                      "security": security, "dti": round(rng.uniform(0.22, 0.48), 4) if new_money == "Yes" else None,
                      "qualified": rng.choice(["Yes", "Yes", "Yes", "No"])})
    return cases


SAMPLE = build_sample()

# ---------------------------------------------------------------- shared print CSS
PAPER_CSS = """
@page{size:letter;margin:16mm 14mm}
*{box-sizing:border-box}
body{margin:0;background:#fff;color:#141414;font:10.5px/1.45 'IBM Plex Sans',system-ui,'Segoe UI',Arial,sans-serif}
.doc{max-width:780px;margin:0 auto;padding:24px}
h1{font:600 20px 'IBM Plex Serif',Georgia,serif;margin:2px 0 0}
h2{font:600 11px 'IBM Plex Sans',Arial,sans-serif;text-transform:uppercase;letter-spacing:.07em;border-bottom:1.5px solid #141414;padding-bottom:3px;margin:18px 0 6px;break-after:avoid}
h3{font-size:11px;margin:10px 0 4px}
.sub{color:#555;font-size:10px}
.kv{display:grid;grid-template-columns:120px 1fr 120px 1fr;gap:2px 12px;margin-top:8px}
.kv dt{color:#555}.kv dd{margin:0}
table{width:100%;border-collapse:collapse;margin:4px 0;break-inside:auto}
th{text-align:left;font-weight:600;border-bottom:1px solid #141414;padding:3px 4px;font-size:9.5px}
td{border-bottom:1px solid #d6d6d6;padding:3px 4px;vertical-align:top}
tr{break-inside:avoid}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.tag{display:inline-block;font-size:9px;font-weight:600;padding:0 5px;border-radius:2px;border:1px solid #141414;white-space:nowrap}
.tag.e{border-color:#1e8c5a;color:#1e6b46}.tag.p{border-color:#a8710f;color:#7d5208}.tag.x{background:#141414;color:#fff}.tag.na{border-color:#999;color:#666}
.box{border:1px solid #141414;padding:8px 10px;margin-top:10px;display:grid;grid-template-columns:repeat(5,1fr);gap:6px}
.box div b{display:block;font-size:16px;font-variant-numeric:tabular-nums}
.box div span{font-size:9px;color:#555;text-transform:uppercase;letter-spacing:.05em}
.calc{background:#f2f4f7;padding:6px 8px;margin:6px 0;border-left:3px solid #141414}
.mono{font-family:'IBM Plex Mono',Menlo,Consolas,monospace;font-size:9.5px;white-space:nowrap}
.nw{white-space:nowrap}
.sig{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:14px}
.sig div{border-top:1px solid #141414;padding-top:4px}
.foot{margin-top:18px;border-top:1px solid #bbb;padding-top:5px;color:#555;font-size:9px}
.bar{display:flex;height:10px;gap:2px;min-width:160px}
.bar i{display:block;height:100%}
.bar i:first-child{border-radius:3px 0 0 3px}.bar i:last-child{border-radius:0 3px 3px 0}
.legend{display:flex;gap:14px;font-size:9.5px;color:#333;margin:4px 0 6px}
.legend span::before{content:"";display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:4px;vertical-align:-1px;background:var(--c)}
"""
FONTS = "<link rel=\"stylesheet\" href=\"https://fonts.googleapis.com/css2?family=IBM+Plex+Mono&family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Serif:wght@600&display=swap\">"
TAG = {"Effective": "e", "Partially effective": "p", "Not effective": "x", "Not applicable": "na"}
COLORS = {"Effective": "#1e8c5a", "Partially effective": "#c98a1b", "Not effective": "#b9443a", "Not applicable": "#c3c8cf"}


def tag(r):
    return f'<span class="tag {TAG[r]}">{E(r)}</span>' if r else '<span class="tag x">Not rated</span>'


# ---------------------------------------------------------------- 1. the workpaper
def workpaper_body(c=CASE):
    rs = c["ratings"]
    counts = {r: sum(1 for v in rs.values() if v[0] == r) for r in RATINGS}
    findings = [(n, q, rs[n]) for n, s, q, _ in QUESTIONS if rs[n][0] in ("Partially effective", "Not effective")]
    rec = record_json()
    h = [f'<div class="sub">{E(ORG)} · Credit file review · {QUARTER} sample</div>',
         f'<h1>{E(c["borrower"])} <span class="sub" style="font:400 11px sans-serif">(synthetic)</span></h1>',
         f'<div class="sub">Case {c["id"]} · <b>{E(c["status"])}</b> {E(c["signed"])}</div>',
         '<dl class="kv">'
         f'<dt>Tester</dt><dd>{E(c["tester"])}</dd><dt>Reviewer</dt><dd>{E(c["reviewer"])}</dd>'
         f'<dt>Review date</dt><dd>{c["review_date"]}</dd><dt>Quarter end</dt><dd>{c["quarter_end"]}</dd>'
         f'<dt>Scope</dt><dd>{E(c["scope"])}</dd><dt>Credit qualified?</dt><dd>{E(c["qualified"])}</dd></dl>',
         '<div class="box">'
         f'<div><b>{len(rs)}</b><span>Questions tested</span></div>'
         + "".join(f'<div><b>{counts[r]}</b><span>{E(r)}</span></div>' for r in RATINGS) + '</div>',
         '<h2>Conclusion</h2>', f'<p style="margin:0">{E(c["summary"])}</p>',
         '<h2>Findings</h2>',
         '<table><thead><tr><th>#</th><th>Question</th><th>Rating</th><th>What the tester found</th></tr></thead><tbody>'
         + "".join(f'<tr><td class="mono">{n}</td><td>{E(q)}</td><td>{tag(r[0])}</td><td>{E(r[1])}</td></tr>' for n, q, r in findings)
         + '</tbody></table>',
         '<h2>Test results</h2>']
    last = None
    rows = []
    for n, s, q, steps in QUESTIONS:
        if s != last:
            rows.append(f'<tr><td colspan="4" style="padding-top:8px;border-bottom:0"><b>{E(s)}</b></td></tr>')
            last = s
        r = rs[n]
        rows.append(f'<tr><td class="mono">{n}</td><td>{E(q)}</td><td>{tag(r[0])}</td><td>{E(r[1]) or "<span class=sub>No comment</span>"}</td></tr>')
    h.append('<table><thead><tr><th style="width:34px">#</th><th>Question</th><th style="width:100px">Rating</th><th>Comment</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>')
    # supporting analysis
    f = c["facilities"]
    h.append('<h2>Supporting analysis</h2><h3>Facilities</h3><table><thead><tr><th>Facility</th><th class="n">Rating</th><th class="n">Commitment</th><th class="n">Outstanding</th></tr></thead><tbody>'
             + "".join(f'<tr><td>{E(a)}</td><td class="n">{b}</td><td class="n">{money(cm)}</td><td class="n">{money(o)}</td></tr>' for a, b, cm, o in f)
             + f'<tr><th>Total</th><th></th><th class="n">{money(sum(x[2] for x in f))}</th><th class="n">{money(sum(x[3] for x in f))}</th></tr></tbody></table>')
    p = c["cashflow_people"]; cf = c["cashflow"]
    h.append('<h3>Owner and guarantor cash flow</h3><table><thead><tr><th></th>' + "".join(f'<th class="n">{E(x)}</th>' for x in p) + '</tr></thead><tbody>'
             f'<tr><td>Adjusted personal income</td>' + "".join(f'<td class="n">{money(v)}</td>' for v in cf["inc"]) + '</tr>'
             f'<tr><td>Existing personal debt payments</td>' + "".join(f'<td class="n">{money(v)}</td>' for v in cf["debt"]) + '</tr>'
             f'<tr><td><i>Left after debt payments</i> <span class="sub">worked out: income − debt</span></td>' + "".join(f'<td class="n"><i>{money(a - b)}</i></td>' for a, b in zip(cf["inc"], cf["debt"])) + '</tr></tbody></table>')
    v = c["valuation"]
    h.append('<h3>Collateral valuation</h3><table><thead><tr><th>Class</th><th class="n">Value</th><th class="n">Advance %</th><th class="n">Adjusted value</th></tr></thead><tbody>'
             + "".join(f'<tr><td>{E(a)}</td><td class="n">{money(b)}</td><td class="n">{p_}%</td><td class="n"><i>{money(b * p_ / 100)}</i></td></tr>' for a, b, p_ in v)
             + f'<tr><th>Total</th><th class="n">{money(sum(x[1] for x in v))}</th><th></th><th class="n">{money(sum(x[1] * x[2] / 100 for x in v))}</th></tr></tbody></table>'
             '<div class="sub">Advance percentages are example values, not policy.</div>')
    d = c["dti"]
    h.append('<h3>Debt-to-income, recomputed by the tester</h3><div class="calc">'
             f'<b>{DTI * 100:.1f}%</b> = ({money(DEBT)} existing + {money(PROP)} proposed) ÷ {money(INC)} monthly income · '
             f'<span class="tag x">Above limit</span> limit {d["limit"] * 100:.0f}% (fictional; confirmed by this organization 2026-10-02)<br>'
             '<span class="sub">Method DTI-DEMO 1.0 (fictional demonstration). Included: '
             + "; ".join(f'{E(a)} {money(x)} {per.lower()}' for a, x, per in d["income"])
             + '. Student loan entered as a zero payment and counted as zero.</span></div>'
             '<div class="sub">The calculation informs question 5.02. It does not set the rating; the tester does.</div>')
    h.append('<h2>Review</h2><table><thead><tr><th>#</th><th>Reviewer asked</th><th>Tester answered</th><th>Status</th></tr></thead><tbody>'
             + "".join(f'<tr><td class="mono">{n}</td><td>{E(q)}<br><span class="sub">{E(by)}</span></td><td>{E(a)}<br><span class="sub">{E(aby)}</span></td><td>{E(st)}</td></tr>' for n, by, q, aby, a, st in c["review_points"])
             + '</tbody></table>')
    h.append(f'<div class="sig"><div>Tested by {E(c["tester"])} · {c["review_date"]}</div><div>Reviewed and signed off by {E(c["reviewer"])} · {c["signed"]}</div></div>')
    h.append(f'<div class="foot">{E(PACK["name"])} {PACK["version"]} ({PACK["fingerprint"]}) · Methods: DTI-DEMO 1.0 · Record fingerprint {rec["fingerprint"]} · '
             'Synthetic data. Methods and limits are fictional demonstrations. Example wording, not any organization\'s policy.</div>')
    return "\n".join(h)


def page(title, body):
    return f"<!doctype html><html lang=en><head><meta charset=utf-8><title>{E(title)}</title>{FONTS}<style>{PAPER_CSS}</style></head><body><div class=doc>{body}</div></body></html>"


# ---------------------------------------------------------------- 2. the record (JSON) and the feed (CSV)
def record_json():
    c = CASE
    rec = {"schema": "workpaper-record/0.1-draft", "contract": "UNVERIFIED example",
           "case": c["id"], "pack": {"name": PACK["name"], "version": PACK["version"]},
           "status": c["status"], "signedOff": c["signed"],
           "fields": {"borrower": {"state": "entered", "value": c["borrower"]}, "tester": {"state": "entered", "value": c["tester"]},
                      "reviewer": {"state": "entered", "value": c["reviewer"]}, "qualified": {"state": "entered", "value": c["qualified"]},
                      "scope": {"state": "entered", "value": c["scope"]}},
           "tables": {"testQuestions": [{"row": n, "applies": True, "rating": {"state": "entered", "value": c["ratings"][n][0]},
                                         "comment": ({"state": "entered", "value": c["ratings"][n][1]} if c["ratings"][n][1] else {"state": "missing", "required": False})}
                                        for n, *_ in QUESTIONS],
                      "facilities": [{"type": a, "rating": b, "commitment": cm, "outstanding": o} for a, b, cm, o in c["facilities"]]},
           "results": [{"method": "DTI-DEMO 1.0", "state": "calculated", "value": round(DTI, 4), "limit": c["dti"]["limit"],
                        "limitConfirmedBy": "this organization", "test": "above limit"}],
           "review": {"points": len(c["review_points"]), "open": 0}}
    rec["fingerprint"] = fingerprint(rec)
    return rec


FEED_COLS = ["case_id", "quarter", "borrower", "tester", "new_money", "secured", "qualified", "dti"] + \
            [f"rating_{n}" for n, *_ in QUESTIONS] + [f"comment_{n}" for n, *_ in QUESTIONS] + ["findings", "_missing"]


def feed_rows():
    rows = []
    for s in SAMPLE:
        r = {"case_id": s["id"], "quarter": QUARTER, "borrower": s["borrower"], "tester": s["tester"], "new_money": s["new_money"],
             "secured": s["security"] == "Secured", "qualified": s["qualified"], "dti": "" if s["dti"] is None else s["dti"]}
        for n, *_ in QUESTIONS:
            r[f"rating_{n}"] = s["ratings"][n][0]
            r[f"comment_{n}"] = s["ratings"][n][1]
        r["findings"] = sum(1 for v in s["ratings"].values() if v[0] in ("Partially effective", "Not effective"))
        r["_missing"] = 0
        rows.append(r)
    return rows


# ---------------------------------------------------------------- 3. the quarter roll-up
def rollup_body():
    n_cases = len(SAMPLE)
    per_q = []
    for n, s, q, _ in QUESTIONS:
        cnt = {r: sum(1 for c in SAMPLE if c["ratings"][n][0] == r) for r in RATINGS}
        tested = n_cases - cnt["Not applicable"]
        rate = cnt["Effective"] / tested if tested else None
        per_q.append((n, s, q, cnt, tested, rate))
    findings = [(c, n, c["ratings"][n]) for c in SAMPLE for n, *_ in QUESTIONS if c["ratings"][n][0] in ("Partially effective", "Not effective")]
    tot_tested = sum(x[4] for x in per_q)
    tot_eff = sum(x[3]["Effective"] for x in per_q)
    worst = min(per_q, key=lambda x: x[5])
    h = [f'<div class="sub">{E(ORG)} · Credit risk review · Quarter roll-up</div>',
         f'<h1>{QUARTER}: {n_cases} credits tested</h1>',
         f'<div class="sub">Built from {n_cases} signed-off workpapers under {E(PACK["name"])} {PACK["version"]}. Every figure links to a case.</div>',
         '<div class="box">'
         f'<div><b>{n_cases}</b><span>Credits tested</span></div>'
         f'<div><b>{tot_tested}</b><span>Questions answered</span></div>'
         f'<div><b>{pct_half_up(tot_eff / tot_tested)}</b><span>Rated effective</span></div>'
         f'<div><b>{len(findings)}</b><span>Findings</span></div>'
         f'<div><b>{sum(1 for c in SAMPLE if c["qualified"] == "No")}</b><span>Not qualified</span></div></div>',
         f'<h2>Where the weaknesses are</h2><p style="margin:0 0 6px">The weakest area this quarter is <b>{E(worst[1].lower())}</b> '
         f'(question {worst[0]}): {worst[3]["Effective"]} of {worst[4]} tested credits were effective.</p>',
         '<div class="legend">' + "".join(f'<span style="--c:{COLORS[r]}">{E(r)}</span>' for r in RATINGS) + '</div>',
         '<table><thead><tr><th>#</th><th>Question</th><th>Results</th><th class="n">Effective</th><th class="n">Partial</th><th class="n">Not effective</th><th class="n">N/A</th><th class="n">Rate</th></tr></thead><tbody>']
    for n, s, q, cnt, tested, rate in per_q:
        bar = "".join(f'<i style="flex:{cnt[r]};background:{COLORS[r]}" title="{E(r)}: {cnt[r]}"></i>' for r in RATINGS if cnt[r])
        h.append(f'<tr><td class="mono">{n}</td><td>{E(q)}</td><td><div class="bar" role="img" aria-label="{n}: '
                 + ", ".join(f"{cnt[r]} {r.lower()}" for r in RATINGS) + f'">{bar}</div></td>'
                 + "".join(f'<td class="n">{cnt[r]}</td>' for r in RATINGS)
                 + f'<td class="n"><b>{pct_half_up(rate)}</b></td></tr>')
    h.append('</tbody></table><div class="sub">Rate = effective ÷ tested. Not applicable is left out of the rate, never counted as effective.</div>')
    h.append('<h2>Findings</h2><table><thead><tr><th>Case</th><th>Borrower</th><th>#</th><th>Rating</th><th>Finding</th><th>Tester</th></tr></thead><tbody>'
             + "".join(f'<tr><td class="mono">{c["id"]}</td><td>{E(c["borrower"])}</td><td class="mono">{n}</td><td>{tag(r[0])}</td><td>{E(r[1])}</td><td class="nw">{E(c["tester"])}</td></tr>' for c, n, r in findings)
             + '</tbody></table>')
    h.append('<div class="foot">Synthetic sample of 12 credits, generated with a fixed seed. Not real results. Example wording, not any organization\'s policy.</div>')
    return "\n".join(h), per_q, findings


# ---------------------------------------------------------------- 4. the workbook (live formulas)
THIN = Side(style="thin", color="BBBBBB")
HDR = PatternFill("solid", fgColor="1F2A37")
INP = PatternFill("solid", fgColor="FFF7E0")
CAL = PatternFill("solid", fgColor="EEF2F7")


def hdr(ws, row, values, widths=None):
    for i, v in enumerate(values, start=1):
        c = ws.cell(row=row, column=i, value=v)
        c.font = Font(bold=True, color="FFFFFF"); c.fill = HDR; c.alignment = Alignment(vertical="center", wrap_text=True)
    if widths:
        for i, w in enumerate(widths, start=1):
            ws.column_dimensions[chr(64 + i)].width = w


def build_workbook(path):
    c = CASE
    wb = Workbook()
    cover = wb.active; cover.title = "Cover"
    cover["A1"] = f"{c['borrower']} (synthetic) · Credit file review"; cover["A1"].font = Font(bold=True, size=14)
    rows = [("Case", c["id"]), ("Status", f"{c['status']} {c['signed']}"), ("Tester", c["tester"]), ("Reviewer", c["reviewer"]),
            ("Review date", c["review_date"]), ("Quarter end", c["quarter_end"]), ("Pack", f"{PACK['name']} {PACK['version']}"),
            ("Credit qualified?", c["qualified"]),
            ("Questions tested", "=COUNTA(Testing!F2:F10)"),
            ("Effective", '=COUNTIF(Testing!F2:F10,"Effective")'),
            ("Partially effective", '=COUNTIF(Testing!F2:F10,"Partially effective")'),
            ("Not effective", '=COUNTIF(Testing!F2:F10,"Not effective")'),
            ("Debt-to-income (recomputed)", "=DTI!B13"),
            ("Note", "Synthetic data. Methods and limits are fictional demonstrations.")]
    for i, (k, v) in enumerate(rows, start=3):
        cover.cell(row=i, column=1, value=k).font = Font(bold=True)
        cover.cell(row=i, column=2, value=v)
    cover["B15"].number_format = "0.0%"
    cover.column_dimensions["A"].width = 30; cover.column_dimensions["B"].width = 60

    t = wb.create_sheet("Testing")
    hdr(t, 1, ["#", "Section", "Question", "How to test", "Applies", "Rating", "Comment"], [7, 18, 46, 46, 9, 20, 50])
    dv = DataValidation(type="list", formula1='"' + ",".join(RATINGS) + '"', allow_blank=True)
    t.add_data_validation(dv)
    for i, (n, s, q, steps) in enumerate(QUESTIONS, start=2):
        r = c["ratings"][n]
        for col, v in enumerate([n, s, q, steps, "Yes", r[0], r[1]], start=1):
            cell = t.cell(row=i, column=col, value=v); cell.alignment = Alignment(wrap_text=True, vertical="top")
        t.cell(row=i, column=6).fill = INP; t.cell(row=i, column=7).fill = INP
        dv.add(f"F{i}")
    t.freeze_panes = "A2"

    f = wb.create_sheet("Facilities")
    hdr(f, 1, ["Facility", "Rating", "Commitment", "Outstanding"], [24, 10, 16, 16])
    for i, (a, b, cm, o) in enumerate(c["facilities"], start=2):
        for col, v in enumerate([a, b, cm, o], start=1):
            f.cell(row=i, column=col, value=v)
    n = len(c["facilities"]) + 1
    f.cell(row=n + 1, column=1, value="Total").font = Font(bold=True)
    for col in ("C", "D"):
        f[f"{col}{n + 1}"] = f"=SUM({col}2:{col}{n})"; f[f"{col}{n + 1}"].fill = CAL
        for r in range(2, n + 2):
            f[f"{col}{r}"].number_format = '"$"#,##0'

    cf = wb.create_sheet("Cash flow")
    hdr(cf, 1, ["Line item"] + c["cashflow_people"], [36, 22, 22])
    labels = ["Adjusted personal income", "Existing personal debt payments", "Left after debt payments (income − debt)"]
    for i, lab in enumerate(labels, start=2):
        cf.cell(row=i, column=1, value=lab)
    for j in range(len(c["cashflow_people"])):
        colL = chr(66 + j)
        cf[f"{colL}2"] = c["cashflow"]["inc"][j]; cf[f"{colL}3"] = c["cashflow"]["debt"][j]
        cf[f"{colL}4"] = f"={colL}2-{colL}3"; cf[f"{colL}4"].fill = CAL
        for r in (2, 3, 4):
            cf[f"{colL}{r}"].number_format = '"$"#,##0'

    v = wb.create_sheet("Collateral")
    hdr(v, 1, ["Class", "Value", "Advance %", "Adjusted value"], [22, 16, 12, 18])
    for i, (a, b, p) in enumerate(c["valuation"], start=2):
        v.cell(row=i, column=1, value=a); v.cell(row=i, column=2, value=b); v.cell(row=i, column=3, value=p)
        v[f"D{i}"] = f"=B{i}*C{i}/100"; v[f"D{i}"].fill = CAL
    n = len(c["valuation"]) + 1
    v.cell(row=n + 1, column=1, value="Total").font = Font(bold=True)
    v[f"B{n + 1}"] = f"=SUM(B2:B{n})"; v[f"D{n + 1}"] = f"=SUM(D2:D{n})"
    for r in range(2, n + 2):
        v[f"B{r}"].number_format = '"$"#,##0'; v[f"D{r}"].number_format = '"$"#,##0'
    v.cell(row=n + 3, column=1, value="Advance percentages are example values, not policy.")

    d = wb.create_sheet("DTI")
    hdr(d, 1, ["Income source", "Amount", "Per", "Monthly"], [30, 14, 10, 14])
    for i, (a, x, per) in enumerate(c["dti"]["income"], start=2):
        d.cell(row=i, column=1, value=a); d.cell(row=i, column=2, value=x); d.cell(row=i, column=3, value=per)
        d[f"D{i}"] = f'=IF(C{i}="Annual",B{i}/12,B{i})'; d[f"D{i}"].fill = CAL
    d["A6"] = "Existing debt"; d["B6"] = "Monthly payment"; d["A6"].font = d["B6"].font = Font(bold=True)
    for i, (a, x) in enumerate(c["dti"]["debts"], start=7):
        d.cell(row=i, column=1, value=a); d.cell(row=i, column=2, value=x)
    d["A11"] = "Proposed monthly payment"; d["B11"] = c["dti"]["proposed"]
    d["A12"] = "Monthly income"; d["B12"] = "=SUM(D2:D4)"; d["B12"].fill = CAL
    d["A13"] = "Debt-to-income"; d["B13"] = "=(SUM(B7:B9)+B11)/B12"; d["B13"].fill = CAL; d["B13"].number_format = "0.0%"
    d["A14"] = "Limit (fictional; confirmed by this organization)"; d["B14"] = c["dti"]["limit"]; d["B14"].number_format = "0%"
    d["A15"] = "Result"; d["B15"] = '=IF(B13<=B14,"Within limit","Above limit")'; d["B15"].fill = CAL
    d["A17"] = "Method DTI-DEMO 1.0 (fictional demonstration). Worked out by the method; the tester sets the rating."

    fd = wb.create_sheet("Findings")
    hdr(fd, 1, ["#", "Question", "Rating", "What the tester found"], [7, 50, 20, 60])
    i = 2
    for n_, s, q, _ in QUESTIONS:
        r = c["ratings"][n_]
        if r[0] in ("Partially effective", "Not effective"):
            for col, val in enumerate([n_, q, r[0], r[1]], start=1):
                fd.cell(row=i, column=col, value=val).alignment = Alignment(wrap_text=True, vertical="top")
            i += 1

    rv = wb.create_sheet("Review log")
    hdr(rv, 1, ["#", "Reviewer asked", "By", "Tester answered", "By", "Status"], [7, 44, 12, 52, 12, 10])
    for i, row in enumerate(c["review_points"], start=2):
        for col, val in enumerate(row, start=1):
            rv.cell(row=i, column=col, value=val).alignment = Alignment(wrap_text=True, vertical="top")

    fe = wb.create_sheet("Feed")
    row = next(r for r in feed_rows() if r["case_id"] == c["id"])
    hdr(fe, 1, FEED_COLS)
    for j, k in enumerate(FEED_COLS, start=1):
        fe.cell(row=2, column=j, value=row[k])
    wb.save(path)


# ---------------------------------------------------------------- write everything
def main():
    rec = record_json()
    (OUT / f"{CASE['id']}-workpaper.html").write_text(page(f"{CASE['id']} workpaper", workpaper_body()))
    rb, per_q, findings = rollup_body()
    (OUT / f"rollup-{QUARTER}.html").write_text(page(f"{QUARTER} roll-up", rb))
    (OUT / f"{CASE['id']}.record.json").write_text(json.dumps(rec, indent=2))
    with open(OUT / f"feed-{QUARTER}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FEED_COLS); w.writeheader(); [w.writerow(r) for r in feed_rows()]
    build_workbook(OUT / f"{CASE['id']}.xlsx")
    # fragments the showcase page embeds, so the page shows exactly what the files contain
    frag = {"workpaper": workpaper_body(), "rollup": rb, "record": rec, "feed_cols": FEED_COLS, "feed": feed_rows(),
            "case": {k: CASE[k] for k in ("id", "borrower", "tester", "reviewer", "ratings", "review_points")},
            "questions": QUESTIONS, "dti": {"inc": INC, "debt": DEBT, "proposed": PROP, "value": DTI},
            "sample": [{"id": s["id"], "borrower": s["borrower"], "tester": s["tester"],
                        "findings": sum(1 for v in s["ratings"].values() if v[0] in ("Partially effective", "Not effective"))} for s in SAMPLE],
            "paper_css": PAPER_CSS}
    (OUT / "fragments.json").write_text(json.dumps(frag, indent=1))
    print("wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main()
