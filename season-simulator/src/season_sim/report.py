"""The report: findings first, then observations, then what was NOT covered.

Built from a run's own output files (findings.jsonl, summary.json, world.json),
never from memory, so a report can be rebuilt from a kept run at any time.

Every finding carries: seed, simulated date, fake client, the call that was
made, what came back, and the rule it breaks with its citation. Observations
are never called failures.
"""

from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

from season_sim import paths

SECTION = [("clear_bug", "Clear bugs",
            "The code contradicts a rule written in this repository, and the fix is local."),
           ("firm_decision", "Needs the firm's decision",
            "A gap whose fix is a choice: a door to build (D8 deferred one), a policy to "
            "pick, or a reading of a rule the firm has to confirm."),
           ("known", "Known, reproduced",
            "Already recorded as a known gap. Reproduced here through the doors, not new.")]

NOT_COVERED = [
    "No document was read. `run_intake` (folder scanning, classification, OCR, the "
    "reader ladder) was never driven; every arrival was recorded with the Received "
    "button on /documents.",
    "No document was opened. Every client-documents event ran with `--skip-render "
    "--no-pdf`; the pre-send gate still ran (its refusals are findings L1 and L3), but "
    "no page was rendered or looked at.",
    "No money moved and no processor was asked. Square, the Windows credential store, "
    "sockets and desktop Outlook were replaced with refusals; `cli.py payments` was never "
    "run, so a client-documents invoice can never be settled here (that absence is itself "
    "H13).",
    "No Filing, extension, disengagement or 8879 request exists in satc_system, because "
    "no front door writes them (H14; D8 for the Filing). The accepted-extension stage "
    "(H3) was asked of the pure function in a labelled what-if, never written.",
    "State returns, payroll, 1099s, estimated payments and Massachusetts duties never "
    "reach Today: client profiles are not persisted, so every client gets the default "
    "federal profile (today_views.py:43-50). Estimates were deliberately not simulated "
    "(the firm: \"drake has voucher generation\").",
    "Fiscal-year filers, Patriots' Day and disaster postponements are not modelled by "
    "client-documents (deadlines.py:56-59) and were not simulated.",
    "Only the client-documents CLI was driven, never its browser front door (web.py). "
    "satc_system's comms, drafting, withholding, staging, autonomy and MCP surfaces were "
    "not driven.",
    "Today's per-session 'dismiss' was never pressed.",
    "The owner's behaviour is a small set of assumptions (scenario.yaml `owner:`); a "
    "different owner would produce a different season. Holidays were not modelled in "
    "the owner's working days.",
    "Cross-job K-1 links cannot be recorded in satc_system (no route calls "
    "`add_relationship`), so the K-1 dependency lives only in the simulated world.",
    "One invoice line per return was billed in satc_system (the engagement price as "
    "one line, as the refusal instructs); the payments ledger's record-and-match door "
    "(/payments/record, /match) was not used, only /invoices/<id>/paid.",
]


def _load(out: Path):
    rows = [json.loads(line) for line in (out / "findings.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    timings = json.loads((out / "timings.json").read_text(encoding="utf-8")) \
        if (out / "timings.json").exists() else {}
    return rows, summary, timings


def _group(rows):
    from season_sim.decisions import decision_for
    by = defaultdict(list)
    for r in rows:
        by[r["invariant"]].append(r)
    out = defaultdict(list)
    for code, rs in by.items():
        rs.sort(key=lambda r: (r["first_seen"], r["sim_client"]))
        out[decision_for(code)].append((code, rs))
    for k in out:
        out[k].sort(key=lambda x: (-len(x[1]), x[0]))
    return out


def _code(s: str) -> str:
    return "`" + str(s).replace("`", "'") + "`"


def markdown(out: Path) -> str:
    rows, s, timings = _load(out)
    seed = s["seed"]
    groups = _group(rows)
    L = []
    add = L.append
    total = len(rows)
    add(f"# The 2027 season, simulated -- seed {seed}")
    add("")
    add(f"{s['clients']} invented clients driven day by day from {s['window'][0]} to "
        f"{s['window'][1]} ({s['days']} days, {s['days_read']} of them read and checked) "
        f"through the real satc_system routes and client-documents commands. Billing door "
        f"this seed: **{s['billing_door']}**. Repository {s['env'].get('repo_sha') or '?'}, "
        f"Python {s['env']['python']}, PYTHONHASHSEED {s['env']['pythonhashseed']}"
        + (f", wall time {timings.get('wall_seconds')} s" if timings else "") + ".")
    add("")
    add(f"**{total} findings** from {len(s['invariants'])} invariants "
        f"({sum(len(v) for v in groups.values())} invariant groups hit). "
        f"{s['door_calls']['total']} door calls, "
        f"{sum(s['door_calls']['not_ok'].values())} of them refused or failed (listed under "
        f"their findings). Checker crashes: {len(s['checker_crashes'])}.")
    add("")
    add("Every name, email and reference below is invented: `Testclient <word> NNN`, "
        "`@example.invalid`. Nothing here is a real client.")
    add("")
    for key, title, blurb in SECTION:
        items = groups.get(key, [])
        add(f"## {title} ({sum(len(r) for _, r in items)} findings, {len(items)} rules)")
        add("")
        add(blurb)
        add("")
        if not items:
            add("None this seed.")
            add("")
        for code, rs in items:
            r0 = rs[0]
            clients = sorted({r['sim_client'] for r in rs})
            add(f"### {code} -- {r0['invariant_name']}")
            add("")
            add(f"*{r0['kind']}* · {len(clients)} client(s) · first seen {r0['first_seen']} · "
                f"held on up to {max(r['days'] for r in rs)} checked day(s)")
            add("")
            add(f"**Rule.** {r0['rule']}")
            add("")
            add("**Source.** " + "; ".join(_code(x) for x in r0["source"]))
            if r0.get("note"):
                add("")
                add(f"**Note.** {r0['note']}")
            add("")
            for r in rs[:3]:
                add(f"- **seed {seed} · {r['first_seen']} · {r['sim_client']}**"
                    + (f" ({r['subject']})" if r["subject"] and r["subject"] != r["sim_client"] else "")
                    + f" -- last seen {r['last_seen']}, {r['days']} day(s)")
                add(f"  - call: {_code(json.dumps(r['call'], sort_keys=True))}")
                add(f"  - output: {_code(r['output'][:600])}")
                add(f"  - expected: {r['expected_per_source']}")
                add(f"  - repro: {_code(r['repro'])}")
            if len(rs) > 3:
                add(f"- ... and {len(rs) - 3} more: {', '.join(r['sim_client'] for r in rs[3:25])}"
                    + (" ..." if len(rs) > 28 else ""))
            add("")

    add("## Labelled what-if (not a finding of this run)")
    add("")
    w = s.get("what_if_H3") or {}
    if w.get("ran"):
        add(f"H3. No door records a Filing (D8), so `derive_stage` was asked directly what it "
            f"would say about {w.get('sim')}'s delivered job if a Filing with ack "
            f"`{w['filing']['ack_code']}` (\"extension accepted\") were on file. It answered "
            f"stage **{w['stage']}**: \"{w['why']}\" (`is_accepted` = {w['is_accepted']}). "
            f"An accepted extension is not an accepted return (models/filing.py:42, :53; "
            f"work/stage.py:96-119). Nothing was written.")
    else:
        add(f"Not run: {w}")
    add("")

    o = s.get("observations") or {}
    add("## Observations (no recorded rule; never failures)")
    add("")
    wy = o.get("working_year_before_2026", {})
    add(f"- **Working year before the first 2026 request.** Today worked on "
        f"{wy.get('days')} checked day(s) against the prior year (first day on 2026: "
        f"{wy.get('first_2026_day')}); overdue rows on those days: "
        f"{wy.get('overdue_rows_on_those_days')}. `working_tax_year`'s docstring says it "
        f"exists so deadlines do not read as wildly overdue (today_views.py:31-35).")
    tv = o.get("today_vs_documents_threshold", {})
    add(f"- **Two chase thresholds.** /documents lists a request after 1 day, Today "
        f"chases after 3 (chasing.py:197; propose.py:151): "
        f"{tv.get('client_days_listed_on_documents_but_not_chased_on_today')} client-days "
        f"across {tv.get('clients')} clients were on one list and not the other.")
    add(f"- **Signature rows.** `signature_outstanding` rows across the season: "
        f"{o.get('signature_outstanding_rows_all_season')} -- no workflow opens an 8879 "
        f"request (H10), while client-documents held "
        f"{o.get('current_year_e_file_authorizations_fully_signed_in_client_documents')} fully "
        f"signed 2026 e-file authorizations (G7; satc says the fact is not one it follows, "
        f"sla.py:231-237).")
    wq = o.get("work_queue", {})
    add(f"- **The Work queue against a real March.** Job-days by stage: "
        f"{wq.get('stage_job_days')}. Days nothing was workable while returns were in "
        f"preparation: {wq.get('days_nothing_workable_while_returns_in_prep')}. No tax "
        f"workflow (1040, 1065, 1120-S, Schedule C) plans an internal task, so a tax job "
        f"is never workable; the owner here prepared earliest-statutory-deadline first "
        f"(an assumption), which /work never offered.")
    for m in wq.get("monthly_top", [])[:12]:
        top = "; ".join(f"#{t['rank']} {t['sim']} {t['workflow']} {t['score']}" for t in m["top"])
        add(f"  - {m['day']}: {m['workable']} workable, {m['not_workable']} not. {top or '-'}")
    add(f"- **Ready to deliver, never proposed.** {o.get('ready_to_deliver_job_days_never_proposed')} "
        f"job-days at `ready_to_deliver`; `deliver_return` is declared and nothing produces it "
        f"(propose.py:45).")
    add(f"- **Sitting untouched.** {o.get('stale_14_days_job_days')} job-days idle 14+ days by the "
        f"firm's own `stale_after_days` (firm_policy.yaml:71-74); most: {o.get('stale_jobs_top')}.")
    add(f"- **Ticked with no completion record.** {o.get('tasks_done_with_no_completion_record')} "
        f"tasks toggled done through the UI carry no completion time (H9; state.py:911-919), so "
        f"the idle factor and the unbilled age never see that work.")
    add(f"- **What blocks.** Request classes opened for 2026: {o.get('request_blocking_classes')} "
        f"(H7: nothing on a 1040 plan blocks prep).")
    add(f"- **SLAs at season end.** measurable: {o.get('slas', {}).get('measurable')}; "
        f"unmeasurable: {o.get('slas', {}).get('unmeasurable')}; Filings on file in satc: "
        f"{o.get('satc_filings_on_file')}, so the e-file reject clock has nothing to read.")
    add(f"- **K-1 lag.** Partnership delivered to dependent 1040 delivered: "
        f"{[(k['sim'], k['lag_days']) for k in o.get('k1_dependency', [])]}. Cross-job "
        f"dependencies are modelled nowhere (docs/BRIEFING.md:212).")
    add(f"- **Facts with no door.** {o.get('facts_with_no_door')}")
    add(f"- **Refused door calls.** {o.get('refused_door_calls')} (each belongs to a finding "
        f"above or is listed here): " + "; ".join(
            f"{r['day']} {r['sim']} {r.get('target')} -> {str(r.get('status'))}"
            for r in o.get("refusals_sample", [])[:6]))
    add("")
    ca = s.get("clock_audit") or []
    if ca:
        leaks = sorted({x for a in ca for x in a["leaks"]})
        add(f"- **Clock-leak audit.** {len(ca)} sample days, {len(ca[0]['reads'])} reads each, "
            f"run under the simulated clock and again under {'2031-06-15'} with `today=` "
            f"passed. Reads that changed: {leaks or 'none'}.")
        add("")

    add("## What the simulator did NOT cover")
    add("")
    for line in NOT_COVERED:
        add(f"- {line}")
    add("")

    add("## Denominators")
    add("")
    add("| invariant | examined (sum over days) | days checked | days with anything to check | findings |")
    add("|---|---|---|---|---|")
    for code, v in sorted(s["invariants"].items(), key=lambda kv: (kv[0][0], int(kv[0][1:]))):
        add(f"| {code} | {v['examined']} | {v['days_checked']} | {v['days_with_subjects']} | "
            f"{v['findings']} |")
    add("")
    add("A row with 0 in the fourth column examined nothing this seed: it neither passed nor "
        "failed.")
    add("")
    rl = s.get("run_level", {})
    add("## Run-level guards")
    add("")
    for k, v in sorted(rl.items()):
        add(f"- {k}: {v}")
    add(f"- banned doors: {', '.join(s.get('banned', []))}")
    add(f"- shadowed modules resolved inside client-documents: {s.get('shadowed_modules')}")
    add("")
    add("## Outcomes by archetype")
    add("")
    by = defaultdict(lambda: defaultdict(int))
    for sim, oc in s["outcomes"].items():
        a = oc["archetype"]
        by[a]["clients"] += 1
        for k in ("delivered", "extended", "disengaged", "filed"):
            by[a][k] += 1 if oc.get(k) else 0
    add("| archetype | clients | delivered | extended | disengaged | closed out as filed |")
    add("|---|---|---|---|---|---|")
    for a in sorted(by):
        v = by[a]
        add(f"| {a} | {v['clients']} | {v['delivered']} | {v['extended']} | {v['disengaged']} | "
            f"{v['filed']} |")
    add("")
    add(f"Reproduce this report: `python -m season_sim run --seed {seed} --report` "
        f"(from `season-simulator/`, with the venv active).")
    add("")
    return "\n".join(L)


def html_page(md_text: str, title: str) -> str:
    """A small, readable HTML rendering of the Markdown. Deliberately simple."""
    import re
    out = []
    in_list = 0
    in_table = False
    for raw in md_text.splitlines():
        line = raw.rstrip()
        esc = html.escape(line)
        esc = re.sub(r"`([^`]+)`", r"<code>\1</code>", esc)
        esc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", esc)
        esc = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", esc)
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-"):
                continue
            if not in_table:
                out.append("<table>")
                in_table = True
                out.append("<tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in cells) + "</tr>")
            else:
                out.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            out.append("</table>")
            in_table = False
        m = re.match(r"^(\s*)- (.*)$", line)
        if m:
            depth = len(m.group(1)) // 2 + 1
            while in_list < depth:
                out.append("<ul>")
                in_list += 1
            while in_list > depth:
                out.append("</ul>")
                in_list -= 1
            item = re.sub(r"^(\s*)- ", "", esc)
            out.append(f"<li>{item}</li>")
            continue
        while in_list:
            out.append("</ul>")
            in_list -= 1
        if line.startswith("### "):
            out.append(f"<h3>{esc[4:]}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{esc[3:]}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{esc[2:]}</h1>")
        elif line:
            out.append(f"<p>{esc}</p>")
    while in_list:
        out.append("</ul>")
        in_list -= 1
    if in_table:
        out.append("</table>")
    css = """
:root{--bg:#fbfbf8;--fg:#1d1d1b;--muted:#5b5b57;--line:#dcdcd4;--code:#efefe8;--accent:#8a3b12}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#171716;--fg:#ececE6;
--muted:#a9a9a2;--line:#3a3a36;--code:#262624;--accent:#e39a6c}}
:root[data-theme="dark"]{--bg:#171716;--fg:#ececE6;--muted:#a9a9a2;--line:#3a3a36;--code:#262624;--accent:#e39a6c}
body{background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;
max-width:980px;margin:0 auto;padding:24px 16px}
h1{font-size:1.6rem}h2{margin-top:2rem;border-bottom:1px solid var(--line);padding-bottom:.3rem;color:var(--accent)}
h3{margin-top:1.4rem}code{background:var(--code);padding:1px 4px;border-radius:3px;font-size:.86em;
word-break:break-word}table{border-collapse:collapse;width:100%;font-size:.9em;display:block;overflow-x:auto}
td,th{border:1px solid var(--line);padding:4px 8px;text-align:left}li{margin:.25rem 0}
"""
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8>"
            f"<meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{css}</style></head><body>"
            + "\n".join(out) + "</body></html>")


def write(out: Path, report_dir: Path) -> Path:
    report_dir = Path(report_dir)
    # Reports may go in season-simulator/reports/ (invented data only) or
    # anywhere outside the worktree; nowhere else inside it.
    from season_sim import guard
    if guard.refuses(report_dir, paths.REPO) and not guard.is_under(report_dir, paths.PROJECT / "reports"):
        raise SystemExit(f"refusing to write a report into {report_dir}")
    report_dir.mkdir(parents=True, exist_ok=True)
    _rows, s, _t = _load(out)
    md = markdown(out)
    name = f"season-2027-seed-{s['seed']}"
    path = report_dir / f"{name}.md"
    path.write_text(md, encoding="utf-8")
    (report_dir / f"{name}.html").write_text(html_page(md, f"Season 2027, seed {s['seed']}"),
                                             encoding="utf-8")
    return path
