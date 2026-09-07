"""A full engagement, start to finish, through the REAL app.

    satc app                       # or however you start it
    PYTHONPATH=src python scripts/demo_arc.py

Every step is an HTTP request to the running Flask app against the real SQLite
store. No test doubles, no fixtures written directly, no importing the engine
and asking it nicely — what prints is what the screens actually say.

WHY THIS EXISTS ALONGSIDE 1200 TESTS. Every store test builds its own temporary
database, which means the MIGRATION PATH has no coverage at all, by
construction: a column added to the DDL and not to _migrate works in every test
and fails on every real install. This found exactly that, in under a minute,
while the suite was entirely green — the invoice row saved, its lines did not,
and what stayed in the register was a bill for 0.00 against work that had been
done.

So point it at a database WITH A HISTORY. That is the whole value; a fresh one
tells you what the tests already told you.
"""
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from http.cookiejar import CookieJar

B = "http://127.0.0.1:5055"
jar = CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def get(path):
    with op.open(B + path) as r:
        return r.read().decode("utf-8", "replace")


def post(path, **data):
    body = urllib.parse.urlencode(data).encode()
    try:
        with op.open(urllib.request.Request(B + path, data=body)) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.read().decode("utf-8", "replace")


def text(html):
    """Strip tags so we can read what the screen says."""
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def step(n, title):
    print(f"\n{'=' * 78}\n{n}. {title}\n{'=' * 78}")


def show(label, html, *phrases):
    body = text(html)
    for p in phrases:
        hit = p in body
        print(f"   {'OK ' if hit else '-- '} {label}: {p[:66]}")


# --------------------------------------------------------------------------
step(1, "A NEW CLIENT ARRIVES")
page = post("/clients/quick-add", name="Marisol Trent", tin="412-55-9087",
            entity_type="INDIVIDUAL", email="marisol@example.com", state="MA")
cid = re.search(r"SATC-\d+", text(page))
cid = cid.group(0) if cid else ""
print(f"   client created: {cid}")

# --------------------------------------------------------------------------
step(2, "THE INTERVIEW → THE WHOLE ENGAGEMENT IT IMPLIES")
plan = get(f"/intake/plan?client={cid}&workflow=personal_1040_core&tax_year=2025"
           "&q_brokerageActivity=yes&q_stateReturnNeeded=yes"
           "&q_marketplaceInsurance=yes&q_expectedK1s=yes")
body = text(plan)

for label, needle in [
    ("deadline is computed from a cited rule", "STATUTE"),
    ("the firm cutoff is marked as NOT law", "FIRM POLICY"),
    ("a quote, marked an estimate", "ESTIMATE"),
    ("documents split by what actually blocks prep", "Blocks starting prep"),
]:
    print(f"   {'OK ' if needle in body else '-- '} {label}")

money = re.findall(r"\d[\d,]*\.\d\d", body)
print(f"   figures on the plan: {money[:6]}")
due = re.search(r"(January|February|March|April|May|June|July|August|September|"
                r"October|November|December) \d{1,2}, 20\d\d", body)
print(f"   deadline it computed: {due.group(0) if due else 'none'}")

# --------------------------------------------------------------------------
step(3, "GENERATE IT — and press the button twice on purpose")
before = len(re.findall(r"/work/", get("/work")))
post("/intake/new", client=cid, workflow_key="personal_1040_core", tax_year="2025",
     due_date="2031-12-25",                      # a typed date, to be ignored
     q_brokerageActivity="yes", q_stateReturnNeeded="yes",
     q_marketplaceInsurance="yes", q_expectedK1s="yes")
post("/intake/new", client=cid, workflow_key="personal_1040_core", tax_year="2025",
     q_brokerageActivity="yes", q_stateReturnNeeded="yes",
     q_marketplaceInsurance="yes", q_expectedK1s="yes")

jobs = re.findall(r'/work/([A-Za-z0-9\-]+)"', get("/work"))
print(f"   jobs on the board after TWO presses of Generate: {len(set(jobs))}")
print(f"   the typed 2031 date was {'IGNORED' if '2031' not in text(get('/work')) else 'USED'}")

# --------------------------------------------------------------------------
step(4, "THE WORK QUEUE — what can I pick up right now")
work = text(get("/work"))
head = re.search(r"(\d+ job[^.]*\.)", work)
print(f"   headline: {head.group(1) if head else work[:110]}")
for phrase in ["Workable now", "Waiting on you", "Waiting on clients"]:
    print(f"   {'OK ' if phrase in work else '-- '} section: {phrase}")
why = re.search(r"(Ready to start[^.]*\.|is still outstanding[^.]*\.)", work)
print(f"   a row's stated reason: {why.group(1)[:100] if why else '—'}")

# --------------------------------------------------------------------------
step(5, "RAISE THE BILL — and try to give a discount with no reason")
post("/invoices/new", action="header", client_id=cid, tax_year="2025",
     plan_key="household", plan_basis="")
post("/invoices/new", action="add", service_code="return_1040", quantity="1")
post("/invoices/new", action="add", service_code="schedule_d", quantity="1")
draft = text(get("/invoices/new"))
nums = re.findall(r"\d[\d,]*\.\d\d", draft)
print(f"   running total on the build screen: {nums[:5]}")

# Off the issue button itself, not the first thing on the page that looks like
# a number — a date matched that pattern and issued a different invoice.
number = re.search(r"Issue invoice (20\d\d-\d{4})", draft)
number = number.group(1) if number else ""
print(f"   draft number: {number}")
refused = text(post(f"/invoices/{number}/issue", issued_on=date.today().isoformat()))
print(f"   {'OK ' if 'recorded reason' in refused else '-- '} "
      f"refused a reduced rate with no basis, on the page")

post("/invoices/new", action="header", client_id=cid, tax_year="2025",
     plan_key="household", plan_basis="Single income household, W-2 only")
issued = post(f"/invoices/{number}/issue", issued_on=date.today().isoformat())
inv = text(get(f"/invoices/{number}"))
for phrase in ["Full value of work", "Household rate applied", "TOTAL DUE"]:
    print(f"   {'OK ' if phrase in inv else '-- '} the client sees: {phrase}")

# --------------------------------------------------------------------------
step(6, "MONEY ARRIVES — a part payment, then the rest")
post(f"/invoices/{number}/paid", amount="200.00",
     received_on=date.today().isoformat(), method="check", reference="cheque 4471")
part = text(get(f"/invoices/{number}"))
owed = re.search(r"outstanding[^\d]*([\d,]+\.\d\d)", part, re.I)
print(f"   after a part payment, still outstanding: {owed.group(1) if owed else '?'}")
print(f"   {'OK ' if 'Paid in full' not in part else '-- '} not reported as settled")

# a payment dated before the invoice existed
bad = text(post(f"/invoices/{number}/paid", amount="100.00",
                received_on="1999-02-14", method="check"))
print(f"   {'OK ' if 'before invoice' in bad or 'has not happened' in bad else '-- '} "
      f"a 1999 payment date is refused")

# --------------------------------------------------------------------------
step(7, "RECORD THAT THE RETURN WENT OUT")
jobs = re.findall(r"/work/([A-Za-z0-9\-]+)\"", get("/work"))
job_id = jobs[0] if jobs else ""
post(f"/work/{job_id}/delivered", kind="return_for_review", channel="portal",
     delivered_on=date.today().isoformat(), return_key=f"{cid}-2025-1040")
jobpage = text(get(f"/work/{job_id}"))
print(f"   {'OK ' if 'Sent the draft return' in jobpage else '-- '} "
      f"the delivery is recorded and named")

# --------------------------------------------------------------------------
step(8, "DRAFT THE COVERING EMAIL — filled from everything above")
mail = text(get(f"/comms?client={cid}&template=invoice_cover&tax_year=2025"
                f"&invoice={number}"))
print(f"   drafting the cover for invoice {number}")
print(f"   {'OK ' if number in mail else '-- '} quotes THIS invoice ({number})")
print(f"   {'OK ' if 'DRAFT' in mail.upper() else '-- '} marked a draft, not sent")
unfilled = re.findall(r"\[\[ ?([^\]]{3,40}) ?\]\]", mail)
print(f"   slots left visibly unfilled: {unfilled[:4] or 'none'}")

print(f"\n{'=' * 78}\nEverything above ran against the live app on {B}.\n{'=' * 78}")
