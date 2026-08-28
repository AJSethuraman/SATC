"""Photographing the browser front door, and counting what is on each screen.

The firm, on the procedures generated from the CLI's own subparsers: *"These
are not pleasant procedures for a user."* They were written from the software's
side of the desk -- they led with commands and module names, and they described
the terminal, which is the builder's door, not the preparer's.

What they asked for instead: a walkthrough somebody runs LIVE, with a client in
the chair. *"be very descriptive on what needs to be clicked and press stand
all the options available like some of them will be so obvious you don't need
to overexplain, but some things will be like why would I ever use this
option?"*

So this drives the real application in a real browser, photographs every screen
a preparer passes through, and writes down EVERY CONTROL IT CAN SEE on each
one. The prose is not generated -- a machine has nothing useful to say about
why you would ever use a control -- but the INVENTORY is, and that is the half
that goes stale. `registry/walkthrough.yaml` answers for each control, and
`missing()` below fails when a control has no answer or an answer names a
control that is no longer there.

Which is the whole point. A hand-written walkthrough of a screen that has
changed is worse than none: the reader trusts it, follows it, and ends up
somewhere the page does not go.

NOTHING REAL IS PHOTOGRAPHED. The leads come from `samples/demo-leads.json`,
which is fabricated and says so. `client-documents/leads.xlsx` is the firm's
real workbook, it holds real people, and nothing here may open it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "samples" / "demo-leads.json"
REGISTRY = ROOT / "registry" / "walkthrough.yaml"
# WHAT THE SOFTWARE LOOKED LIKE LAST TIME ANYBODY PHOTOGRAPHED IT. Committed,
# in text, so the check that the registry answers for every control can run in
# the suite -- where there is no browser to drive and no screen to look at.
# `capture.py` rewrites it, and a difference is the news: either the front door
# changed and the walkthrough has not, or the harness has stopped seeing
# straight.
INVENTORY_FILE = ROOT / "registry" / "walkthrough-screens.json"

# The order a preparer meets them, which is the order the walkthrough runs in.
# A screen missing from here is a screen the walkthrough does not cover, and
# `missing()` says so rather than letting it be quietly skipped.
SCREENS = [
    ("home", "The list you start from"),
    ("leads", "Everyone who has asked"),
    ("lead-detail", "What one prospect told us"),
    ("by-phone", "Somebody who called instead"),
    ("question", "One question at a time"),
    ("question-claim", "A question the website already answered"),
    ("question-hardno", "Work the firm does not take"),
    ("question-back", "Going back to fix an answer"),
    ("review", "Everything, before anything is created"),
    ("created", "The engagement exists"),
    ("refused", "A HARD NO"),
    ("engagement", "The record"),
    ("package-before", "What is about to be built"),
    ("package-blocked", "A check failed"),
    ("package-written", "The pack, and every check that passed"),
    ("requote-form", "The work changed, so the price does"),
    ("requote-changes", "Every line the new quote moves"),
    ("requote-done", "The new quote, recorded"),
    ("signatures-waiting", "Who to chase this morning"),
    ("signatures-one", "One client, and what is still out"),
    ("prices", "What the firm charges"),
    ("wording", "Changing a sentence in a letter"),
    ("wording-section", "One section, open"),
    ("wording-add", "Adding a section that is not there"),
]


@dataclass(frozen=True)
class Control:
    """One thing on the screen a person can act on -- once, however many times
    it is drawn.

    THE REVIEW PAGE HAS THIRTY-EIGHT "Change" BUTTONS AND ONE AFFORDANCE. A
    walkthrough that lists them separately is a walkthrough nobody finishes,
    and a registry that demands thirty-eight explanations gets thirty-eight
    copies of the same sentence. So controls are folded by SHAPE -- what they
    are, what they are styled as, and, for a button, which form they post to
    and what that form carries.

    The shape is what distinguishes them, not the label. `← Back` and `Never
    mind — nothing to change` are both `button.link` on the same page and are
    two different things: one posts to the back route empty, the other posts
    `resume`. The forms tell them apart; the styling does not.
    """
    kind: str
    shape: str
    # The label, when this control says one thing. Empty when it is a repeated
    # row -- then `examples` carries what it said, and the explanation is about
    # the row, not about any one of them.
    label: str = ""
    examples: tuple[str, ...] = ()
    count: int = 1

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.label}" if self.label else f"{self.kind}[{self.shape}]"

    @property
    def shown(self) -> str:
        """What to call it in the document."""
        if self.label:
            return self.label
        if len(self.examples) <= 3:
            return ", ".join(self.examples)
        return f"{', '.join(self.examples[:3])}, and {len(self.examples) - 3} more"


# A LABEL THAT IS AN IDENTIFIER IS NOT A NAME. The home page's one link to an
# engagement is captioned `2026-0001`, which is a different string on the next
# run -- keying an explanation to it would mean the registry went stale every
# time anybody looked.
_IDISH = re.compile(r"^\d{4}-\d{4}$|^[0-9a-f]{8,}$")


def fold(raw: list[dict]) -> list[Control]:
    """The screen's affordances, from everything the browser could see.

    Same shape and same words -> one control. Same shape, different words ->
    one control that is drawn per row, with what it said kept as examples.
    """
    groups: dict[str, list[dict]] = {}
    for c in raw:
        if c.get("label"):
            groups.setdefault(c["shape"], []).append(c)
    out = []
    for shape, group in groups.items():
        labels = [g["label"] for g in group]
        distinct = sorted(set(labels))
        named = len(distinct) == 1 and not _IDISH.match(distinct[0])
        if named:
            out.append(Control(kind=group[0]["kind"], shape=shape,
                               label=distinct[0], count=len(group)))
        else:
            out.append(Control(kind=group[0]["kind"], shape=shape,
                               examples=tuple(distinct), count=len(group)))
    return out


@dataclass
class Screen:
    key: str
    heading: str
    shot: str = ""
    controls: list[Control] = field(default_factory=list)
    # What the page says about itself, above the controls.
    help: str = ""


# The JavaScript that does the looking. It runs in the page, because the only
# honest answer to "what can a preparer see here" comes from the rendered
# document -- `innerText` is empty for anything that is not laid out, which is
# exactly the thing a walkthrough must not describe as visible.
INVENTORY = r"""() => {
  const seen = [];
  // `offsetParent !== null` IS A PROXY, AND IT LIES. A textarea inside a
  // CLOSED <details> reports an offsetParent and a 36px box in Chromium --
  // measured, on a fixture, because the same class of bug has bitten this
  // repository before from the other side (`innerText` reads '' for a subtree
  // that is not laid out, while its rectangle still has a height). Counting
  // controls a preparer cannot see is precisely the failure a walkthrough
  // built by looking is supposed to be immune to.
  //
  // `checkVisibility` gets all of it right -- display:none, visibility:hidden
  // and a shut disclosure -- and the fallback is only for a browser that does
  // not have it.
  const vis = el => el.checkVisibility
    ? el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true,
                          contentVisibilityAuto: true})
    : (el.offsetParent !== null && !el.closest('details:not([open])'));
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();

  // An engagement ref, a draft id and a filename all vary run to run. What
  // matters about a form is WHICH ROUTE it posts to and what it carries, so
  // the varying parts become <id> and the shape survives the next sitting.
  const route = f => {
    if (!f) return '';
    const a = (f.getAttribute('action') || '').split('?')[0];
    const carries = [...f.querySelectorAll('input[type=hidden]')]
      .map(i => i.name).sort().join(',');
    return a.replace(/\/[0-9a-f]{8,}/g, '/<id>')
            .replace(/\/\d{4}-\d{4}/g, '/<ref>')
            .replace(/\/[^/]+\.html/g, '/<file>')
          + (carries ? '{' + carries + '}' : '');
  };
  const shape = el => {
    const cls = [...el.classList].sort().join('.');
    const nm = (el.getAttribute('name') || '').split(':')[0];
    const kind = el.tagName.toLowerCase();
    // A BUTTON WRAPPED IN A LINK IS THE LINK. "Home" and "Open the
    // engagement" are both `button.ghost` sitting inside the same form, and
    // folding them together would explain one and call the other missing --
    // where each one GOES is the whole difference between them.
    const href = el.closest('a') ? (el.closest('a').getAttribute('href') || '')
        .replace(/[0-9a-f]{8,}/g, '<id>').replace(/\d{4}-\d{4}/g, '<ref>')
      : '';
    const parts = [kind, el.type || '', cls, nm,
                   href || route(el.form || el.closest('form'))];
    return parts.filter(Boolean).join('|');
  };

  // A BOX WITH NO CAPTION STILL HAS A NAME ON THE SCREEN -- it is just not
  // written beside it. The interview's answer box is captioned by the
  // question; a section's text box is captioned by the section it is inside.
  // Falling back to the `name` attribute would put `t:s01.1` in a document a
  // preparer reads, which is the software's word for it and nobody else's.
  const labelFor = el => {
    if (el.id) {
      const l = document.querySelector(`label[for="${el.id}"]`);
      if (l) return clean(l.innerText);
    }
    const wrap = el.closest('label');
    if (wrap) return clean(wrap.innerText);
    if (clean(el.placeholder)) return clean(el.placeholder);
    // A CAPTION THE PAGE DECLARES, because a box inside a disclosure has no
    // caption of its own and there is now more than one kind. This used to
    // return 'the text of one section' for any of them, which was true while
    // the wording editor was the only screen built this way -- and then the
    // re-quote put an answer box inside a disclosure and it was captioned as
    // a section of a letter. The summary's own text cannot be used: it is the
    // section heading, or the question, and either makes a registry key that
    // is different next week.
    const box = el.closest('details');
    if (box) {
      const said = box.getAttribute('data-caption');
      if (said) return clean(said);
      if (box.querySelector('summary')) return 'the text of one section';
    }
    const h = document.querySelector('h1');
    return h ? 'the answer to “' + clean(h.innerText) + '”' : '';
  };

  for (const b of document.querySelectorAll('button')) {
    if (vis(b)) seen.push({kind: 'button', label: clean(b.innerText),
                           shape: shape(b)});
  }
  for (const a of document.querySelectorAll('a')) {
    if (vis(a) && clean(a.innerText) && !a.querySelector('button')) {
      // WHERE IT SITS IS PART OF WHAT IT IS. The masthead and a "Home" link
      // in the body both point at `/`; folding them together would explain
      // one of them and describe the other as missing.
      const zone = a.closest('header') ? 'header' : 'main';
      seen.push({kind: 'link', label: clean(a.innerText),
                 shape: 'a|' + zone + '|' +
                        [...a.classList].sort().join('.') + '|' +
                        (a.getAttribute('href') || '')
                          .replace(/[0-9a-f]{8,}/g, '<id>')
                          .replace(/\d{4}-\d{4}/g, '<ref>')
                          .replace(/\/[^/]+$/, '/<x>')});
    }
  }
  for (const i of document.querySelectorAll('input, textarea, select')) {
    if (!vis(i) || i.type === 'hidden') continue;
    const kind = i.tagName === 'TEXTAREA' ? 'textarea'
               : i.tagName === 'SELECT' ? 'select' : i.type;
    seen.push({kind, label: labelFor(i), shape: shape(i)});
  }
  for (const d of document.querySelectorAll('details > summary')) {
    if (vis(d)) seen.push({kind: 'disclosure', label: clean(d.innerText),
                           shape: 'summary|' +
                             [...d.parentElement.classList].sort().join('.')});
  }
  return {
    heading: clean((document.querySelector('h1') || {}).innerText),
    help: clean((document.querySelector('p.help') || {}).innerText),
    controls: seen,
  };
}"""


def demo_workbook(into: Path) -> Path:
    """The fabricated leads, as the workbook the app reads.

    Built rather than committed as a binary: a reviewer can read
    `samples/demo-leads.json` and see at a glance that nobody in it is real,
    which is not true of an .xlsx.
    """
    import openpyxl

    spec = json.loads(DEMO.read_text(encoding="utf-8"))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(spec["columns"])
    for row in spec["rows"]:
        ws.append(row)
    into.parent.mkdir(parents=True, exist_ok=True)
    wb.save(into)
    return into


def load_registry(path: Path | None = None) -> dict:
    """{screen: {control key: explanation or None}}.

    `None` is a deliberate answer, not a gap: it means somebody looked at that
    control and decided a preparer needs no help with it. "Next" is the case
    this exists for -- explaining it would train the reader to skip the notes,
    and the notes are where the ones that matter live.
    """
    import yaml

    path = path or REGISTRY
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def missing(screens: list[Screen], registry: dict) -> list[str]:
    """Everything the walkthrough would be lying about, in one list.

    Three ways it can lie, and all three are the same lie -- the document says
    something about the software that is not so:

    * a screen in `SCREENS` that was never reached (so it has no photograph,
      and whatever the text says about it is unchecked),
    * a control on a screen with no entry at all (so the walkthrough is
      silently incomplete: the reader meets a button the document never
      mentions),
    * an entry for a control that is not on the screen any more (so the
      walkthrough tells them to press something that is gone).
    """
    out = []
    got = {s.key: s for s in screens}
    # THE CHROME IS EXPLAINED ONCE. The masthead link is on all eighteen
    # screens; eighteen identical entries would be eighteen places to forget
    # to change it, and a reader who meets the same sentence eighteen times
    # stops reading the sentences.
    everywhere = registry.get("_everywhere") or {}
    for key, _ in SCREENS:
        if key not in got:
            out.append(f"{key}: never reached, so nothing about it is checked")
    seen_everywhere: set[str] = set()
    for screen in screens:
        entries = registry.get(screen.key)
        if entries is None:
            out.append(f"{screen.key}: no entry in the registry at all")
            continue
        here = {c.key for c in screen.controls}
        seen_everywhere |= here & set(everywhere)
        for control in screen.controls:
            if control.key not in entries and control.key not in everywhere:
                out.append(f"{screen.key}: nothing written about "
                           f"{control.key!r}, which is on the screen")
        for named in entries:
            if named not in here:
                out.append(f"{screen.key}: the registry explains {named!r}, "
                           f"which is not on the screen any more")
    for named in everywhere:
        if named not in seen_everywhere:
            out.append(f"_everywhere: {named!r} is explained as being on every "
                       f"screen and is on none of them")
    return out


def to_json(screens: list[Screen]) -> str:
    return json.dumps(
        [{"key": s.key, "heading": s.heading, "help": s.help, "shot": s.shot,
          "controls": [{"kind": c.kind, "shape": c.shape, "label": c.label,
                        "examples": list(c.examples), "count": c.count}
                       for c in s.controls]}
         for s in screens], indent=2, ensure_ascii=False) + "\n"


def from_json(text: str) -> list[Screen]:
    return [Screen(key=d["key"], heading=d["heading"], help=d.get("help", ""),
                   shot=d.get("shot", ""),
                   controls=[Control(kind=c["kind"], shape=c["shape"],
                                     label=c.get("label", ""),
                                     examples=tuple(c.get("examples", ())),
                                     count=c.get("count", 1))
                             for c in d["controls"]])
            for d in json.loads(text)]
