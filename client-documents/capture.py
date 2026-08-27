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

import walkthrough as wt  # noqa: E402

OUT = ROOT / "out" / "walkthrough"
ANSWERS = json.loads(
    (ROOT / "samples" / "interview-answers.json").read_text(encoding="utf-8"))
FONTS = re.compile(r"https?://fonts\.(googleapis|gstatic)\.com/")
CHROMIUM = os.environ.get("SATC_CHROMIUM") or "/opt/pw-browsers/chromium"


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
        browser = await p.chromium.launch(executable_path=CHROMIUM)
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
        await answer_through(ctx, app.base, sid,
                             stop_at=lambda s: s["question"]["type"] == "text"
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
        screens.append(await look(page, "review", shots))

        await page.click("button:has-text('Create the engagement')")
        await page.wait_for_load_state("networkidle")
        screens.append(await look(page, "created", shots))
        ref = await page.evaluate(
            "() => (document.querySelector('h1').innerText.match"
            "(/\\d{4}-\\d{4}/) || [''])[0]")

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

        # ── the record, and the pack ──────────────────────────────────────
        await go(f"/engagement/{ref}")
        screens.append(await look(page, "engagement", shots))
        await go(f"/engagement/{ref}/package")
        screens.append(await look(page, "package-before", shots))

        async with page.expect_navigation(timeout=300000, wait_until="load"):
            await page.click("button:has-text('Build the pack')",
                             no_wait_after=True)
        screens.append(await look(page, "package-written", shots))

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
