"""Drive the browser front door and photograph every screen of it.

Run it: `python capture.py` (writes into `out/walkthrough/`).

This is a HARNESS, not a test. It starts the real application on a real port,
walks it with a real browser, and writes what it saw. `walkthrough.missing()`
is what turns that into a check; this file's whole job is to get to every
screen and look at it.

Everything it photographs is fabricated -- `samples/demo-leads.json` and
`samples/interview-answers.json`, both of which say so in their first line. The
firm's real workbook is never opened here and must never be.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.parse
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import presend  # noqa: E402
import walkthrough as wt  # noqa: E402

OUT = ROOT / "out" / "walkthrough"
ANSWERS = json.loads(
    (ROOT / "samples" / "interview-answers.json").read_text(encoding="utf-8"))
FONTS = re.compile(r"https?://fonts\.(googleapis|gstatic)\.com/")

# THE PINNED BROWSER, AND THE FALLBACK, LIVE IN `presend`. This file used
# to carry its own copy of the constant and launch it directly, so it died
# with "executable doesn't exist at /opt/pw-browsers/chromium" on the first
# machine that was not the container it was written in -- while the
# application it photographs rendered fine on that same machine.


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class App:
    """The real application, on a real port, in its own process.

    Not Flask's test client: a test client renders no pixels, and the one
    failure this whole harness exists to catch is a screen that reads
    differently to a person than it does to a string search.
    """

    def __init__(self, store: Path, workbook: Path, templates: Path):
        self.port = _free_port()
        self.store, self.workbook, self.templates = store, workbook, templates
        self.proc: subprocess.Popen | None = None

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self):
        # THE TEMPLATES ARE A COPY. One screen the walkthrough has to show is
        # the gate refusing a pack, and the honest way to reach it is the way a
        # preparer would: change a sentence in a letter to something the firm
        # has ruled out, and try to send it. That writes to a template file --
        # so the app is pointed at a throwaway copy, and the repository's own
        # templates are never touched by a screenshot run.
        script = (
            "import sys; sys.path.insert(0, %r)\n"
            "from pathlib import Path\n"
            "import cli, editor\n"
            "cli.TEMPLATE_DIR = editor.TEMPLATE_DIR = Path(%r)\n"
            "import web\n"
            "web.create_app(store=Path(%r), leads_workbook=Path(%r))"
            ".run(port=%d, use_reloader=False)\n"
            % (str(ROOT), str(self.templates), str(self.store),
               str(self.workbook), self.port))
        self.proc = subprocess.Popen([sys.executable, "-c", script],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        for _ in range(80):
            try:
                with socket.create_connection(("127.0.0.1", self.port), 0.4):
                    return self
            except OSError:
                time.sleep(0.25)
        raise RuntimeError("the application did not come up")

    def __exit__(self, *exc):
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=10)


async def look(page, key: str, shots: Path) -> wt.Screen:
    """Photograph one screen and write down everything on it."""
    await page.wait_for_timeout(220)
    shot = f"{key}.png"
    # CROP TO WHAT IS ON THE SCREEN. A full-page shot of a short page is the
    # page plus several hundred pixels of nothing, and in a document where
    # nineteen of them run down the page in a column, the nothing is most of
    # what a reader scrolls past.
    box = await page.evaluate("""() => {
      const els = [document.querySelector('header'),
                   document.querySelector('main')].filter(Boolean);
      if (!els.length) return null;
      const r = els.map(e => e.getBoundingClientRect());
      const top = Math.min(...r.map(b => b.top + window.scrollY));
      // `main` carries 80px of bottom padding so a page never ends flush
      // against the window. In a photograph that is just empty paper, so the
      // crop ends at the last thing actually drawn.
      const kids = [...(document.querySelector('main') || {children: []})
                      .children];
      const last = kids.length
        ? Math.max(...kids.map(k => k.getBoundingClientRect().bottom))
          + window.scrollY
        : Math.max(...r.map(b => b.bottom + window.scrollY));
      const bottom = Math.max(last, ...r.map(b => b.top + window.scrollY));
      return {x: 0, y: Math.max(0, top), width: document.documentElement.clientWidth,
              height: Math.min(bottom - top + 24, 4000)};
    }""")
    await page.screenshot(path=str(shots / shot), full_page=True,
                          clip=box or None)
    seen = await page.evaluate(wt.INVENTORY)
    controls = wt.fold(seen["controls"])
    drawn = sum(c.count for c in controls)
    print(f"  {key:<18} {len(controls):>2} control(s) ({drawn:>2} drawn)  "
          f"{seen['heading'][:40]}")
    return wt.Screen(key=key, heading=seen["heading"], help=seen["help"],
                     shot=shot, controls=controls)


async def answer_through(ctx, base, sid, stop_at=None):
    """Answer the interview over its own JSON door, up to a question or the end.

    The browser is for looking at; getting to question forty is plumbing, and
    doing it by clicking would make this harness forty times slower and no more
    truthful.
    """
    J = {"Accept": "application/json"}
    while True:
        st = await (await ctx.request.get(f"{base}/interview/{sid}",
                                          headers=J)).json()
        if st["complete"]:
            return None
        qid = st["question"]["id"]
        if stop_at and stop_at(st):
            return st
        await ctx.request.post(
            f"{base}/interview/{sid}",
            data={"answer": ANSWERS.get(qid)},
            headers={**J, "Content-Type": "application/json"})


async def run(app: App, shots: Path) -> list[wt.Screen]:
    from playwright.async_api import async_playwright

    J = {"Accept": "application/json"}
    screens: list[wt.Screen] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(**presend.launch_args())
        # NARROW ON PURPOSE. The app's column is 660px wide; photographing it
        # at 1180 puts a quarter of every screenshot into empty margin, and
        # then the document scales the whole thing down into a text column --
        # so the buttons a preparer is being told to press end up smaller than
        # the words telling them to press them.
        ctx = await browser.new_context(viewport={"width": 800, "height": 900})
        page = await ctx.new_page()
        await page.route(FONTS, lambda r: r.abort())

        async def go(path):
            await page.goto(app.base + path, wait_until="networkidle")

        # ── the leads list, and one lead opened ───────────────────────────
        await go("/leads")
        screens.append(await look(page, "leads", shots))
        await page.click("details.blk.quiet summary")
        screens.append(await look(page, "lead-detail", shots))
        await page.click("details.blk.door summary")
        screens.append(await look(page, "by-phone", shots))

        # ── a sitting, started from the first lead ────────────────────────
        await go("/leads")
        await page.click("text=Start the interview")
        await page.wait_for_load_state("networkidle")
        sid = page.url.rstrip("/").rsplit("/", 1)[-1]
        # The first question is the one the website already answered, so it
        # carries a claim and the one-press button that takes it.
        screens.append(await look(page, "question-claim", shots))

        # A plain typed question, and one that can refuse the work.
        #
        # `year` COUNTS AS TYPED. It is a box you type into, and until
        # 3 September 2026 `tax_year` was `type: text` and was the question this
        # stopped at. Giving it its own type moved this stop PAST `red_flags` --
        # so the walk answered the hard-no question on its way by, and the next
        # step had no hard-no question left to photograph and shot the review
        # screen instead. The registry caught it; nothing else would have.
        await answer_through(ctx, app.base, sid,
                             stop_at=lambda s: s["question"]["type"] in ("text", "year")
                             and not s["claim"])
        await go(f"/interview/{sid}")
        screens.append(await look(page, "question", shots))

        await answer_through(
            ctx, app.base, sid,
            stop_at=lambda s: any(o.get("hard_no")
                                  for o in s["question"].get("options", [])))
        await go(f"/interview/{sid}")
        screens.append(await look(page, "question-hardno", shots))

        # Going back to fix the answer just given.
        await answer_through(ctx, app.base, sid,
                             stop_at=lambda s: s["answered"] >= 12)
        await ctx.request.post(f"{app.base}/interview/{sid}/back", headers=J)
        await go(f"/interview/{sid}")
        screens.append(await look(page, "question-back", shots))
        await ctx.request.post(f"{app.base}/interview/{sid}/back",
                               data={"resume": True},
                               headers={**J, "Content-Type": "application/json"})

        # ── review, and what it decides ───────────────────────────────────
        await answer_through(ctx, app.base, sid)
        await go(f"/interview/{sid}")
        # HOVER ONE ROW FIRST, because that is the control now. Twenty-six
        # answers each carrying the word `Change` is the word twenty-six times
        # and the eye cannot find the one that is wrong, so from 3 September
        # 2026 the word appears on the row you are pointing at or have tabbed
        # to. The harness counts what a preparer can SEE (`checkOpacity`), so
        # photographing this screen cold would show -- correctly -- no way to
        # change anything, and the walkthrough would stop explaining one.
        # THE ROW THAT HAS ONE, not the second row. Only some answers are
        # editable, so `tr:nth-child(2)` hovered whichever row happened to be
        # second -- and when that one carried no Change button the harness
        # correctly reported none drawn, and the walkthrough check failed
        # saying the registry explained a control that was not there. The
        # control was there; the hover was pointed at the wrong row.
        await page.locator("table.plain tr:has(td.fix button.link)").first \
                  .hover()
        screens.append(await look(page, "review", shots))

        # CREATING LANDS ON THE CLIENT'S FILE. The page that used to say
        # "Engagement 2026-0001 created" and offer three buttons is gone
        # (3 September 2026), so this is where a preparer arrives -- with the
        # line at the top saying it was just made and the stage bar showing
        # the one thing that has happened so far. Photographed HERE rather
        # than later precisely because that is the state they meet.
        await page.click("button:has-text('Create the engagement')")
        await page.wait_for_load_state("networkidle")
        screens.append(await look(page, "engagement", shots))
        ref = page.url.rstrip("/").split("/engagement/")[-1].split("?")[0]

        # ── the same interview, refused ───────────────────────────────────
        no = (await (await ctx.request.post(app.base + "/interview",
                                            headers=J)).json())["draft"]
        await answer_through(ctx, app.base, no)
        await ctx.request.post(
            f"{app.base}/interview/{no}",
            data={"answer": ["assurance_needed"]},
            headers={**J, "Content-Type": "application/json"})
        # `red_flags` is answered above; posting it again is how a preparer
        # would change it, so drive the refusal the way one happens.
        await ctx.request.post(f"{app.base}/interview/{no}/back",
                               data={"to": "red_flags"},
                               headers={**J, "Content-Type": "application/json"})
        await ctx.request.post(
            f"{app.base}/interview/{no}",
            data={"answer": ["assurance_needed"]},
            headers={**J, "Content-Type": "application/json"})
        await go(f"/interview/{no}")
        await page.click("button:has-text('Create the engagement')")
        await page.wait_for_load_state("networkidle")
        screens.append(await look(page, "refused", shots))

        # ── the pack ──────────────────────────────────────────────────────
        await go(f"/engagement/{ref}/package")
        screens.append(await look(page, "package-before", shots))

        # A CLEAN BUILD NO LONGER HAS A PAGE. Nothing was flagged, so it lands
        # back on the client's file with the count on a line -- which is why
        # nothing is photographed here. The build still has to RUN: everything
        # after this walks an engagement that has a pack.
        async with page.expect_navigation(timeout=300000, wait_until="load"):
            await page.click("button:has-text('Build the pack')",
                             no_wait_after=True)

        # ── the work changed, so the price does ───────────────────────────
        #
        # Driven exactly as a preparer would: open the one question whose
        # answer moved, type the new number, look at what it does to the
        # estimate, and give the reason that records it. Not staged -- the
        # figures on these three screenshots are the fee schedule's, computed
        # in the running app while the shot was taken.
        # TWO ANSWERS, BECAUSE THEY STATE ONE FACT. The count is what the
        # K-1 line is billed from; the additional-forms line is the same fact
        # in the preparer's own words, printed two inches above it. Moving one
        # without the other is refused, so the walkthrough shows the way that
        # works rather than the way that stops.
        await go(f"/engagement/{ref}/requote")
        await page.click("details.blk:has(input[name=count_k1s]) summary")
        await page.fill("input[name=count_k1s]", "6")
        await page.click("details.blk:has(input[name=additional_forms]) summary")
        await page.fill("input[name=additional_forms]", "Six K-1s as reported")
        screens.append(await look(page, "requote-form", shots))

        async with page.expect_navigation(timeout=300000, wait_until="load"):
            await page.click("button:has-text('See what changes')",
                             no_wait_after=True)
        screens.append(await look(page, "requote-changes", shots))

        await page.fill("textarea[name=reason]",
                        "the estate issued four more K-1s in June")
        # Same again: recording the quote lands on the client's file, where
        # the price history it used to show on its own page already prints.
        async with page.expect_navigation(timeout=300000, wait_until="load"):
            await page.click("button:has-text('Record the new quote')",
                             no_wait_after=True)

        # ── who has signed, and who has not ───────────────────────────────
        #
        # The pack is recorded as gone out first, because that is the order it
        # happens in and because "outstanding" means nothing until something
        # has been sent. Then one signature is recorded, so the screen is
        # photographed with both halves on it -- what is back and what is not.
        await go(f"/engagement/{ref}/signatures")
        async with page.expect_navigation(timeout=300000, wait_until="load"):
            await page.click("button:has-text('It has gone out')",
                             no_wait_after=True)
        await page.click("details.blk:has(input[name=reference]) summary")
        await page.fill("details.blk[open] input[name=on]", "February 9, 2027")
        await page.check("details.blk[open] input[value=e-signed]")
        await page.fill("details.blk[open] input[name=reference]", "env_9f2c11")
        async with page.expect_navigation(timeout=300000, wait_until="load"):
            await page.click("details.blk[open] button:has-text('Record it')",
                             no_wait_after=True)
        # Photographed with one still open: the form is what a preparer uses,
        # and a screen of shut disclosures cannot be written about.
        await page.click("details.blk:has(input[name=reference]) summary")
        screens.append(await look(page, "signatures-one", shots))

        await go("/signatures")
        screens.append(await look(page, "signatures-waiting", shots))

        # A BILL IS RAISED FIRST, because a payments screen with no invoice on
        # it shows nothing and teaches nothing. Raised through the real
        # command, with no link -- this environment cannot reach Square, and a
        # walkthrough that quietly needed a network would be a walkthrough
        # nobody else could regenerate.
        import cli as _cli
        _cli.main(["invoice", "--engagement", ref, "--store", str(app.store),
                   "--billed", "2026 tax year", "--no-link"])
        await go("/payments")
        screens.append(await look(page, "payments", shots))

        # ── the two screens the rest of the app hangs off ─────────────────
        await go("/")
        screens.append(await look(page, "home", shots))
        await go("/prices")
        screens.append(await look(page, "prices", shots))
        await go("/templates")
        screens.append(await look(page, "wording", shots))

        # ── and the gate refusing, reached the way one is reached ─────────
        #
        # Not staged: a sentence in the engagement letter is changed to
        # something the firm has ruled out of anything a client reads, exactly
        # as a preparer might, and the pack is rebuilt. The check that catches
        # it is the one that would catch it in March.
        # The 1040 pack's engagement letter, by the name `cli.DOCUMENTS` gives
        # it -- not a filename typed in here, which would go stale the first
        # time a template is renamed.
        import cli
        letter = urllib.parse.quote(cli.DOCUMENTS["tax-letter"][0])
        await go(f"/templates/{letter}")
        await page.click("details.blk summary")
        screens.append(await look(page, "wording-section", shots))
        await page.click("details.blk.add summary")
        screens.append(await look(page, "wording-add", shots))
        await page.click("details.blk.add summary")
        box = await page.query_selector("details.blk[open] textarea")
        was = await box.input_value()
        await box.fill(was.rstrip() +
                       " Payment is due pursuant to the terms above.")
        await page.click("details.blk[open] button:has-text('Save this section')")
        await page.wait_for_load_state("networkidle")

        await go(f"/engagement/{ref}/package")
        async with page.expect_navigation(timeout=300000, wait_until="load"):
            await page.click("button:has-text('Build the pack')",
                             no_wait_after=True)
        screens.append(await look(page, "package-blocked", shots))

        await browser.close()
    return screens


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    shots = OUT / "shots"
    shots.mkdir(parents=True)
    work = Path(tempfile.mkdtemp(prefix="satc-walk-"))
    try:
        book = wt.demo_workbook(work / "demo-leads.xlsx")
        templates = work / "templates"
        shutil.copytree(ROOT.parent / "satc-handoff" / "04-TEMPLATES", templates)
        print(f"\nPhotographing the front door — fabricated leads from "
              f"{wt.DEMO.name}\n")
        with App(work / "store", book, templates) as app:
            screens = asyncio.run(run(app, shots))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    book = wt.to_json(screens)
    (OUT / "screens.json").write_text(book, encoding="utf-8")
    # And the committed copy, so the suite can check the registry against it
    # on a machine with no browser.
    wt.INVENTORY_FILE.write_text(book, encoding="utf-8")
    total = sum(len(s.controls) for s in screens)
    print(f"\n  {len(screens)} screen(s), {total} control(s), photographed "
          f"into {shots}")

    gaps = wt.missing(screens, wt.load_registry())
    if gaps:
        print(f"\n  {len(gaps)} thing(s) the walkthrough would be wrong about:")
        for g in gaps:
            print(f"    {g}")
        return 1
    print("\n  Every screen reached and every control accounted for.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
