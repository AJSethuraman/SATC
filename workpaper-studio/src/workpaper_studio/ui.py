"""Screens, in the Paper design (design/paper). Server-rendered HTML: the engine decides, these only show.

Nothing here computes a status, a result or a verdict. Every number and every word about completeness comes from
engine.evaluate(), so the screen cannot drift from the release check, the feed or the workbook.
"""
from __future__ import annotations

from html import escape as E

from .engine import OK_STATUSES, fmt_value
from .methods import blank
from .workbook import FAMILIES, mix

GROUND = "#E4E0D9"


def family_vars(family):
    dark, mid = FAMILIES.get(family or "graphite", FAMILIES["graphite"])
    return f"--dark:#{dark};--mid:#{mid};--bar:#{mix(dark, mid, .72)};--sub:#{mix(dark, 'FFFFFF', .7)};--label:#{mix(dark, 'FFFFFF', .22)};--btn:#{mix(dark, 'FFFFFF', .16)}"


CSS = """
:root{--ground:#E4E0D9;--card:#EBE7E0;--field:#F7F3EC;--recess:#DDD9D2;--na:#D4D0C9;--rule:#D3CFC8;--edge:#A29E97;--edgel:#F9F5EE;
--ink:#262421;--input:#1A1A1A;--mute:#6D6A63;--ok:#1F6F46;--okT:#DCEBDD;--warn:#8A5A00;--warnT:#F6E3B2;--warnE:#CF9A33;--bad:#A92A21;--badT:#F4D9D4}
*{box-sizing:border-box}
html,body{margin:0;background:var(--ground);color:var(--ink);font:13.3px/1.35 Arial,Helvetica,sans-serif}
a{color:var(--dark)}
.skip{position:absolute;left:-9999px}.skip:focus{left:8px;top:8px;background:#fff;padding:6px;z-index:9}
.band{background:var(--dark);color:#fff;padding:6px 16px 6px}
.band .row{display:flex;align-items:center;gap:12px;max-width:1080px;margin:0 auto}
.band h1{font-size:18.6px;font-weight:700;letter-spacing:.02em;text-transform:uppercase;margin:0;flex:1;min-width:0}
.band .subt{max-width:1080px;margin:2px auto 0;color:var(--sub);font-size:10.6px}
.nav{display:flex;gap:4px;flex-wrap:wrap}
.btn,.nav a{display:inline-block;padding:7px 12px;font:700 10.6px Arial;letter-spacing:.03em;text-transform:uppercase;color:#fff;background:var(--btn);
 border:1px solid;border-color:rgba(255,255,255,.45) rgba(0,0,0,.35) rgba(0,0,0,.35) rgba(255,255,255,.45);text-decoration:none;cursor:pointer;white-space:nowrap}
.nav a[aria-current=page]{background:var(--ground);color:var(--dark);border-color:var(--ground)}
.who{font-size:10.6px;color:var(--sub);text-align:right}.who a{color:#fff}
main,.page{max-width:1080px;margin:0 auto;padding:10px 16px 40px}
.strip{display:flex;flex-wrap:wrap;align-items:center;gap:8px 22px;padding:8px 0 12px}
.strip .lab{font:700 10.6px Arial;text-transform:uppercase;color:var(--dark)}
.chip{display:inline-block;padding:2px 12px;font-weight:700}
.chip.ok{background:var(--okT);color:var(--ok)}.chip.warn{background:var(--warnT);color:var(--warn)}.chip.plain{background:var(--card)}
.strip .actions{margin-left:auto;display:flex;gap:6px;flex-wrap:wrap}
.act{padding:7px 14px;font:700 12px Arial;border:1px solid var(--dark);background:var(--dark);color:#fff;cursor:pointer}
.act.secondary{background:var(--card);color:var(--dark)}
.act[aria-disabled=true]{opacity:.55}
.flash{padding:8px 12px;margin:0 0 10px;background:var(--badT);color:var(--bad);border:1px solid var(--bad)}
.flash.good{background:var(--okT);color:var(--ok);border-color:var(--ok)}
.saving{font-size:11px;color:var(--mute);min-height:14px}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:10px}
.card{background:var(--card);margin-bottom:10px}
.cards .card{margin:0}
.bar{background:var(--bar);color:#fff;font:700 13.3px Arial;text-transform:uppercase;letter-spacing:.02em;text-align:center;padding:4px 8px;position:relative}
.bar .code{position:absolute;right:8px;top:5px;font:400 10.6px Arial;text-transform:none}
.body{padding:6px 8px 4px}
.foot{text-align:right;font-weight:700;color:var(--mute);padding:2px 8px 6px}
.foot.ok{color:var(--ok)}.foot.warn{color:var(--warn)}
.note{font-style:italic;color:var(--mute);font-size:12px;padding:2px 8px}
.f{display:grid;grid-template-columns:minmax(90px,45%) 1fr;align-items:center;gap:3px 6px;margin:3px 0}
.f.long{grid-template-columns:1fr}
.f label,.f .l{color:var(--label);padding-left:4px}
.ctl{position:relative;display:flex;gap:3px}
input,select,textarea{font:13.3px Arial;color:var(--input);background:var(--field);border:1px solid;border-color:var(--edge) var(--edgel) var(--edgel) var(--edge);
 padding:3px 6px;width:100%;min-height:23px;border-radius:0}
input.num{text-align:right}
select{text-align:center;text-align-last:center}
textarea{resize:vertical;min-height:52px}
input:focus,select:focus,textarea:focus,.act:focus,.btn:focus,.mini:focus,.nav a:focus{outline:2px solid #2A4474;outline-offset:1px}
.missing input,.missing select,.missing textarea{background:var(--warnT);border-color:var(--warnE)}
.missing input::placeholder,.missing textarea::placeholder{color:var(--warn);font-style:italic}
.nastate{flex:1;background:var(--na);color:var(--mute);font-style:italic;text-align:center;padding:3px 6px;min-height:23px}
.calc{background:var(--recess);text-align:right;padding:3px 8px;min-height:23px}
.nc{font-style:italic;color:var(--mute);border-bottom:1px dashed #8C857A;text-align:center;padding:3px 8px}
.f .mini,table.t .mini{opacity:0}.f:hover .mini,.f:focus-within .mini,table.t tr:hover .mini,table.t tr:focus-within .mini,.mini:focus{opacity:1}
table.t th:empty{border:0}
.mini{font:10px Arial;color:var(--mute);background:none;border:1px solid var(--rule);padding:1px 5px;cursor:pointer;white-space:nowrap}
table.t{width:100%;border-collapse:separate;border-spacing:4px 3px}
table.t th{font:700 12px Arial;text-transform:uppercase;color:var(--dark);border-bottom:1px solid var(--dark);padding:2px 4px;text-align:center}
table.t td.rl{color:var(--label);white-space:nowrap;padding-left:4px}
table.t tr.ex td input,table.t tr.ex td select{background:repeating-linear-gradient(135deg,#CCC8C1 0 2px,var(--card) 2px 7px);text-decoration:line-through;color:var(--mute)}
table.t tr.tot td{font-weight:700}
.sub{font:700 13.3px Arial;color:var(--dark);margin:8px 4px 2px}
.q{display:grid;grid-template-columns:62px 1fr 180px 1.1fr;gap:4px 8px;align-items:stretch;margin:4px 0 6px}
.q .n{font-weight:700;color:var(--dark);text-align:center;align-self:center;font-size:13px}.q .n small{display:block;font:italic 10px Arial;color:var(--mute)}
.q .qt{color:var(--dark);font-size:14.6px;border-bottom:1px solid var(--rule);padding:4px;align-self:stretch;display:flex;flex-direction:column;justify-content:center}
.q .qt details{font-size:11.5px;color:var(--mute)}.q .qt summary{cursor:pointer;width:max-content}
.q select{height:100%;min-height:40px}.q textarea{min-height:40px}
.q.no{background:var(--na);opacity:.85}.q.no .qt{color:var(--mute)}
.rate-Effective select{color:var(--ok)}.rate-Partially select{color:var(--warn)}.rate-Not select{color:var(--bad)}
.grp{font:700 14.6px Arial;color:var(--dark);margin:10px 4px 2px}
.calcgrid{display:grid;grid-template-columns:1fr 160px 1.4fr;gap:3px 8px;align-items:center;padding:6px 8px}
.calcgrid .l{text-align:right;color:var(--label)}
.calcgrid .res{font:700 17px Arial;background:var(--recess);text-align:right;padding:4px 8px}
.verdict{font-weight:700;color:var(--mute)}.verdict.ok{color:var(--ok)}.verdict.bad{color:var(--bad)}.verdict.nt{font-style:italic;font-weight:400}
.trace{padding:2px 8px 8px;font-size:12px}
.trace ul{margin:2px 0 4px 18px;padding:0}
.points{border-top:1px solid var(--rule);margin:4px 8px 6px;padding-top:4px}
.pt{background:var(--field);border-left:3px solid var(--warnE);padding:6px 8px;margin:4px 0}
.pt.closed{border-left-color:var(--ok);opacity:.8}
.pt .meta{font-size:11px;color:var(--mute)}
.pt .reply{margin:4px 0 0 14px;padding-left:8px;border-left:2px solid var(--rule)}
form.inline{display:flex;gap:6px;align-items:flex-start;margin-top:4px}
form.inline textarea{min-height:34px}
.list{width:100%;border-collapse:collapse;background:var(--card)}
.list th{background:var(--bar);color:#fff;font:700 11px Arial;text-transform:uppercase;padding:6px 8px;text-align:left}
.list td{padding:6px 8px;border-bottom:1px solid var(--rule);vertical-align:top}
.ok-t{color:var(--ok);font-weight:700}.warn-t{color:var(--warn);font-weight:700}.bad-t{color:var(--bad);font-weight:700}
.hint{color:var(--mute);font-size:12px}
h2{font:700 15px Arial;color:var(--dark);margin:16px 0 6px}
.err{color:var(--bad);font-size:11.5px}
@media (max-width:760px){.cards{grid-template-columns:1fr}.q{grid-template-columns:44px 1fr}.q select,.q textarea{grid-column:2}.band h1{font-size:15px}
 .calcgrid{grid-template-columns:1fr 1fr}.calcgrid .vd{grid-column:1/3}}
@media print{.nav,.actions,.mini,.points form,.who,.saving,form,.skip{display:none!important}body{background:#fff}.card{break-inside:avoid}}
"""

JS = r"""
const CASE = document.body.dataset.case;
const main = () => document.getElementById('main');
const saving = t => { const s = document.getElementById('saving'); if (s) s.textContent = t; };
const QKEY = 'ws-pending-' + CASE;
function pending(){ try { return JSON.parse(localStorage.getItem(QKEY) || '[]'); } catch(e){ return []; } }
function setPending(q){ try { localStorage.setItem(QKEY, JSON.stringify(q)); } catch(e){} }
async function post(url, body){
  const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams(body)});
  if (!r.ok && r.status >= 500) throw new Error('server');
  return r.json();
}
function apply(res, focusPath){
  if (res.main){ const keep = focusPath || (document.activeElement && document.activeElement.dataset.path);
    main().innerHTML = res.main; bind();
    if (keep){ const el = main().querySelector('[data-path="'+CSS.escape(keep)+'"]'); if (el) el.focus(); } }
  const f = document.getElementById('flash');
  if (f){ f.textContent = res.error || ''; f.className = res.error ? 'flash' : ''; f.hidden = !res.error; }
}
async function send(kind, body, focusPath){
  saving('Saving…');
  try { const res = await post('/api/case/'+CASE+'/'+kind, body); apply(res, focusPath); saving(res.error ? 'Not saved: see the message above' : 'Saved'); return true; }
  catch(e){ const q = pending(); q.push([kind, body]); setPending(q); saving('Not saved yet: the connection failed. It will be retried, and nothing you typed is lost.'); return false; }
}
async function flush(){
  const q = pending(); if (!q.length) return;
  const rest = [];
  for (const [k, b] of q){ try { const res = await post('/api/case/'+CASE+'/'+k, b); apply(res); } catch(e){ rest.push([k, b]); } }
  setPending(rest); saving(rest.length ? 'Still not saved: retrying.' : 'Saved');
}
function bind(){
  main().querySelectorAll('[data-path]').forEach(el => {
    if (el.dataset.bound) return; el.dataset.bound = 1;
    el.addEventListener('change', () => send('set', {path: el.dataset.path, value: el.value}, el.dataset.path));
  });
  main().querySelectorAll('[data-mark]').forEach(b => {
    if (b.dataset.bound) return; b.dataset.bound = 1;
    b.addEventListener('click', () => {
      const st = b.dataset.mark; let reason = '';
      if (st){ reason = prompt(st === 'na' ? 'Why does this not apply?' : 'Why is this row left out?'); if (reason === null) return; }
      send('mark', {path: b.dataset.target, state: st, reason: reason});
    });
  });
}
if (CASE){ bind(); flush(); setInterval(flush, 4000); }
"""


def page(title, body, family=None, case_id="", band_title=None, subtitle="", nav=(), user=None, current=None):
    navh = "".join(f'<a href="{E(h)}"{" aria-current=page" if lab == current else ""}>{E(lab)}</a>' for lab, h in nav)
    who = f'<div class="who">{E(user)}<br><a href="/signin">Switch person</a></div>' if user else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><style>{CSS}</style></head>
<body data-case="{E(case_id)}" style="{family_vars(family)}"><a class="skip" href="#main">Skip to the work</a>
<header class="band"><div class="row"><h1>{E(band_title or title)}</h1><nav class="nav" aria-label="Screens">{navh}</nav>{who}</div>
<div class="subt">{E(subtitle)}</div></header>
{body}<script>{JS}</script></body></html>"""


def chip(text, tone="plain"):
    return f'<span class="chip {tone}">{E(str(text))}</span>'


def status_tone(status):
    if status in ("Complete",) or status.startswith("OK"):
        return "ok"
    if "missing" in status or status.startswith("Waiting"):
        return "warn"
    return ""


# ------------------------------------------------------------------ home, sign-in
def signin(users, nxt="/"):
    rows = "".join(f'<tr><td><form method="post" action="/signin"><input type="hidden" name="user" value="{E(u)}"><input type="hidden" name="next" value="{E(nxt)}">'
                   f'<button class="act" type="submit">{E(u)}</button></form></td><td>{E(", ".join(r))}</td></tr>' for u, r in users.items())
    body = f"""<main id="main"><h2>Who is working?</h2>
<p class="hint">This installation keeps a record of who did what. Choosing a name here is how it knows. It is not a password check:
this is a local tool for one organization, and the rules about who may do what are enforced whoever signs in.</p>
<table class="list"><tr><th>Person</th><th>Can</th></tr>{rows}</table></main>"""
    return page("Sign in · Workpaper Studio", body, band_title="Workpaper Studio", subtitle="Sign in")


def home(st, user, cases, flash=""):
    roles = st.roles(user)
    pub = st.published()
    nav = [("Cases", "/")] + ([("Settings", "/settings")] if roles & {"admin"} else [("Settings", "/settings")]) + [("Tools", "/tools")]
    start = ""
    if "preparer" in roles:
        btns = "".join(f'<form method="post" action="/case/new" style="display:inline"><input type="hidden" name="tool" value="{E(t)}">'
                       f'<button class="act" type="submit">New {E(t.lower())}</button></form> ' for t in sorted(pub))
        start = f'<div class="strip"><span class="lab">Start a case</span>{btns or "<span class=hint>No tool has been approved yet. A designer proposes one on Tools and an approver approves it.</span>"}</div>'

    def table(title, rows, empty):
        if not rows:
            return f'<h2>{E(title)}</h2><p class="hint">{E(empty)}</p>'
        trs = "".join(f'<tr><td><a href="/case/{E(c["id"])}">{E(c["id"])}</a></td><td>{E(c["tool"])} {E(c["version"])}</td><td>{E(c["subject"])}</td>'
                      f'<td>{E(c["status"])}</td><td>{_missing_txt(c)}</td><td>{E(c["preparer"])}</td><td>{E(c["events"][-1]["at"])}</td></tr>' for c in rows)
        return (f'<h2>{E(title)}</h2><table class="list"><tr><th>Case</th><th>Tool</th><th>Subject</th><th>Status</th><th>Still missing</th>'
                f'<th>Preparer</th><th>Last change</th></tr>{trs}</table>')
    mine = [c for c in cases if c["preparer"] == user and c["status"] != "Released"]
    review = [c for c in cases if "reviewer" in roles and c["status"] in ("In review", "Approved") and c["preparer"] != user]
    done = [c for c in cases if c["status"] == "Released"]
    others = [c for c in cases if c not in mine and c not in review and c not in done]
    parts = []
    if "preparer" in roles:
        parts.append(table("Your cases", mine, "You have no open cases. Start one above."))
    if "reviewer" in roles:
        parts.append(table("Waiting for your review", review, "Nothing is waiting for you."))
    parts.append(table("Other cases", others, "None."))
    parts.append(table("Released", done, "Nothing released yet."))
    fl = f'<div class="flash">{E(flash)}</div>' if flash else ""
    body = f'<main id="main">{fl}{start}{"".join(parts)}</main>'
    return page("Cases · Workpaper Studio", body, band_title="Workpaper Studio", subtitle="Cases", nav=nav, user=user, current="Cases")


def _missing_txt(c):
    n = c["eval"]["missing"]
    return f'<span class="warn-t">{n}</span>' if n else '<span class="ok-t">0</span>'


# ------------------------------------------------------------------ the case
def case_nav(c, current):
    screens = []
    for s in c["pack"].sections:
        sc = s.get("screen", "Workpaper")
        if sc not in screens:
            screens.append(sc)
    nav = [(sc, f'/case/{c["id"]}?screen={sc}') for sc in screens]
    nav += [("Check", f'/case/{c["id"]}/check'), ("History", f'/case/{c["id"]}/history'), ("Outputs", f'/case/{c["id"]}/outputs'), ("Cases", "/")]
    return nav


def case_page(st, user, c, screen="Workpaper", flash=""):
    body = f'<main id="main">{case_main(st, user, c, screen, flash)}</main>'
    sub = f'{c["pack"].data["org"]["name"]}  ·  {c["tool"]} {c["version"]}  ·  {c["id"]}  ·  pack {c["fingerprint"]}  ·  limits v{c["policy_version"]}'
    title = c["tool"] if screen == "Workpaper" else f'{c["tool"]}: {screen}'
    return page(f'{c["id"]} · {title}', body, family=c["pack"].data.get("family"), case_id=c["id"], band_title=title,
                subtitle=sub, nav=case_nav(c, screen), user=user, current=screen)


def case_main(st, user, c, screen, flash=""):
    roles = st.roles(user)
    can_edit = "preparer" in roles and c["status"] in ("In progress", "Returned")
    ev = c["eval"]
    out = [f'<div id="flash" class="flash" role="alert"{"" if flash else " hidden"}>{E(flash)}</div>', strip(st, user, c)]
    secs = [s for s in c["pack"].sections if s.get("screen", "Workpaper") == screen]
    i = 0
    while i < len(secs):
        s = secs[i]
        if _compact(s):
            group = [s]
            while len(group) < 3 and i + len(group) < len(secs) and _compact(secs[i + len(group)]):
                group.append(secs[i + len(group)])
            out.append('<div class="cards">' + "".join(section(st, user, c, g, can_edit, compact=True) for g in group) + "</div>")
            i += len(group)
        else:
            out.append(section(st, user, c, s, can_edit))
            i += 1
    out.append('<p class="saving" id="saving" aria-live="polite"></p>')
    return "".join(out)


def strip(st, user, c):
    ev, roles = c["eval"], st.roles(user)
    ready = ev["ready"]
    acts = []
    cid = c["id"]

    def a(label, action, secondary=False):
        return (f'<form method="post" action="/case/{E(cid)}/{action}" style="display:inline"><button class="act{" secondary" if secondary else ""}" '
                f'type="submit">{E(label)}</button></form>')
    if "preparer" in roles and c["status"] in ("In progress", "Returned") and user == c["preparer"]:
        acts.append(a("Submit for review", "submit"))
    if "reviewer" in roles and c["status"] == "In review" and user != c["preparer"]:
        acts += [a("Return to preparer", "return", True), a("Approve", "approve")]
    if roles & {"reviewer", "admin"} and c["status"] == "Approved":
        acts.append(a("Release", "release"))
    tone = {"In progress": "plain", "Returned": "warn", "In review": "plain", "Approved": "ok", "Released": "ok"}[c["status"]]
    return (f'<div class="strip" aria-label="Where this case stands"><span class="lab">Ready for review</span>{chip("Yes" if ready else "No", "ok" if ready else "warn")}'
            f'<span class="lab">Still missing</span><b>{ev["missing"]}</b><span class="lab">Sections complete</span><b>{ev["sections_done"]} of {ev["sections_total"]}</b>'
            f'<span class="lab">Status</span>{chip(c["status"], tone)}<span class="actions">{"".join(acts)}</span></div>')


def _compact(s):
    return all(b["kind"] == "field" and b.get("type") != "longtext" for b in s["blocks"]) and len(s["blocks"]) <= 4


def section(st, user, c, s, can_edit, compact=False):
    ev = c["eval"]
    sv = next(x for x in ev["sections"] if x["id"] == s["id"])
    note = ""
    if s["mode"] == "conditional":
        rf = s["rule"]["field"]
        lab = c["pack"].field(rf)["label"]
        note = f'<div class="note">Only when “{E(lab)}” is {E(" or ".join(s["rule"]["values"]))}.' + \
               (" It does not apply, so anything entered here is kept but not counted." if sv["applies"] == "No" else "") + "</div>"
    elif s["mode"] == "optional":
        note = '<div class="note">Optional: complete it if it helps the review.</div>'
    na = sv["applies"] == "No"
    edit = can_edit and not na
    parts = []
    fields_run = []

    def flush():
        if fields_run:
            parts.append('<div class="body">' + "".join(field(c, b, edit) for b in fields_run) + "</div>")
            fields_run.clear()
    for b in s["blocks"]:
        if b["kind"] == "field":
            fields_run.append(b)
            continue
        flush()
        if b["kind"] == "grid":
            parts.append(grid(c, b, edit, s, len(s["blocks"]) == 1))
        else:
            parts.append(calc(st, user, c, b, can_edit))
    flush()
    tone = status_tone(sv["status"])
    pts = points(st, user, c, s)
    style = ' style="background:var(--na)"' if na else ""
    return (f'<section class="card" id="s-{E(s["id"])}" aria-labelledby="h-{E(s["id"])}"{style}><div class="bar" id="h-{E(s["id"])}">{E(s["title"])}</div>{note}'
            f'{"".join(parts)}{pts}<div class="foot {tone}">{E(sv["status"])}</div></section>')


def _anchor(path):
    return "p-" + path.replace("/", "-").replace(".", "_").replace(" ", "_")


def control(c, defn, path, value, edit, missing=False, extra_cls=""):
    lists = c["pack"].data["org"].get("lists", {})
    t = defn.get("type", "text")
    dis = "" if edit else " disabled"
    aid = _anchor(path)
    ph = ' placeholder="Required"' if missing else ""
    lab = E(defn.get("label") or "")
    if t in ("list", "choice"):
        opts = defn.get("opts") if t == "choice" else lists.get(defn.get("list"), [])
        o = '<option value=""></option>' + "".join(f'<option{" selected" if v == value else ""}>{E(v)}</option>' for v in opts)
        return f'<select id="{aid}" data-path="{E(path)}" aria-label="{lab}"{dis} class="{extra_cls}">{o}</select>'
    if t in ("longtext", "comment"):
        return f'<textarea id="{aid}" data-path="{E(path)}" aria-label="{lab}"{dis}{ph}>{E("" if blank(value) else str(value))}</textarea>'
    if t == "date":
        return f'<input type="date" id="{aid}" data-path="{E(path)}" aria-label="{lab}" value="{E(value or "")}"{dis}>'
    if t == "number":
        shown = "" if blank(value) else fmt_value(value, defn).replace("$", "")
        return f'<input class="num" inputmode="decimal" id="{aid}" data-path="{E(path)}" aria-label="{lab}" value="{E(shown)}"{dis}{ph}>'
    return f'<input id="{aid}" data-path="{E(path)}" aria-label="{lab}" value="{E("" if blank(value) else str(value))}"{dis}{ph}>'


def field(c, b, edit):
    f = c["eval"]["fields"][b["id"]]
    path = f"f/{b['id']}"
    long_ = b.get("type") == "longtext"
    cls = "f long" if long_ else "f"
    if f["state"] == "na":
        ctl = (f'<div class="ctl"><div class="nastate" id="{_anchor(path)}" tabindex="-1">N/A: {E(f["reason"] or "")}</div>'
               + (f'<button class="mini" type="button" data-mark="" data-target="{E(path)}">Clear</button>' if edit else "") + "</div>")
    else:
        mk = f'<button class="mini" type="button" data-mark="na" data-target="{E(path)}" title="Mark not applicable, with a reason">N/A</button>' if edit else ""
        ctl = f'<div class="ctl{" missing" if f["state"] == "missing" else ""}">{control(c, b, path, f["value"], edit, f["state"] == "missing")}{mk}</div>'
    req = "" if b.get("req") else ' <span class="hint">(optional)</span>'
    return f'<div class="{cls}"><label for="{_anchor(path)}">{E(b["label"])}{req}</label>{ctl}</div>'


def grid(c, g, edit, s, only):
    t = c["eval"]["tables"][g["id"]]
    if t["questions"] is not None:
        return questions(c, g, t, edit)
    gid, by = g["id"], g.get("cellsBy", "col")
    C, rows = t["cols"], list(t["rows"])
    rows_from, cols_from = g["rows"]["from"], g["cols"]["from"]
    if rows_from == "entered":
        n = max(len(rows) + 1, g["rows"].get("min", 0), 3)
        lab = (g["rows"].get("addLabel") or "Row").capitalize()
        rows += [{"key": str(i), "label": f"{lab} {i + 1}", "cells": {}, "computed": {}, "excluded": False, "reason": None, "def": {}} for i in range(len(rows), n)]
    head = '<tr><th scope="col"><span class="skip">Row</span></th>'
    for j, col in enumerate(C):
        if cols_from == "entered":
            cp = f"g/{gid}/_cols/c{j}"
            names = (c["data"].get(gid) or {}).get("_cols") or []
            v = names[j] if j < len(names) else ""
            head += f'<th scope="col"><input data-path="{E(cp)}" aria-label="Name of column {j + 1}" value="{E(v)}" placeholder="{E(col["label"])}"{"" if edit else " disabled"}></th>'
        else:
            head += f'<th scope="col">{E(col["label"])}</th>'
    head += "<th></th></tr>" if edit and rows_from in ("entered", "list") else "</tr>"
    miss = {i["path"] for sec in c["eval"]["sections"] for i in sec["items"]}
    body = ""
    for r in rows:
        cls = ' class="ex"' if r["excluded"] else ""
        tip = ' title="Left out: ' + E(r["reason"] or "") + '"' if r["excluded"] else ""
        tr = f'<tr{cls}><td class="rl"{tip}>{E(r["label"])}</td>'
        for col in C:
            d_ = r["def"] if by == "row" else col
            path = f"g/{gid}/{r['key']}/{col['key']}"
            if d_.get("compute"):
                v = r["computed"].get(col["key"])
                tr += f'<td><div class="calc">{E(fmt_value(v, dict(d_, type="number")) if v is not None else "")}</div></td>'
            else:
                defn = dict(d_, label=f'{r["label"]}, {col["label"]}')
                v = r["cells"].get(col["key"])
                m = path in miss
                tr += f'<td class="{"missing" if m else ""}">{control(c, defn, path, v, edit and not r["excluded"], m)}</td>'
        if edit and rows_from in ("entered", "list"):
            used = r["excluded"] or any(not blank(x) for x in r["cells"].values())
            if r["excluded"]:
                tr += f'<td><button class="mini" type="button" data-mark="" data-target="g/{E(gid)}/{E(r["key"])}">Include</button></td>'
            elif used:
                tr += f'<td><button class="mini" type="button" data-mark="excluded" data-target="g/{E(gid)}/{E(r["key"])}" title="Leave this row out, with a reason">Exclude</button></td>'
            else:
                tr += "<td></td>"
        body += tr + "</tr>"
    if t["totals"]:
        tr = '<tr class="tot"><td class="rl">Total</td>'
        for col in C:
            v = t["totals"].get(col["key"])
            tr += f'<td><div class="calc">{E(fmt_value(v, dict(col, type="number")))}</div></td>' if v is not None else "<td></td>"
        body += tr + "</tr>"
    ex = [r for r in rows if r["excluded"]]
    exn = "".join(f'<div class="note">{E(r["label"])} is left out: {E(r["reason"] or "")}.</div>' for r in ex)
    title = "" if only else f'<div class="bar" style="margin-top:6px">{E(g["label"])}</div>'
    return f'{title}<div class="body"><table class="t" aria-label="{E(g["label"])}"><thead>{head}</thead><tbody>{body}</tbody></table>{exn}</div>'


def questions(c, g, t, edit):
    gid = g["id"]
    rating, comment = t["cols"][0], (t["cols"][1] if len(t["cols"]) > 1 else None)
    out, last = [], None
    for r in t["rows"]:
        q = t["questions"][r["key"]]
        d = r["def"]
        if d.get("group") and d["group"] != last:
            out.append(f'<div class="grp">{E(d["group"])}</div>')
            last = d["group"]
        when = d.get("when")
        cond = ""
        if when:
            lab = c["pack"].field(when["field"])["label"]
            cond = f'<small>if {E(lab.rstrip("?").lower())}</small>' if when["values"] == ["Yes"] else f'<small>if {E(", ".join(when["values"]).lower())}</small>'
        no = q["applies"] == "No"
        rp, cp = f"g/{gid}/{r['key']}/{rating['key']}", (f"g/{gid}/{r['key']}/{comment['key']}" if comment else None)
        info = f'<details><summary>How to test</summary>{E(d.get("info", ""))}</details>' if d.get("info") else ""
        rv = q["rating"] or ""
        rate_cls = "rate-" + rv.split()[0] if rv else ""
        rctl = control(c, dict(rating, label=f'Question {r["key"]} rating'), rp, rv, edit and not no, q["rating_missing"] and not no)
        cctl = control(c, dict(comment, type="comment", label=f'Question {r["key"]} comment'), cp, q["comment"], edit and not no, q["need_comment"]) if comment else ""
        state = ""
        if no:
            state = '<div class="note">Not applicable for this case.</div>'
        elif q["applies"] == "Waiting":
            state = f'<div class="note">Waiting on “{E(c["pack"].field(when["field"])["label"])}”.</div>'
        out.append(f'<div class="q{" no" if no else ""}" id="q-{E(r["key"])}"><div class="n">{E(r["key"])}{cond}</div>'
                   f'<div class="qt">{E(d.get("label", ""))}{info}{state}</div>'
                   f'<div class="{rate_cls}{" missing" if q["rating_missing"] and not no else ""}">{rctl}</div>'
                   f'<div class="{"missing" if q["need_comment"] else ""}">{cctl}</div></div>')
    return '<div class="body">' + "".join(out) + "</div>"


def calc(st, user, c, b, can_edit):
    k = c["eval"]["calcs"][b["id"]]
    rows = ""
    for lab, v in k["parts"].items():
        if v is None:
            shown = '<div class="nc">Not calculated</div>'
        elif lab == "Inputs still missing" or k["method"] == "devrate":
            shown = f'<div class="calc">{v}</div>'
        elif v is None:
            shown = '<div class="nc">Not calculated</div>'
        else:
            shown = f'<div class="calc">${v:,.2f}</div>' if k["method"] == "recon" else f'<div class="calc">${v:,.0f}</div>'
        rows += f'<div class="l">{E(lab)}</div>{shown}<div></div>'
    res = f'<div class="res">{E(k["display"])}</div>' if k["status"] == "calculated" else f'<div class="nc">{E(k["display"])}</div>'
    vc = {"Within limit": "ok", "Above limit": "bad"}.get(k["verdict"], "nt")
    rows += f'<div class="l"><b>{E(k["name"])}</b></div>{res}<div class="vd verdict {vc}">{E(k["verdict"])}</div>'
    pol = k["policy"]
    lim = (f'Limit {k["limit_display"]}, set by the organization on Settings (confirmed by {E(pol.get("by", ""))} on {E(pol.get("date", ""))}). It is not part of the method.'
           if k["confirmed"] else "No limit has been confirmed for this organization yet, so the result is not tested. An admin confirms it on Settings.")
    trace = f'<div class="trace"><div class="hint">{lim}</div>'
    if k["missing"]:
        trace += "<b>Why there is no result</b><ul>" + "".join(f"<li>{E(m)}</li>" for m in k["missing"]) + "</ul>"
    if k["disclosures"]:
        trace += "<b>Disclosed</b><ul>" + "".join(f"<li>{E(m)}</li>" for m in k["disclosures"]) + "</ul>"
    trace += "</div>"
    exc = exceptions(st, user, c, b, k, can_edit)
    return (f'<div class="bar" id="calc-{E(b["id"])}" style="margin-top:6px">{E(k["name"])}<span class="code">{E(k["code"])}</span></div>'
            f'<div class="calcgrid" aria-live="polite">{rows}</div>{trace}{exc}')


def exceptions(st, user, c, b, k, can_edit):
    exs = [e for e in c["exceptions"].values() if e["calc"] == b["id"]]
    if k["verdict"] != "Above limit" and not exs:
        return ""
    roles = st.roles(user)
    out = '<div class="points"><b>Exception</b> <span class="hint">The result stays as calculated. An exception is recorded beside it.</span>'
    for e in exs:
        ack = f'Acknowledged by {E(e["ack"]["by"])}, {E(e["ack"]["at"])}' if e["ack"] else "Waiting for the reviewer to acknowledge it."
        btn = ""
        if not e["ack"] and "reviewer" in roles and user != c["preparer"] and c["status"] == "In review":
            btn = f'<form method="post" action="/case/{E(c["id"])}/ack" class="inline"><input type="hidden" name="id" value="{E(e["id"])}"><button class="act" type="submit">Acknowledge</button></form>'
        out += f'<div class="pt{" closed" if e["ack"] else ""}"><b>{E(e["reason"])}</b>. {E(e["note"])}<div class="meta">Recorded by {E(e["by"])}, {E(e["at"])}. {ack}</div>{btn}</div>'
    if k["verdict"] == "Above limit" and "preparer" in roles and c["status"] in ("In progress", "Returned", "In review") and not exs:
        reasons = c["pack"].data["org"]["lists"].get("Exception reasons", [])
        o = "".join(f"<option>{E(r)}</option>" for r in reasons)
        out += (f'<form method="post" action="/case/{E(c["id"])}/exception" class="inline"><input type="hidden" name="calc" value="{E(b["id"])}">'
                f'<select name="reason" aria-label="Reason" style="max-width:260px"><option value="">Reason…</option>{o}</select>'
                f'<textarea name="note" aria-label="Explain the exception" placeholder="Explain it"></textarea><button class="act" type="submit">Record exception</button></form>')
    return out + "</div>"


def points(st, user, c, s):
    pts = [p for p in c["points"].values() if p["section"] == s["id"]]
    roles = st.roles(user)
    is_rev = "reviewer" in roles and user != c["preparer"]
    if not pts and not (is_rev and c["status"] == "In review"):
        return ""
    out = '<div class="points">'
    for p in pts:
        reps = "".join(f'<div class="reply">{E(r["text"])}<div class="meta">{E(r["by"])}, {E(r["at"])}</div></div>' for r in p["replies"])
        acts = ""
        if p["open"] and "preparer" in roles and user == c["preparer"]:
            acts += (f'<form method="post" action="/case/{E(c["id"])}/reply" class="inline"><input type="hidden" name="id" value="{E(p["id"])}">'
                     f'<textarea name="text" aria-label="Your answer to {E(p["id"])}" placeholder="Your answer"></textarea><button class="act" type="submit">Answer</button></form>')
        if p["open"] and is_rev:
            acts += (f'<form method="post" action="/case/{E(c["id"])}/clear" class="inline"><input type="hidden" name="id" value="{E(p["id"])}">'
                     f'<button class="act secondary" type="submit">Clear point {E(p["id"])}</button></form>')
        state = "Open" if p["open"] else f'Cleared by {E(p.get("cleared_by", ""))}'
        out += f'<div class="pt{"" if p["open"] else " closed"}" id="point-{E(p["id"])}"><b>{E(p["id"])}</b> {E(p["text"])}<div class="meta">Raised by {E(p["by"])}, {E(p["at"])} · {state}</div>{reps}{acts}</div>'
    if is_rev and c["status"] == "In review":
        out += (f'<form method="post" action="/case/{E(c["id"])}/point" class="inline"><input type="hidden" name="section" value="{E(s["id"])}">'
                f'<textarea name="text" aria-label="Review point on {E(s["title"])}" placeholder="Raise a review point on {E(s["title"])}"></textarea>'
                f'<button class="act secondary" type="submit">Raise point</button></form>')
    return out + "</div>"


# ------------------------------------------------------------------ check, history, outputs
def check_page(st, user, c, flash=""):
    rows = ""
    for x in st.release_check(c):
        link = ""
        if x["link"]:
            if x["link"].startswith(("f/", "g/")):
                sec = _section_of(c, x["link"])
                link = f'<a href="/case/{E(c["id"])}?screen={E(sec.get("screen", "Workpaper"))}#{_anchor(x["link"])}">Go to it</a>'
            elif x["link"].startswith("calc/"):
                sec = _section_of_calc(c, x["link"][5:])
                link = f'<a href="/case/{E(c["id"])}?screen={E(sec.get("screen", "Workpaper"))}#calc-{E(x["link"][5:])}">Go to it</a>'
            elif x["link"].startswith("point/"):
                link = f'<a href="/case/{E(c["id"])}#point-{E(x["link"][6:])}">Go to it</a>'
        cls = "ok-t" if x["ok"] else "warn-t"
        rows += f'<tr><td>{E(x["check"])}</td><td class="{cls}">{"OK" if x["ok"] else "Not yet"}</td><td>{E(x["detail"])}</td><td>{link}</td></tr>'
    fl = f'<div class="flash">{E(flash)}</div>' if flash else ""
    body = (f'<main id="main">{fl}{strip(st, user, c)}<p class="hint">Every line must read OK before the case is approved and released. '
            f'Each line that is not says what is needed and links to it.</p><table class="list"><tr><th>Check</th><th>Result</th><th>Detail</th><th></th></tr>{rows}</table></main>')
    return page(f'{c["id"]} · Release check', body, family=c["pack"].data.get("family"), band_title=f'{c["tool"]}: release check',
                subtitle=f'{c["id"]}  ·  {c["status"]}', nav=case_nav(c, "Check"), user=user, current="Check")


def _section_of(c, path):
    parts = path.split("/")
    for s, b in c["pack"].blocks():
        if b.get("id") == parts[1]:
            return s
    return {}


def _section_of_calc(c, cid):
    for s, b in c["pack"].blocks():
        if b.get("id") == cid:
            return s
    return {}


def history_page(st, user, c):
    rows = ""
    for e in reversed(c["events"]):
        what = {k: v for k, v in e.items() if k not in ("seq", "at", "actor", "kind")}
        detail = ""
        if e["kind"] == "set":
            detail = f'{E(e["path"])}: {E(_s(e.get("old")))} → <b>{E(_s(e.get("new")))}</b>'
        elif e["kind"] == "mark":
            detail = f'{E(e["path"])}: ' + (f'{"not applicable" if e["state"] == "na" else "excluded"} ({E(e.get("reason") or "")})' if e.get("state") else "cleared")
        else:
            detail = E("; ".join(f"{k}: {v}" for k, v in what.items() if k != "outputs")) or ""
        rows += f'<tr><td>{e["seq"]}</td><td>{E(e["at"])}</td><td>{E(e["actor"])}</td><td>{E(e["kind"].replace("_", " "))}</td><td>{detail}</td></tr>'
    body = (f'<main id="main"><p class="hint">Everything done to this case, newest first. Nothing here can be changed or removed: '
            f'the case on screen is rebuilt from this list.</p><table class="list"><tr><th>#</th><th>When</th><th>Who</th><th>What</th><th>Detail</th></tr>{rows}</table></main>')
    return page(f'{c["id"]} · History', body, family=c["pack"].data.get("family"), band_title=f'{c["tool"]}: history',
                subtitle=c["id"], nav=case_nav(c, "History"), user=user, current="History")


def _s(v):
    return "(blank)" if v is None or v == "" else str(v)


def outputs_page(st, user, c):
    rel = st.released_outputs(c["id"])
    if rel:
        rows = "".join(f'<tr><td><a href="/case/{E(c["id"])}/file/{E(o["name"])}">{E(o["name"])}</a></td><td><code>{E(o["sha256"][:16])}</code></td><td>{E(o["at"])}</td></tr>' for o in rel)
        released = f'<h2>Released</h2><p class="hint">Written once at release and fingerprinted. These are the record.</p><table class="list"><tr><th>File</th><th>SHA-256</th><th>Written</th></tr>{rows}</table>'
    else:
        released = '<h2>Released</h2><p class="hint">Nothing yet. Outputs are written once, when the case is released.</p>'
    draft = (f'<h2>Drafts</h2><p class="hint">Built now from the case as it stands. Marked as drafts: they are not the record.</p>'
             f'<p><a class="act" href="/case/{E(c["id"])}/draft/feed.json">Data feed (JSON)</a> <a class="act" href="/case/{E(c["id"])}/draft/feed.csv">Data feed (CSV)</a> '
             f'<a class="act" href="/case/{E(c["id"])}/draft/workbook.xlsx">Workbook</a> <a class="act secondary" href="/case/{E(c["id"])}?print=1" target="_blank">Print the workpaper</a></p>'
             f'<p class="hint">The data feed’s layout is this application’s own proposal: the receiving system’s format has not been supplied yet. Fields marked personal are masked in it.</p>')
    body = f'<main id="main">{strip(st, user, c)}{released}{draft}</main>'
    return page(f'{c["id"]} · Outputs', body, family=c["pack"].data.get("family"), band_title=f'{c["tool"]}: outputs',
                subtitle=c["id"], nav=case_nav(c, "Outputs"), user=user, current="Outputs")


# ------------------------------------------------------------------ settings and tools
def settings_page(st, user, flash=""):
    roles = st.roles(user)
    pv, pol = st.policy()
    rows = ""
    for tool, v in sorted(st.published().items()):
        p = st.stored_pack(v["fingerprint"])
        for s, b in p.calcs():
            cur = pol.get(tool, {}).get(b["id"], {})
            pct = b["method"] in ("dti", "devrate")
            shown = lambda x: "" if x is None else (f"{x * 100:g}" if pct else f"{x:g}")
            confirmed = cur.get("confirmed")
            state = f'<span class="ok-t">Confirmed</span> by {E(cur.get("by", ""))}, {E(cur.get("date", ""))}' if confirmed else '<span class="warn-t">Not confirmed</span>'
            form = ""
            if "admin" in roles:
                form = (f'<form method="post" action="/settings" class="inline"><input type="hidden" name="tool" value="{E(tool)}"><input type="hidden" name="calc" value="{E(b["id"])}">'
                        f'<input name="limit" aria-label="Our limit" value="{E(shown(cur.get("limit", b["limit"])))}" style="width:90px">{"%" if pct else ""}'
                        f'<button class="act" type="submit">Confirm</button></form>')
            rows += (f'<tr><td>{E(tool)}</td><td>{E(b["limitLabel"])}</td><td>{E(b.get("code", ""))}</td><td>{E(shown(b["limit"]))}{"%" if pct else ""}</td>'
                     f'<td>{E(shown(cur.get("limit"))) if cur else "–"}{"%" if pct and cur else ""}</td><td>{state}</td><td>{form}</td></tr>')
    hist = "".join(f'<tr><td>v{h["version"]}</td><td>{E(h["at"])}</td><td>{E(h["by"])}</td><td>{E(h["note"])}</td></tr>' for h in st.policy_history())
    fl = f'<div class="flash">{E(flash)}</div>' if flash else ""
    body = (f'<main id="main">{fl}<h2>Limits</h2><p class="hint">A limit belongs to this organization, not to the method. The method’s author recommends one; '
            f'nothing is tested against it until an admin confirms the organization’s own. A case keeps the limits it was started with (version {pv} is current).</p>'
            f'<table class="list"><tr><th>Tool</th><th>Limit</th><th>Method</th><th>Author recommends</th><th>Ours</th><th>State</th><th></th></tr>{rows}</table>'
            f'<h2>Versions</h2><table class="list"><tr><th>Version</th><th>When</th><th>Who</th><th>Change</th></tr>{hist}</table></main>')
    return page("Settings · Workpaper Studio", body, band_title="Settings", subtitle="Organization limits",
                nav=[("Cases", "/"), ("Settings", "/settings"), ("Tools", "/tools")], user=user, current="Settings")


def tools_page(st, user, flash=""):
    roles = st.roles(user)
    good, bad = st.pack_files()
    vers = {v["fingerprint"]: v for v in st.versions()}
    rows = ""
    for p in good:
        v = vers.get(p.fingerprint)
        if not v:
            state = '<span class="warn-t">Not proposed</span>'
            act = (f'<form method="post" action="/tools/propose" class="inline"><input type="hidden" name="file" value="{E(p.file)}"><button class="act" type="submit">Propose for publishing</button></form>'
                   if "designer" in roles else "")
        elif not v["approved_by"]:
            state = f'<span class="warn-t">Proposed</span> by {E(v["proposed_by"])}, waiting for an approver'
            act = (f'<form method="post" action="/tools/approve" class="inline"><input type="hidden" name="fp" value="{E(p.fingerprint)}"><button class="act" type="submit">Approve</button></form>'
                   if "approver" in roles else "")
        else:
            state = f'<span class="ok-t">Published</span>: proposed by {E(v["proposed_by"])}, approved by {E(v["approved_by"])}'
            act = ""
        rows += (f'<tr><td><a href="/tools/{E(p.file)}">{E(p.name)}</a></td><td>{E(p.version)}</td><td><code>{E(p.fingerprint)}</code></td><td>{E(p.file)}</td>'
                 f'<td>{state}</td><td>{act}</td></tr>')
    for e in bad:
        rows += f'<tr><td colspan="4">{E(e.file)}</td><td class="bad-t" colspan="2">Refused: {E(str(e))}</td></tr>'
    hist = "".join(f'<tr><td>{E(v["tool"])} {E(v["version"])}</td><td><code>{E(v["fingerprint"])}</code></td><td>{E(v["proposed_by"])}, {E(v["proposed_at"])}</td>'
                   f'<td>{E(v["approved_by"] or "–")}{", " + E(v["approved_at"]) if v["approved_at"] else ""}</td></tr>' for v in reversed(st.versions()))
    fl = f'<div class="flash">{E(flash)}</div>' if flash else ""
    body = (f'<main id="main">{fl}<h2>Tool packs</h2><p class="hint">Each tool is one pack file: its sections, questions, tables, lists and calculations. '
            f'A pack that is wrong is refused here with the reason. A designer proposes a version and a different person approves it. '
            f'New cases use the newest approved version; existing cases keep the version they were started with.</p>'
            f'<table class="list"><tr><th>Tool</th><th>Version</th><th>Fingerprint</th><th>File</th><th>State</th><th></th></tr>{rows}</table>'
            f'<h2>Every version ever proposed</h2><table class="list"><tr><th>Tool</th><th>Fingerprint</th><th>Proposed</th><th>Approved</th></tr>{hist}</table></main>')
    return page("Tools · Workpaper Studio", body, band_title="Tools", subtitle="Tool packs, versions and approvals",
                nav=[("Cases", "/"), ("Settings", "/settings"), ("Tools", "/tools")], user=user, current="Tools")


def pack_page(st, user, p):
    out = []
    for s in p.sections:
        mode = {"required": "Required", "optional": "Optional", "conditional": "Only when " + (s.get("rule") or {}).get("field", "") + " is " + " or ".join((s.get("rule") or {}).get("values", []))}[s["mode"]]
        items = []
        for b in s["blocks"]:
            if b["kind"] == "field":
                items.append(f'Field: {E(b["label"])} ({E(b["type"])}{", required" if b.get("req") else ""}{", personal" if b.get("personal") else ""})')
            elif b["kind"] == "grid":
                items.append(f'Table: {E(b["label"])}. Rows {E(b["rows"]["from"])}, columns {E(b["cols"]["from"])}' +
                             (f' ({", ".join(E(str(i.get("label") or i["key"])) for i in b["cols"].get("items") or [])})' if b["cols"]["from"] == "fixed" else ""))
            else:
                items.append(f'Calculation: {E(b.get("code", b["method"]))}, recommended limit {E(str(b["limit"]))}')
        out.append(f'<section class="card"><div class="bar">{E(s["title"])}</div><div class="note">{E(mode)}{" · screen " + E(s["screen"]) if s.get("screen") else ""}</div>'
                   f'<div class="body"><ul>{"".join(f"<li>{x}</li>" for x in items)}</ul></div></section>')
    lists = "".join(f'<tr><td>{E(k)}</td><td>{E(", ".join(v))}</td></tr>' for k, v in p.data["org"]["lists"].items())
    body = (f'<main id="main"><p class="hint">{E(p.file)} · fingerprint <code>{E(p.fingerprint)}</code>. This is the configuration; the case screens are generated from it.</p>'
            f'{"".join(out)}<h2>Lists</h2><table class="list"><tr><th>List</th><th>Values</th></tr>{lists}</table></main>')
    return page(f"{p.name} · Tools", body, family=p.data.get("family"), band_title=f"{p.name} {p.version}", subtitle="Pack outline",
                nav=[("Cases", "/"), ("Settings", "/settings"), ("Tools", "/tools")], user=user, current="Tools")
