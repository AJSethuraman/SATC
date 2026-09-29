# The 2027 season, simulated -- seed 7

60 invented clients driven day by day from 2027-01-01 to 2027-10-15 (288 days, 288 of them read and checked) through the real satc_system routes and client-documents commands. Billing door this seed: **client_documents**. Repository 7ddb58e6, Python 3.12.10, PYTHONHASHSEED 0, wall time 1127.5 s.

**335 findings** from 50 invariants (17 invariant groups hit). 1358 door calls, 8 of them refused or failed (listed under their findings). Checker crashes: 0.

Every name, email and reference below is invented: `Testclient <word> NNN`, `@example.invalid`. Nothing here is a real client.

## Clear bugs (116 findings, 6 rules)

The code contradicts a rule written in this repository, and the fix is local.

### C5 -- the board and the job page agree on a job's stage

*failure* · 54 client(s) · first seen 2027-01-01 · held on up to 258 checked day(s)

**Rule.** S3: two halves of one tool make the same call. The board passes no delivery (queue.py:559); the job page does (work_views.py:280).

**Source.** `docs/SOFTWARE-TENETS.md:103`; `satc_system/src/satc/work/queue.py:559`; `satc_system/src/satc/app/work_views.py:280`

**Note.** expected to fail once a delivery is recorded

- **seed 7 · 2027-01-01 · SIM-004** (engagement-5773a0b67c22576a) -- last seen 2027-10-15, 210 day(s)
  - call: `{"clock": "frozen@2027-01-01T14:00Z", "door": "http", "target": "GET /work/engagement-5773a0b67c22576a", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `GET /work lists it as not_started; GET /work/engagement-5773a0b67c22576a shows 'delivered'`
  - expected: one stage
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-01 --client SIM-004 --check C5`
- **seed 7 · 2027-01-01 · SIM-006** (engagement-36c0a37e9eb87ee0) -- last seen 2027-10-15, 219 day(s)
  - call: `{"clock": "frozen@2027-01-01T14:00Z", "door": "http", "target": "GET /work/engagement-36c0a37e9eb87ee0", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `GET /work lists it as not_started; GET /work/engagement-36c0a37e9eb87ee0 shows 'delivered'`
  - expected: one stage
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-01 --client SIM-006 --check C5`
- **seed 7 · 2027-01-01 · SIM-008** (engagement-8ee5f167535ee7cf) -- last seen 2027-10-15, 212 day(s)
  - call: `{"clock": "frozen@2027-01-01T14:00Z", "door": "http", "target": "GET /work/engagement-8ee5f167535ee7cf", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `GET /work lists it as not_started; GET /work/engagement-8ee5f167535ee7cf shows 'delivered'`
  - expected: one stage
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-01 --client SIM-008 --check C5`
- ... and 51 more: SIM-011, SIM-014, SIM-021, SIM-022, SIM-024, SIM-027, SIM-030, SIM-032, SIM-035, SIM-037, SIM-040, SIM-041, SIM-042, SIM-044, SIM-045, SIM-048, SIM-049, SIM-053, SIM-057, SIM-058, SIM-059, SIM-026 ...

### E6 -- an ended engagement is not shown as due

*failure* · 27 client(s) · first seen 2027-01-01 · held on up to 288 checked day(s)

**Rule.** A disengaged or closed-out engagement has nothing due; showing it OVERDUE on the season board is a confident wrong answer and noise (principles 5, 13).

**Source.** `docs/DESIGN-PRINCIPLES.md:64-74`; `docs/DESIGN-PRINCIPLES.md:235-243`; `client-documents/deadlines.py:414`

**Note.** H4 in the brief

- **seed 7 · 2027-01-01 · SIM-004** (2026-0004) -- last seen 2027-10-15, 288 day(s)
  - call: `{"clock": "frozen@2027-01-01T14:00Z", "door": "cli", "target": "cli.main(['season', ...])", "today_arg": "2027-01-01"}`
  - output: `2026-0004: papers due in 2026-03-25 OVERDUE (closed out)`
  - expected: off the board
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-01 --client SIM-004 --check E6`
- **seed 7 · 2027-01-01 · SIM-006** (2026-0006) -- last seen 2027-10-15, 288 day(s)
  - call: `{"clock": "frozen@2027-01-01T14:00Z", "door": "cli", "target": "cli.main(['season', ...])", "today_arg": "2027-01-01"}`
  - output: `2026-0006: papers due in 2026-03-25 OVERDUE (closed out)`
  - expected: off the board
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-01 --client SIM-006 --check E6`
- **seed 7 · 2027-01-01 · SIM-008** (2026-0008) -- last seen 2027-10-15, 288 day(s)
  - call: `{"clock": "frozen@2027-01-01T14:00Z", "door": "cli", "target": "cli.main(['season', ...])", "today_arg": "2027-01-01"}`
  - output: `2026-0008: papers due in 2026-03-25 OVERDUE (closed out)`
  - expected: off the board
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-01 --client SIM-008 --check E6`
- ... and 24 more: SIM-011, SIM-014, SIM-021, SIM-022, SIM-024, SIM-027, SIM-030, SIM-032, SIM-035, SIM-037, SIM-040, SIM-041, SIM-042, SIM-044, SIM-045, SIM-048, SIM-049, SIM-053, SIM-057, SIM-058, SIM-059, SIM-009

### B11 -- a client with nothing started for the year is invited

*failure* · 23 client(s) · first seen 2027-01-05 · held on up to 284 checked day(s)

**Rule.** interview_invite means 'a client with no engagement for the year'. A client with no job, no request and no document for the working year gets one. (S31: a claim and its behaviour are two things.)

**Source.** `satc_system/src/satc/actions/propose.py:44`; `satc_system/src/satc/app/today_views.py:86`; `docs/SOFTWARE-TENETS.md:706`

**Note.** expected to fail (H8): /today passes every job in ANY year as engaged

- **seed 7 · 2027-01-05 · SIM-004** (SATC-005000) -- last seen 2027-02-11, 38 day(s)
  - call: `{"clock": "frozen@2027-01-05T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `no interview_invite; the client has jobs only for [2025]`
  - expected: 'Nothing started for 2026'
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-05 --client SIM-004 --check B11`
- **seed 7 · 2027-01-05 · SIM-006** (SATC-006000) -- last seen 2027-02-01, 28 day(s)
  - call: `{"clock": "frozen@2027-01-05T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `no interview_invite; the client has jobs only for [2025]`
  - expected: 'Nothing started for 2026'
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-05 --client SIM-006 --check B11`
- **seed 7 · 2027-01-05 · SIM-008** (SATC-007000) -- last seen 2027-02-10, 37 day(s)
  - call: `{"clock": "frozen@2027-01-05T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `no interview_invite; the client has jobs only for [2025]`
  - expected: 'Nothing started for 2026'
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-05 --client SIM-008 --check B11`
- ... and 20 more: SIM-011, SIM-014, SIM-021, SIM-022, SIM-024, SIM-027, SIM-032, SIM-035, SIM-037, SIM-040, SIM-041, SIM-042, SIM-044, SIM-045, SIM-048, SIM-049, SIM-053, SIM-057, SIM-058, SIM-059

### L1 -- a document the process calls for can pass its own gate

*failure* · 8 client(s) · first seen 2027-04-08 · held on up to 1 checked day(s)

**Rule.** The pre-send gate refuses documents that are wrong. A lifecycle document built from a valid payload -- here the extension notice, whose template defines a no-payment branch ('the exact inverse of PaymentEnclosed') -- passes it. S6: the template's conditions and the gate's floors are two lists that must agree.

**Source.** `satc-handoff/04-TEMPLATES/FIELDS - Extension Notice.md:54`; `satc-handoff/04-TEMPLATES/FIELDS - Extension Notice.md:68`; `satc-handoff/04-TEMPLATES/SATC Extension Notice.html:75-81`; `client-documents/registry/required.yaml:60-66`; `docs/SOFTWARE-TENETS.md:150`

- **seed 7 · 2027-04-08 · SIM-001** (2027-0001) -- last seen 2027-04-08, 1 day(s)
  - call: `{"args": {"argv": ["event", "--kind", "extension", "--engagement", "2027-0001", "--answers", "<RUN>/answers/event-extension-2027-0001.json", "--skip-render", "--no-pdf", "--out", "<RUN>/out", "--store", "<RUN>/engagements"]}, "clock": "frozen@2027-04-08T14:00Z", "door": "cli", "status": 1, "target": "cli.main", "today_arg": "2027-04-08"}`
  - output: `cli event --kind extension on 2027-04-08: REFUSED BY THE PRE-SEND GATE -- compliance [SAT-C Extension Notice - 001 - 2026.html]: the compliance floor 'estimate-is-not-final-liability' is not on the page — none of ['final liability', 'not the final'] appears. The extension payment figure is made from an incomplete file. Saying so is what stops a client treating it as the bill.`
  - expected: the extension document passes the gate
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-001 --check L1`
- **seed 7 · 2027-04-08 · SIM-003** (2027-0003) -- last seen 2027-04-08, 1 day(s)
  - call: `{"args": {"argv": ["event", "--kind", "extension", "--engagement", "2027-0003", "--answers", "<RUN>/answers/event-extension-2027-0003.json", "--skip-render", "--no-pdf", "--out", "<RUN>/out", "--store", "<RUN>/engagements"]}, "clock": "frozen@2027-04-08T14:00Z", "door": "cli", "status": 1, "target": "cli.main", "today_arg": "2027-04-08"}`
  - output: `cli event --kind extension on 2027-04-08: REFUSED BY THE PRE-SEND GATE -- compliance [SAT-C Extension Notice - 003 - 2026.html]: the compliance floor 'estimate-is-not-final-liability' is not on the page — none of ['final liability', 'not the final'] appears. The extension payment figure is made from an incomplete file. Saying so is what stops a client treating it as the bill.`
  - expected: the extension document passes the gate
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-003 --check L1`
- **seed 7 · 2027-04-08 · SIM-012** (2027-0012) -- last seen 2027-04-08, 1 day(s)
  - call: `{"args": {"argv": ["event", "--kind", "extension", "--engagement", "2027-0012", "--answers", "<RUN>/answers/event-extension-2027-0012.json", "--skip-render", "--no-pdf", "--out", "<RUN>/out", "--store", "<RUN>/engagements"]}, "clock": "frozen@2027-04-08T14:00Z", "door": "cli", "status": 1, "target": "cli.main", "today_arg": "2027-04-08"}`
  - output: `cli event --kind extension on 2027-04-08: REFUSED BY THE PRE-SEND GATE -- compliance [SAT-C Extension Notice - 012 - 2026.html]: the compliance floor 'estimate-is-not-final-liability' is not on the page — none of ['final liability', 'not the final'] appears. The extension payment figure is made from an incomplete file. Saying so is what stops a client treating it as the bill.`
  - expected: the extension document passes the gate
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-012 --check L1`
- ... and 5 more: SIM-035, SIM-041, SIM-044, SIM-047, SIM-051

### D4 -- an ended engagement is not chased for signatures

*failure* · 3 client(s) · first seen 2027-03-02 · held on up to 228 checked day(s)

**Rule.** Principle 13: a queue that becomes noise is worse than no queue. An engagement that is disengaged or closed out has nothing left to sign for.

**Source.** `docs/DESIGN-PRINCIPLES.md:235-243`; `client-documents/signing.py:612-647`

**Note.** H5 in the brief

- **seed 7 · 2027-03-02 · SIM-055** (2027-0055) -- last seen 2027-10-15, 228 day(s)
  - call: `{"clock": "frozen@2027-03-02T14:00Z", "door": "function", "target": "signing.waiting", "today_arg": "2027-03-02"}`
  - output: `signing.waiting lists 2027-0055 (disengaged) missing ['Form 8879/TaxpayerName', 'Form 8879/SpouseName']`
  - expected: not listed
  - repro: `python -m season_sim repro --seed 7 --until 2027-03-02 --client SIM-055 --check D4`
- **seed 7 · 2027-03-15 · SIM-045** (2027-0045) -- last seen 2027-10-15, 215 day(s)
  - call: `{"clock": "frozen@2027-03-15T14:00Z", "door": "function", "target": "signing.waiting", "today_arg": "2027-03-15"}`
  - output: `signing.waiting lists 2027-0045 (disengaged) missing ['Form 8879/TaxpayerName']`
  - expected: not listed
  - repro: `python -m season_sim repro --seed 7 --until 2027-03-15 --client SIM-045 --check D4`
- **seed 7 · 2027-03-24 · SIM-052** (2027-0052) -- last seen 2027-10-15, 206 day(s)
  - call: `{"clock": "frozen@2027-03-24T14:00Z", "door": "function", "target": "signing.waiting", "today_arg": "2027-03-24"}`
  - output: `signing.waiting lists 2027-0052 (disengaged) missing ['Form 8879/TaxpayerName', 'Form 8879/SpouseName']`
  - expected: not listed
  - repro: `python -m season_sim repro --seed 7 --until 2027-03-24 --client SIM-052 --check D4`

### K1 -- an explicit --today governs the whole read

*failure* · 1 client(s) · first seen 2027-01-01 · held on up to 12 checked day(s)

**Rule.** `cli season --today D` answers for D. Run under a wrong machine clock with an explicit --today, it must print what it prints under the right one.

**Source.** `client-documents/cli.py:3082`; `client-documents/deadlines.py:414-434`; `client-documents/deadlines.py:395`

**Note.** checked by the clock-leak audit on sample days (H11)

- **seed 7 · 2027-01-01 · -** (cli season) -- last seen 2027-10-15, 12 day(s)
  - call: `{"clock": "frozen@2031-06-15T14:00Z vs frozen@2027-01-01T14:00Z", "door": "cli", "target": "cli.main(['season', '--today', D, '--store', S])", "today_arg": "2027-01-01"}`
  - output: `cli season --today 2027-01-01 printed differently when the machine clock was wrong. First difference: clock on the day: '!! 2026-03-25  OVERDUE  2026-0004  Testclient Delta 004           papers due in' | clock on 2031-06-15: '  nothing due in that window.'`
  - expected: identical output: --today D alone decides the answer
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-01 --check K1`

## Needs the firm's decision (211 findings, 10 rules)

A gap whose fix is a choice: a door to build (D8 deferred one), a policy to pick, or a reading of a rule the firm has to confirm.

### G4 -- the papers-due date matches what the client was told

*cross_store* · 57 client(s) · first seen 2027-01-05 · held on up to 284 checked day(s)

**Rule.** The letter tells the client 'we need your complete information by <<MaterialsDeadline>>' (client-documents, set 26 Aug 2026). satc_system's cutoff drives its extension flag. Where they differ the owner is flagged to extend a client who is still inside the date they were given. Whether the cutoff is an engagement term is the firm's call.

**Source.** `LOG.md:847`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:79`; `client-documents/registry/firm-settings.yaml:114`; `satc_system/configs/firm_policy.yaml:34-39`

- **seed 7 · 2027-01-05 · SIM-005** (2027-0005) -- last seen 2027-10-15, 284 day(s)
  - call: `{"clock": "frozen@2027-01-05T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-01-05"}`
  - output: `satc documents_due 2027-02-01 (firm_policy cutoff); client told February 22, 2027`
  - expected: the same date
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-05 --client SIM-005 --check G4`
- **seed 7 · 2027-01-05 · SIM-030** (2027-0030) -- last seen 2027-10-15, 284 day(s)
  - call: `{"clock": "frozen@2027-01-05T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-01-05"}`
  - output: `satc documents_due 2027-03-01 (firm_policy cutoff); client told March 25, 2027`
  - expected: the same date
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-05 --client SIM-030 --check G4`
- **seed 7 · 2027-01-06 · SIM-042** (2027-0042) -- last seen 2027-10-15, 283 day(s)
  - call: `{"clock": "frozen@2027-01-06T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-01-06"}`
  - output: `satc documents_due 2027-03-01 (firm_policy cutoff); client told March 25, 2027`
  - expected: the same date
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-06 --client SIM-042 --check G4`
- ... and 54 more: SIM-045, SIM-056, SIM-026, SIM-016, SIM-021, SIM-037, SIM-003, SIM-013, SIM-055, SIM-058, SIM-033, SIM-035, SIM-041, SIM-060, SIM-038, SIM-046, SIM-007, SIM-012, SIM-015, SIM-034, SIM-043, SIM-053 ...

### G6 -- both systems know whether the bill is paid

*cross_store* · 50 client(s) · first seen 2027-02-04 · held on up to 254 checked day(s)

**Rule.** D3 settles invoice numbering in client-documents. 'We will not e-file a return before the invoice for it is settled' is gated by client-documents alone; Today's money rows read satc_system's invoices alone. Whichever door bills, the other system cannot see it.

**Source.** `LOG.md:847-854`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:95`; `client-documents/signing.py:541-572`; `satc_system/src/satc/app/today_views.py:81-96`

- **seed 7 · 2027-02-04 · SIM-037** (2027-0037) -- last seen 2027-10-15, 254 day(s)
  - call: `{"clock": "frozen@2027-02-04T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-02-04"}`
  - output: `2027-0037 billed as 2027-0001 in client-documents; satc_system holds no invoice for 2026`
  - expected: Today's money rows know the bill exists
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-04 --client SIM-037 --check G6`
- **seed 7 · 2027-02-04 · SIM-042** (2027-0042) -- last seen 2027-10-15, 254 day(s)
  - call: `{"clock": "frozen@2027-02-04T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-02-04"}`
  - output: `2027-0042 billed as 2027-0002 in client-documents; satc_system holds no invoice for 2026`
  - expected: Today's money rows know the bill exists
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-04 --client SIM-042 --check G6`
- **seed 7 · 2027-02-04 · SIM-057** (2027-0057) -- last seen 2027-10-15, 254 day(s)
  - call: `{"clock": "frozen@2027-02-04T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-02-04"}`
  - output: `2027-0057 billed as 2027-0003 in client-documents; satc_system holds no invoice for 2026`
  - expected: Today's money rows know the bill exists
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-04 --client SIM-057 --check G6`
- ... and 47 more: SIM-026, SIM-030, SIM-015, SIM-027, SIM-056, SIM-013, SIM-016, SIM-049, SIM-005, SIM-046, SIM-038, SIM-033, SIM-014, SIM-034, SIM-060, SIM-007, SIM-053, SIM-018, SIM-059, SIM-023, SIM-009, SIM-010 ...

### G8 -- no extension flag while the client is inside the date they were told

*cross_store* · 39 client(s) · first seen 2027-02-02 · held on up to 24 checked day(s)

**Rule.** The client was told 'we need your complete information by <<MaterialsDeadline>>'. Today proposes a likely extension from the day after satc's own cutoff. Before the told date, that row is about a client who is not late (H2).

**Source.** `LOG.md:847`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:79`; `satc_system/src/satc/actions/propose.py:254-280`; `satc_system/configs/firm_policy.yaml:34-39`

- **seed 7 · 2027-02-02 · SIM-005** (extension_candidate/SATC-029000/2026) -- last seen 2027-02-22, 21 day(s)
  - call: `{"clock": "frozen@2027-02-02T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[urgent] Likely extension — 1065 2026 -- Your cutoff was Feb 01 and 4 items are still outstanding. An extension needs the client's written authorisation before you file it. (client told February 22, 2027)`
  - expected: no extension flag before February 22, 2027
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-02 --client SIM-005 --check G8`
- **seed 7 · 2027-02-02 · SIM-015** (extension_candidate/SATC-042000/2026) -- last seen 2027-02-10, 9 day(s)
  - call: `{"clock": "frozen@2027-02-02T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[urgent] Likely extension — 1120S 2026 -- Your cutoff was Feb 01 and 2 items are still outstanding. An extension needs the client's written authorisation before you file it. (client told February 22, 2027)`
  - expected: no extension flag before February 22, 2027
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-02 --client SIM-015 --check G8`
- **seed 7 · 2027-02-02 · SIM-016** (extension_candidate/SATC-032000/2026) -- last seen 2027-02-18, 17 day(s)
  - call: `{"clock": "frozen@2027-02-02T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[urgent] Likely extension — 1065 2026 -- Your cutoff was Feb 01 and 3 items are still outstanding. An extension needs the client's written authorisation before you file it. (client told February 22, 2027)`
  - expected: no extension flag before February 22, 2027
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-02 --client SIM-016 --check G8`
- ... and 36 more: SIM-026, SIM-033, SIM-001, SIM-002, SIM-003, SIM-004, SIM-006, SIM-008, SIM-009, SIM-010, SIM-011, SIM-012, SIM-017, SIM-019, SIM-020, SIM-021, SIM-023, SIM-024, SIM-025, SIM-028, SIM-029, SIM-031 ...

### B13 -- the prior-year question does not ask for a new-client-only document

*failure* · 21 client(s) · first seen 2027-01-05 · held on up to 284 checked day(s)

**Rule.** The 1040 workflow asks for prior-year returns only when newSatcClient is 'yes'. For a returning client that document is not an omission, so a row asking where it went is noise the owner learns to scroll past (principle 13).

**Source.** `satc_system/configs/workflows/personal_1040_core.yaml:170-176`; `satc_system/src/satc/actions/propose.py:180-200`; `satc_system/src/satc/rollover/diff.py:111-138`; `docs/DESIGN-PRINCIPLES.md:235-243`

- **seed 7 · 2027-01-05 · SIM-030** (prior_year_question/SATC-014000/2026) -- last seen 2027-10-15, 284 day(s)
  - call: `{"clock": "frozen@2027-01-05T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[soon] Ask about 1 document not seen this year -- Prior-year return was on file for 2025 with nothing for 2026 — not even requested.`
  - expected: no question about ['Prior-year return']: the workflow asks it of new clients only
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-05 --client SIM-030 --check B13`
- **seed 7 · 2027-01-06 · SIM-042** (prior_year_question/SATC-020000/2026) -- last seen 2027-10-15, 283 day(s)
  - call: `{"clock": "frozen@2027-01-06T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[soon] Ask about 2 documents not seen this year -- Brokerage 1099, Prior-year return were on file for 2025 with nothing for 2026 — not even requested.`
  - expected: no question about ['Prior-year return']: the workflow asks it of new clients only
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-06 --client SIM-042 --check B13`
- **seed 7 · 2027-01-06 · SIM-045** (prior_year_question/SATC-022000/2026) -- last seen 2027-10-15, 283 day(s)
  - call: `{"clock": "frozen@2027-01-06T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[soon] Ask about 1 document not seen this year -- Prior-year return was on file for 2025 with nothing for 2026 — not even requested.`
  - expected: no question about ['Prior-year return']: the workflow asks it of new clients only
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-06 --client SIM-045 --check B13`
- ... and 18 more: SIM-021, SIM-037, SIM-058, SIM-035, SIM-041, SIM-053, SIM-027, SIM-057, SIM-059, SIM-049, SIM-006, SIM-024, SIM-044, SIM-014, SIM-011, SIM-008, SIM-040, SIM-004

### L4 -- a payment made another way can be recorded

*failure* · 14 client(s) · first seen 2027-02-18 · held on up to 1 checked day(s)

**Rule.** The filing gate's refusal says 'a bill paid another way is recorded by hand', and the invoice tells the client 'If you would rather pay another way, tell us and we will arrange it.' A check that arrived must have a door that records it; otherwise the gate blocks transmitting that return for good (S31: a claim and its behaviour are two things).

**Source.** `client-documents/signing.py:564-570`; `client-documents/registry/firm-settings.yaml:100-102`; `client-documents/payments.py:622-634`; `client-documents/cli.py:859-900`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:95`; `docs/SOFTWARE-TENETS.md:706`

**Note.** H13 in the brief. Only CHECK payers are counted: a card payment would settle through Square, which the simulator is not allowed to reach

- **seed 7 · 2027-02-18 · SIM-037** (2027-0037) -- last seen 2027-02-18, 1 day(s)
  - call: `{"clock": "frozen@2027-02-18T14:00Z", "door": "cli", "target": "(none exists) -- cli.py payments asks Square only", "today_arg": "2027-02-18"}`
  - output: `check received 2027-02-18 for invoice 2027-0001 on 2027-0037: no command records it (cli.py offers 'payments', which asks Square). may_file still says: 1 of 1 invoice(s) on this engagement are not recorded as settled — 2027-0001. Every engagement letter says we will not e-file before the invoice is settled. 'python cli.py payments' asks the processor; a bill paid anothe`
  - expected: a door that records the check, so the gate can clear
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-18 --client SIM-037 --check L4`
- **seed 7 · 2027-03-01 · SIM-013** (2027-0013) -- last seen 2027-03-01, 1 day(s)
  - call: `{"clock": "frozen@2027-03-01T14:00Z", "door": "cli", "target": "(none exists) -- cli.py payments asks Square only", "today_arg": "2027-03-01"}`
  - output: `check received 2027-02-28 for invoice 2027-0010 on 2027-0013: no command records it (cli.py offers 'payments', which asks Square). may_file still says: 1 of 1 invoice(s) on this engagement are not recorded as settled — 2027-0010. Every engagement letter says we will not e-file before the invoice is settled. 'python cli.py payments' asks the processor; a bill paid anothe`
  - expected: a door that records the check, so the gate can clear
  - repro: `python -m season_sim repro --seed 7 --until 2027-03-01 --client SIM-013 --check L4`
- **seed 7 · 2027-03-01 · SIM-030** (2027-0030) -- last seen 2027-03-01, 1 day(s)
  - call: `{"clock": "frozen@2027-03-01T14:00Z", "door": "cli", "target": "(none exists) -- cli.py payments asks Square only", "today_arg": "2027-03-01"}`
  - output: `check received 2027-03-01 for invoice 2027-0005 on 2027-0030: no command records it (cli.py offers 'payments', which asks Square). may_file still says: 1 of 1 invoice(s) on this engagement are not recorded as settled — 2027-0005. Every engagement letter says we will not e-file before the invoice is settled. 'python cli.py payments' asks the processor; a bill paid anothe`
  - expected: a door that records the check, so the gate can clear
  - repro: `python -m season_sim repro --seed 7 --until 2027-03-01 --client SIM-030 --check L4`
- ... and 11 more: SIM-046, SIM-060, SIM-005, SIM-034, SIM-054, SIM-050, SIM-008, SIM-043, SIM-036, SIM-051, SIM-003

### B8 -- a deadline row is dated at the operative deadline

*failure* · 11 client(s) · first seen 2027-04-16 · held on up to 183 checked day(s)

**Rule.** 'The operative deadline -- extended when an extension is on file.' A client whose return is extended, filed, or whose engagement has ended must not be told the original due date has passed (principle 5: a confident wrong answer). The facts are on file in client-documents; satc_system has no door to receive them (H14).

**Source.** `satc_system/src/satc/obligations/due_dates.py:109-110`; `docs/DESIGN-PRINCIPLES.md:64-74`

**Note.** expected to fail (H1): build_queue has no input for filed, extended or disengaged

- **seed 7 · 2027-04-16 · SIM-001** (deadline_approaching/SATC-061000/1040-2026) -- last seen 2027-10-15, 183 day(s)
  - call: `{"clock": "frozen@2027-04-16T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[overdue] 1040 for 2026 was due Apr 15 -- US 1040, 2026: overdue by 1 days.`
  - expected: no 'overdue' against the original date: client-documents records 2027-0001 as extended
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-16 --client SIM-001 --check B8`
- **seed 7 · 2027-04-16 · SIM-003** (deadline_approaching/SATC-033000/1040-2026) -- last seen 2027-10-15, 183 day(s)
  - call: `{"clock": "frozen@2027-04-16T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[overdue] 1040 for 2026 was due Apr 15 -- US 1040, 2026: overdue by 1 days.`
  - expected: no 'overdue' against the original date: client-documents records 2027-0003 as extended
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-16 --client SIM-003 --check B8`
- **seed 7 · 2027-04-16 · SIM-012** (deadline_approaching/SATC-041000/1040-2026) -- last seen 2027-10-15, 183 day(s)
  - call: `{"clock": "frozen@2027-04-16T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[overdue] 1040 for 2026 was due Apr 15 -- US 1040, 2026: overdue by 1 days.`
  - expected: no 'overdue' against the original date: client-documents records 2027-0012 as extended
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-16 --client SIM-012 --check B8`
- ... and 8 more: SIM-035, SIM-041, SIM-044, SIM-045, SIM-047, SIM-051, SIM-052, SIM-055

### L3 -- an extension notice can restate what the extension changed

*failure* · 8 client(s) · first seen 2027-04-08 · held on up to 1 checked day(s)

**Rule.** The package check refuses a first-deliverable target earlier than the materials deadline. An extension moves the materials deadline past the target promised at the interview, and the extension event carries no field to restate the target -- so every extension notice is refused. The letter commits the firm to filing extensions where needed.

**Source.** `client-documents/consistency.py:313-345`; `satc-handoff/04-TEMPLATES/SATC Engagement Letter - Tax Preparation.html:83`; `client-documents/registry/lifecycle.yaml`

- **seed 7 · 2027-04-08 · SIM-001** (2027-0001) -- last seen 2027-04-08, 1 day(s)
  - call: `{"args": {"argv": ["event", "--kind", "extension", "--engagement", "2027-0001", "--answers", "<RUN>/answers/event-extension-2027-0001.json", "--skip-render", "--no-pdf", "--out", "<RUN>/out", "--store", "<RUN>/engagements"]}, "clock": "frozen@2027-04-08T14:00Z", "door": "cli", "status": 1, "target": "cli.main", "today_arg": "2027-04-08"}`
  - output: `cli event --kind extension on 2027-04-08: REFUSED BY THE PRE-SEND GATE -- agrees [(pack)]: the first deliverable is not promised before the materials are due — the first deliverable is promised for April 8, 2027, which is before the August 16, 2027 date the same package tells the client to send everything by`
  - expected: the extension document passes the gate
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-001 --check L3`
- **seed 7 · 2027-04-08 · SIM-003** (2027-0003) -- last seen 2027-04-08, 1 day(s)
  - call: `{"args": {"argv": ["event", "--kind", "extension", "--engagement", "2027-0003", "--answers", "<RUN>/answers/event-extension-2027-0003.json", "--skip-render", "--no-pdf", "--out", "<RUN>/out", "--store", "<RUN>/engagements"]}, "clock": "frozen@2027-04-08T14:00Z", "door": "cli", "status": 1, "target": "cli.main", "today_arg": "2027-04-08"}`
  - output: `cli event --kind extension on 2027-04-08: REFUSED BY THE PRE-SEND GATE -- agrees [(pack)]: the first deliverable is not promised before the materials are due — the first deliverable is promised for April 8, 2027, which is before the August 16, 2027 date the same package tells the client to send everything by`
  - expected: the extension document passes the gate
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-003 --check L3`
- **seed 7 · 2027-04-08 · SIM-012** (2027-0012) -- last seen 2027-04-08, 1 day(s)
  - call: `{"args": {"argv": ["event", "--kind", "extension", "--engagement", "2027-0012", "--answers", "<RUN>/answers/event-extension-2027-0012.json", "--skip-render", "--no-pdf", "--out", "<RUN>/out", "--store", "<RUN>/engagements"]}, "clock": "frozen@2027-04-08T14:00Z", "door": "cli", "status": 1, "target": "cli.main", "today_arg": "2027-04-08"}`
  - output: `cli event --kind extension on 2027-04-08: REFUSED BY THE PRE-SEND GATE -- agrees [(pack)]: the first deliverable is not promised before the materials are due — the first deliverable is promised for April 8, 2027, which is before the August 16, 2027 date the same package tells the client to send everything by`
  - expected: the extension document passes the gate
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-012 --check L3`
- ... and 5 more: SIM-035, SIM-041, SIM-044, SIM-047, SIM-051

### G5 -- what client-documents records, satc_system reflects

*cross_store* · 7 client(s) · first seen 2027-03-15 · held on up to 215 checked day(s)

**Rule.** D3 splits the engagement from the return. An extension, disengagement or close-out recorded in client-documents should stop satc_system asking for the same client's documents or proposing an extension. There is no door that carries the fact across (H14).

**Source.** `LOG.md:847`; `satc_system/src/satc/actions/__init__.py:96-98`

- **seed 7 · 2027-03-15 · SIM-045** (prior_year_question/SATC-022000/2026) -- last seen 2027-10-15, 215 day(s)
  - call: `{"clock": "frozen@2027-03-15T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[soon] Ask about 2 documents not seen this year -- 1099-R / 5498, Prior-year return were on file for 2025 with nothing for 2026 — not even requested.`
  - expected: no prior_year_question row: 2027-0045 is disengaged in client-documents
  - repro: `python -m season_sim repro --seed 7 --until 2027-03-15 --client SIM-045 --check G5`
- **seed 7 · 2027-04-08 · SIM-001** (extension_candidate/SATC-061000/2026) -- last seen 2027-10-15, 191 day(s)
  - call: `{"clock": "frozen@2027-04-08T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[urgent] Likely extension — 1040 2026 -- Your cutoff was Mar 01 and 4 items are still outstanding. An extension needs the client's written authorisation before you file it.`
  - expected: no extension_candidate row: 2027-0001 is already extended in client-documents
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-001 --check G5`
- **seed 7 · 2027-04-08 · SIM-003** (extension_candidate/SATC-033000/2026) -- last seen 2027-07-11, 95 day(s)
  - call: `{"clock": "frozen@2027-04-08T14:00Z", "door": "http", "target": "GET /today", "today_arg": "(none: the route reads date.today(), frozen)"}`
  - output: `[urgent] Likely extension — 1040 2026 -- Your cutoff was Mar 01 and 1 item is still outstanding. An extension needs the client's written authorisation before you file it.`
  - expected: no extension_candidate row: 2027-0003 is already extended in client-documents
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-003 --check G5`
- ... and 4 more: SIM-012, SIM-035, SIM-041, SIM-047

### E5 -- an amended return is not placed at the original return's dates

*failure* · 2 client(s) · first seen 2027-02-01 · held on up to 257 checked day(s)

**Rule.** An amended return is a refund claim with its own clock (IRC 6511(a), deadlines.py). Placing it at the original return's filing dates, already past, is principle 5: a confident wrong answer.

**Source.** `client-documents/deadlines.py:348-356`; `docs/DESIGN-PRINCIPLES.md:64-74`

**Note.** H6 in the brief; plausible rather than certain

- **seed 7 · 2027-02-01 · SIM-009** (2027-0109) -- last seen 2027-10-15, 257 day(s)
  - call: `{"clock": "frozen@2027-02-01T14:00Z", "door": "cli", "target": "cli.main(['season', ...])", "today_arg": "2027-02-01"}`
  - output: `2027-0109: papers due in 2026-03-25 OVERDUE (-313 days)`
  - expected: no original-return deadline on an amended return
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-01 --client SIM-009 --check E5`
- **seed 7 · 2027-02-01 · SIM-030** (2027-0130) -- last seen 2027-10-15, 257 day(s)
  - call: `{"clock": "frozen@2027-02-01T14:00Z", "door": "cli", "target": "cli.main(['season', ...])", "today_arg": "2027-02-01"}`
  - output: `2027-0130: papers due in 2026-03-25 OVERDUE (-313 days)`
  - expected: no original-return deadline on an amended return
  - repro: `python -m season_sim repro --seed 7 --until 2027-02-01 --client SIM-030 --check E5`

### G1 -- each ref names exactly one satc engagement

*cross_store* · 2 client(s) · first seen 2027-01-06 · held on up to 283 checked day(s)

**Rule.** D3: 'client-documents owns the engagement; satc_system holds the return.' Each engaged ref has one satc Engagement carrying it, and client_for_ref resolves to the paired client.

**Source.** `LOG.md:847`; `satc_system/src/satc/persistence/store.py:701-721`; `satc_system/tests/test_the_join_has_a_writer.py`

- **seed 7 · 2027-01-06 · SIM-056** (2027-0056) -- last seen 2027-10-15, 283 day(s)
  - call: `{"clock": "frozen@2027-01-06T14:00Z", "door": "function", "target": "SATCStore.client_for_ref", "today_arg": "2027-01-06"}`
  - output: `2027-0056: satc engagements carrying it: none satc_system has no workflow for this return, so there is no job to carry the ref`
  - expected: exactly [SATC-030000]
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-06 --client SIM-056 --check G1`
- **seed 7 · 2027-01-19 · SIM-046** (2027-0046) -- last seen 2027-10-15, 270 day(s)
  - call: `{"clock": "frozen@2027-01-19T14:00Z", "door": "function", "target": "SATCStore.client_for_ref", "today_arg": "2027-01-19"}`
  - output: `2027-0046: satc engagements carrying it: none satc_system has no workflow for this return, so there is no job to carry the ref`
  - expected: exactly [SATC-039000]
  - repro: `python -m season_sim repro --seed 7 --until 2027-01-19 --client SIM-046 --check G1`

## Known, reproduced (8 findings, 1 rule)

Already recorded as a known gap. Reproduced here through the doors, not new.

### E7 -- an extended engagement is shown at its extended date

*known* · 8 client(s) · first seen 2027-04-08 · held on up to 191 checked day(s)

**Rule.** board() emits materials and filing milestones only, never extended; the firm chose 'Date only for now'. Reproduced, not new.

**Source.** `client-documents/deadlines.py:197-202`; `canon/corpus/decisions-in-their-words.md:123-125`

- **seed 7 · 2027-04-08 · SIM-001** (2027-0001) -- last seen 2027-10-15, 191 day(s)
  - call: `{"clock": "frozen@2027-04-08T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-04-08"}`
  - output: `2027-0001: papers due in 2027-03-25 OVERDUE (extended)`
  - expected: the extended date
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-001 --check E7`
- **seed 7 · 2027-04-08 · SIM-003** (2027-0003) -- last seen 2027-10-15, 191 day(s)
  - call: `{"clock": "frozen@2027-04-08T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-04-08"}`
  - output: `2027-0003: papers due in 2027-03-25 OVERDUE (extended)`
  - expected: the extended date
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-003 --check E7`
- **seed 7 · 2027-04-08 · SIM-012** (2027-0012) -- last seen 2027-10-15, 191 day(s)
  - call: `{"clock": "frozen@2027-04-08T14:00Z", "door": "function", "target": "(read pass)", "today_arg": "2027-04-08"}`
  - output: `2027-0012: papers due in 2027-03-25 OVERDUE (extended)`
  - expected: the extended date
  - repro: `python -m season_sim repro --seed 7 --until 2027-04-08 --client SIM-012 --check E7`
- ... and 5 more: SIM-035, SIM-041, SIM-044, SIM-047, SIM-051

## Labelled what-if (not a finding of this run)

H3. No door records a Filing (D8), so `derive_stage` was asked directly what it would say about SIM-002's delivered job if a Filing with ack `a` ("extension accepted") were on file. It answered stage **complete**: "Accepted by the IRS on Apr 15, 2027." (`is_accepted` = True). An accepted extension is not an accepted return (models/filing.py:42, :53; work/stage.py:96-119). Nothing was written.

## Observations (no recorded rule; never failures)

- **Working year before the first 2026 request.** Today worked on 4 checked day(s) against the prior year (first day on 2026: 2027-01-05); overdue rows on those days: [24, 24, 24, 24]. `working_tax_year`'s docstring says it exists so deadlines do not read as wildly overdue (today_views.py:31-35).
- **Two chase thresholds.** /documents lists a request after 1 day, Today chases after 3 (chasing.py:197; propose.py:151): 655 client-days across 55 clients were on one list and not the other.
- **Signature rows.** `signature_outstanding` rows across the season: 0 -- no workflow opens an 8879 request (H10), while client-documents held 45 fully signed 2026 e-file authorizations (G7; satc says the fact is not one it follows, sla.py:231-237).
- **The Work queue against a real March.** Job-days by stage: {'in_prep': 1, 'not_started': 14607, 'prep_ready': 11, 'ready_to_deliver': 9728}. Days nothing was workable while returns were in preparation: 54. No tax workflow (1040, 1065, 1120-S, Schedule C) plans an internal task, so a tax job is never workable; the owner here prepared earliest-statutory-deadline first (an assumption), which /work never offered.
  - 2027-01-01: 0 workable, 24 not. -
  - 2027-02-01: 1 workable, 63 not. #1 SIM-031 new_client_onboarding 0.067
  - 2027-03-01: 0 workable, 92 not. -
  - 2027-03-15: 0 workable, 92 not. -
  - 2027-04-01: 0 workable, 92 not. -
  - 2027-04-15: 0 workable, 92 not. -
  - 2027-05-01: 0 workable, 92 not. -
  - 2027-06-01: 0 workable, 92 not. -
  - 2027-07-01: 0 workable, 92 not. -
  - 2027-08-01: 0 workable, 92 not. -
  - 2027-09-01: 0 workable, 92 not. -
  - 2027-10-01: 0 workable, 92 not. -
- **Ready to deliver, never proposed.** 9728 job-days at `ready_to_deliver` on the board, by workflow {'new_client_onboarding': 8942, 'personal_rental_schedule_e': 786}; `deliver_return` is declared and nothing produces it (propose.py:45). The simulated owner records delivery for the return's jobs, never for onboarding, so onboarding jobs sit here once their tasks are ticked -- satc has no other way to call a job finished.
- **Sitting untouched.** 5513 job-days idle 14+ days by the firm's own `stale_after_days` (firm_policy.yaml:71-74), by stage {'not_started': 3325, 'ready_to_deliver': 2188}; most: [['SIM-055', 526], ['SIM-047', 500], ['SIM-052', 478], ['SIM-001', 470], ['SIM-003', 338]]. Tax jobs are never workable (no internal tasks), so the idle factor never ranks them.
- **Delivered against closed out.** 50 returns delivered, 0 closed out as filed through `cli.py close` (the only 'filed' door, and only once `may_file` is clear). Payments the clients made that no door could record: 50 (14 of them checks; the rest were card payments that only Square could report, and the simulator may not reach Square).
- **Ticked with no completion record.** 114 tasks toggled done through the UI carry no completion time (H9; state.py:911-919), so the idle factor and the unbilled age never see that work.
- **What blocks.** Request classes opened for 2026: {'1095-A -> non_blocking': 8, '1099-R / 5498 -> non_blocking': 18, 'Asset acquisition or disposition documents -> non_blocking': 2, 'Brokerage 1099 -> non_blocking': 22, 'Capital contribution and distribution detail -> non_blocking': 2, 'Core income documents -> non_blocking': 50, 'Engagement letter -> non_blocking': 34, 'Expense records -> non_blocking': 3, 'Improvement invoices -> non_blocking': 3, 'Intake questionnaire -> non_blocking': 34, 'K-1 -> expected_late': 4, 'Kickoff call scheduling -> non_blocking': 34, 'Mortgage interest and property tax statements -> non_blocking': 3, 'Personal-use day confirmation -> non_blocking': 3, 'Prior-year return -> non_blocking': 63, 'Rent roll -> non_blocking': 3, 'Shareholder W-2 and payroll support -> non_blocking': 3, 'Shareholder distribution detail -> non_blocking': 3, 'Trial balance -> non_blocking': 5, 'Welcome email -> non_blocking': 34} (H7: nothing on a 1040 plan blocks prep).
- **SLAs at season end.** measurable: ['efile_reject_turnaround']; unmeasurable: ['first_response: client_message_received', 'notice_turnaround: notice_response_sent', 'return_turnaround: documents_complete', 'signature_acknowledged: authorization_signed']; Filings on file in satc: 0, so the e-file reject clock has nothing to read.
- **K-1 lag.** Partnership delivered to dependent 1040 delivered: [('SIM-010', 13), ('SIM-017', 28), ('SIM-021', 13), ('SIM-060', 7)]. Cross-job dependencies are modelled nowhere (docs/BRIEFING.md:212).
- **Facts with no door.** {'no_door: client-documents has no door to record it without Square': 50, 'no_door: satc_system has no door for it': 11, 'no_satc_workflow: Form 1120: satc_system has no workflow to hold this return (satc/intake/fanout.py:117)': 2}
- **Refused door calls.** 8 (each belongs to a finding above or is listed here): 2027-04-08 SIM-001 cli.main -> 1; 2027-04-08 SIM-003 cli.main -> 1; 2027-04-08 SIM-012 cli.main -> 1; 2027-04-08 SIM-035 cli.main -> 1; 2027-04-08 SIM-041 cli.main -> 1; 2027-04-08 SIM-044 cli.main -> 1

- **Clock-leak audit.** 12 sample days, 6 reads each, run under the simulated clock and again under 2031-06-15 with `today=` passed. Reads that changed: ['cli season --today D', 'deadlines.board(today=D)'].

## What the simulator did NOT cover

- No document was read. `run_intake` (folder scanning, classification, OCR, the reader ladder) was never driven; every arrival was recorded with the Received button on /documents.
- No document was opened. Every client-documents event ran with `--skip-render --no-pdf`; the pre-send gate still ran (its refusals are findings L1 and L3), but no page was rendered or looked at.
- No money moved and no processor was asked. Square, the Windows credential store, sockets and desktop Outlook were replaced with refusals; `cli.py payments` was never run, so a client-documents invoice can never be settled here (that absence is itself H13).
- No Filing, extension, disengagement or 8879 request exists in satc_system, because no front door writes them (H14; D8 for the Filing). The accepted-extension stage (H3) was asked of the pure function in a labelled what-if, never written.
- State returns, payroll, 1099s, estimated payments and Massachusetts duties never reach Today: client profiles are not persisted, so every client gets the default federal profile (today_views.py:43-50). Estimates were deliberately not simulated (the firm: "drake has voucher generation").
- Fiscal-year filers, Patriots' Day and disaster postponements are not modelled by client-documents (deadlines.py:56-59) and were not simulated.
- Only the client-documents CLI was driven, never its browser front door (web.py). satc_system's comms, drafting, withholding, staging, autonomy and MCP surfaces were not driven.
- Today's per-session 'dismiss' was never pressed.
- The owner's behaviour is a small set of assumptions (scenario.yaml `owner:`); a different owner would produce a different season. Holidays were not modelled in the owner's working days.
- Cross-job K-1 links cannot be recorded in satc_system (no route calls `add_relationship`), so the K-1 dependency lives only in the simulated world.
- One invoice line per return was billed in satc_system (the engagement price as one line, as the refusal instructs); the payments ledger's record-and-match door (/payments/record, /match) was not used, only /invoices/<id>/paid.

## Denominators

| invariant | examined (sum over days) | days checked | days with anything to check | findings |
|---|---|---|---|---|
| A1 | 61396 | 288 | 288 | 0 |
| A2 | 15064 | 288 | 284 | 0 |
| A3 | 1152 | 288 | 288 | 0 |
| B1 | 34732 | 288 | 288 | 0 |
| B2 | 34732 | 288 | 288 | 0 |
| B3 | 34732 | 288 | 288 | 0 |
| B4 | 34732 | 288 | 288 | 0 |
| B5 | 288 | 288 | 288 | 0 |
| B6 | 3149 | 288 | 281 | 0 |
| B7 | 16240 | 288 | 285 | 0 |
| B8 | 12353 | 288 | 245 | 11 |
| B9 | 13091 | 288 | 249 | 0 |
| B10 | 11123 | 288 | 284 | 0 |
| B11 | 1809 | 288 | 284 | 23 |
| B12 | 2304 | 288 | 288 | 0 |
| B13 | 6816 | 288 | 284 | 21 |
| C1 | 24347 | 288 | 288 | 0 |
| C2 | 12 | 288 | 8 | 0 |
| C3 | 24347 | 288 | 288 | 0 |
| C4 | 0 | 288 | 0 | 0 |
| C5 | 24347 | 288 | 288 | 54 |
| C6 | 12 | 288 | 8 | 0 |
| C7 | 5 | 288 | 3 | 0 |
| C8 | 12 | 288 | 8 | 0 |
| C9 | 3 | 288 | 3 | 0 |
| D1 | 109000 | 288 | 288 | 0 |
| D2 | 10438 | 288 | 283 | 0 |
| D3 | 5646 | 288 | 284 | 0 |
| D4 | 5646 | 288 | 284 | 3 |
| E1 | 22490 | 288 | 288 | 0 |
| E2 | 44980 | 288 | 288 | 0 |
| E3 | 44980 | 288 | 288 | 0 |
| E4 | 288 | 288 | 288 | 0 |
| E5 | 1028 | 288 | 257 | 2 |
| E6 | 16078 | 288 | 288 | 27 |
| E7 | 3056 | 288 | 191 | 8 |
| F1 | 22490 | 288 | 288 | 0 |
| F2 | 22490 | 288 | 288 | 0 |
| F3 | 22490 | 288 | 288 | 0 |
| G1 | 15064 | 288 | 284 | 2 |
| G2 | 15064 | 288 | 284 | 0 |
| G4 | 15064 | 288 | 284 | 57 |
| G5 | 10352 | 288 | 284 | 7 |
| G6 | 10891 | 288 | 254 | 50 |
| G8 | 1643 | 288 | 251 | 39 |
| K1 | 12 | 300 | 12 | 1 |
| L1 | 8 | 288 | 1 | 8 |
| L2 | 0 | 288 | 0 | 0 |
| L3 | 8 | 288 | 1 | 8 |
| L4 | 14 | 288 | 12 | 14 |

A row with 0 in the fourth column examined nothing this seed: it neither passed nor failed.

## Run-level guards

- banned_call_attempts: 0
- cd_default_store_untouched: True
- cd_out_untouched: True
- env_pinned_at_end: True
- store_is_run_dir: True
- worktree_unchanged: True
- banned doors: socket.socket, socket.create_connection, payments.processor, payments._remembered, square_setup.stored_token, email_draft.open_outlook_draft, email_draft.outlook_available
- shadowed modules resolved inside client-documents: ['requests.py', 'packaging.py']

## Outcomes by archetype

| archetype | clients | delivered | extended | disengaged | closed out as filed |
|---|---|---|---|---|---|
| amended | 2 | 2 | 0 | 0 | 0 |
| ccorp | 2 | 2 | 0 | 0 | 0 |
| disengages | 3 | 0 | 0 | 3 | 0 |
| extension | 5 | 5 | 2 | 0 | 0 |
| goes_quiet | 4 | 0 | 4 | 0 | 0 |
| joint_spouse_missing | 2 | 2 | 0 | 0 | 0 |
| k1_gated | 4 | 4 | 0 | 0 | 0 |
| late_docs | 6 | 6 | 2 | 0 | 0 |
| missing_8879 | 3 | 3 | 0 | 0 | 0 |
| never_reengages | 3 | 0 | 0 | 0 | 0 |
| on_time | 16 | 16 | 0 | 0 | 0 |
| partnership | 2 | 2 | 0 | 0 | 0 |
| rental | 3 | 3 | 0 | 0 | 0 |
| requote | 2 | 2 | 0 | 0 | 0 |
| scorp | 3 | 3 | 0 | 0 | 0 |

Reproduce this report: `python -m season_sim run --seed 7 --report` (from `season-simulator/`, with the venv active).
