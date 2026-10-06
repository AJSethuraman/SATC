"""A real headless browser, because claiming to be one is a false statement.

THE FIRM DECIDED THIS ON THE DOCKET, 8 September 2026, asked what a tie-out
should announce to a publisher: **"Real headless browser."** Not a client that
sends a browser's user-agent string. The distinction is not fussiness — the text
those publishers serve is cited as authority in client work, and a request that
misrepresents who is asking is a false statement made in the course of it.

AND IT COSTS US ACCESS. THIS PARAGRAPH USED TO SAY THE OPPOSITE and the claim
was never measured. It read *"it also happens to be the only thing that works"*
and cited two rows:

    UA satc-desk-tieout   ->   10,596 b   an interstitial on another host
    UA Chrome/140         ->  584,798 b   THE REGULATION

BOTH ROWS WERE CURL WITH A USER-AGENT STRING SWAPPED. No browser was in that
experiment, so it establishes that SENDING A CHROME UA STRING works and says
nothing whatever about a real browser. The desk that produced the original
measurement caught the error in its own data being quoted back at it, on the
Forge, 8 September 2026 -- and then measured the thing itself:

    a real headless Chrome  ->   12,474 b   "Request Access", correct host,
                                            no redirect, HTTP 200

    "THE HONEST CLIENT IS REFUSED. THE MISREPRESENTING ONE IS SERVED."

The mechanism, established with no network and no misrepresentation, by asking
the browser what it announces: `HeadlessChrome/…`, `webdriver=false`. FLAGS
below sets no `--user-agent`, so eCFR flags the token `HeadlessChrome` exactly
as it flagged `satc-desk-tieout`. It is the string, not automation detection.

SO THE ARGUMENT FOR A REAL BROWSER IS THE ETHICAL ONE AND ONLY THAT ONE, and it
stands on its own -- which is just as well, because the empirical one is
inverted. `--user-agent=Chrome/140` would very likely work and is exactly the
false statement the firm ruled out. That is theirs to reconsider, and it is a
sharper decision than when they made it: honesty here costs access, and the
sentence this paragraph replaced was what hid the cost.

WHAT THE PUBLISHER DOES IS STILL THE DANGEROUS SHAPE, whichever client is used:
it refuses with an HTTP 200 carrying a full page of unrelated text. A network
error becomes COULD NOT, correctly, but a clean 200 with the wrong document used
to become DIFFERS -- which `ask.answer` reads as `authority_has_moved` and uses
to WITHDRAW the answer. That happened, end to end, on the Forge: the product
told a human to retire a citation the publisher carries perfectly well.
`proving._absent` is the fix -- DIFFERS now requires positive evidence that the
document IS the one asked for.

SO `url` IS THE LOAD-BEARING FIELD and this transport's first duty is to report
WHERE IT LANDED. The browser should stop the bounce happening at all;
`proving`'s landed-host check stays as the guard for when it does not, and a
transport that does not say where it ended up disarms that guard silently.

STDLIB ONLY, AND THE BROWSER IS A SUBPROCESS. `desk` is a plugin that installs
onto the firm's machine with nothing to pip-install, and this module must import
cleanly where no browser exists at all -- every test in this suite imports it and
none of them may launch one. So the binary is DISCOVERED at call time, never at
import, and its absence is an ordinary refusal naming the fix rather than an
ImportError at the top of the file.

NOTHING HERE RUNS IN THE TEST SUITE, and that is not a gap that grepping closes.
`conftest.py` replaces the socket layer for every test, autouse, with a test
proving that guard can fail -- so the one thing this module exists to do is the
one thing CI can never exercise. What CI covers is the SHAPE: the command built,
the landed URL read back, the failures told apart. What only a live run covers is
whether a real publisher serves a real browser the real document. That run is
#344, on the Forge, recorded -- and until it exists this module is unproven
against anything but a fixture.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from fetch import Response

#: Where a headless Chromium lives, in the order worth trying. `CHROME` is
#: honoured first so a machine with an unusual layout says so once rather than
#: being guessed at forever -- and the environment variable is read at CALL
#: time, so a test can point this at a fixture without reloading the module.
ENV_VAR = "SATC_DESK_BROWSER"
CANDIDATES = (
    "chromium", "chromium-browser", "google-chrome", "google-chrome-stable",
    "chrome", "msedge",
    # The path this container ships, named explicitly because `which` does not
    # find it: Playwright installs outside PATH.
    "/opt/pw-browsers/chromium",
    # Windows, where the firm's machine is. `shutil.which` finds these by name
    # only if they are on PATH, and the installers do not put them there.
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
)

#: Flags that make a browser a TRANSPORT rather than a session. No profile, no
#: extensions, no stored credentials -- `signed_in_browser` is a different rung
#: of `record.ACCESS` and a different permission, and nothing here may climb to
#: it by accident. `--dump-dom` prints the rendered DOM and exits.
FLAGS = (
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-extensions",
    "--incognito",
    "--dump-dom",
)

#: ADDED ONLY WHEN RUNNING AS ROOT, AND IT IS A REAL WEAKENING. Chromium
#: refuses to start as root at all without it -- found on the first live run,
#: 8 September 2026, and it is exactly the class #344 exists for: decided by the
#: MACHINE rather than by the code, so no fixture test in this suite could have
#: seen it.
#:
#:     ERROR zygote_host_impl_linux.cc: Running as root without --no-sandbox
#:     is not supported.
#:
#: WHAT IS GIVEN UP. The sandbox is what contains a compromised renderer, and
#: this transport fetches URLs A SEARCHER FOUND -- not a fixed allow-list. As
#: root with no sandbox, a renderer exploit is root on that machine. That is a
#: real exposure and not a theoretical one.
#:
#: WHY IT IS CONDITIONAL RATHER THAN ALWAYS. On any machine that is not root --
#: the firm's Windows box included -- the sandbox stays on and nothing is given
#: up. Adding the flag unconditionally would spend the protection everywhere to
#: buy it in one container, which is the shape of every "just make it work"
#: change this record exists to refuse.
#:
#: THE BETTER FIX IS NOT TO RUN AS ROOT, and this comment is not a substitute
#: for it. It is written here rather than in a commit message because the next
#: session to read this file is the one that needs to know.
ROOT_ONLY = ("--no-sandbox",)

#: THE PROXY, WHERE THE MACHINE HAS ONE. Chromium does not read `HTTPS_PROXY`,
#: so on a machine whose egress goes through one it reaches nothing -- and it
#: reports that as a RENDERED ERROR PAGE, which is the trap below. Read from the
#: environment so a machine without one is unaffected.
PROXY_VARS = ("SATC_DESK_PROXY", "HTTPS_PROXY", "https_proxy")

#: CHROMIUM'S OWN ERROR PAGES, WHICH ARRIVE AS A SUCCESSFUL DOM.
#:
#: FOUND ON THE FIRST LIVE RUN, 8 September 2026, and it is a defect in this
#: module rather than a surprise about the world. `--dump-dom` prints whatever
#: was rendered, the browser EXITS 0 having rendered its own error page, and
#: 186,234 bytes of "This site can't be reached ... ERR_CONNECTION_RESET" came
#: back looking exactly like a document.
#:
#: THAT IS THE DANGEROUS SHAPE THIS MODULE'S HEADER IS ABOUT, arriving through
#: the door nothing was watching: `proving` compares our passage against it,
#: does not find it, and returns DIFFERS -- which `ask.answer` reads as
#: `authority_has_moved` and uses to WITHDRAW the answer. A failure that was
#: OURS becomes a published claim about the PUBLISHER.
#:
#: MATCHED ON THE BODY'S CLASS, WHICH IS STRUCTURE AND NOT PROSE. Chromium
#: stamps `<body class="neterror">` and its siblings on every interstitial. A
#: search for `ERR_` in the text would fire on any document that happens to
#: contain those characters, and this repository has twice shipped a guard that
#: read English and went red on documentation.
ERROR_PAGE_CLASSES = (
    "neterror", "ssl", "captive-portal", "main-frame-blocked",
    "safe-browsing-billing", "enterprise-block", "enterprise-warn",
    "bad-clock", "https-only", "insecure-form", "lookalike-url",
    "managed-profile-required",
)

#: Error codes that mean OUR egress refused, not the origin. `fetch.classify`
#: turns the first into `source_blocked_by_us`, whose fix is the allow-list, and
#: everything else into `source_refuses_us`, whose fix is emphatically not.
EGRESS_CODES = ("ERR_TUNNEL_CONNECTION_FAILED", "ERR_PROXY_CONNECTION_FAILED",
                "ERR_BLOCKED_BY_CLIENT", "ERR_BLOCKED_BY_ADMINISTRATOR",
                "ERR_PROXY_AUTH_REQUESTED", "ERR_MANDATORY_PROXY_CONFIGURATION_FAILED")

#: How long one page gets. A publisher that has not answered in this is a
#: `transient` failure and `fetch.fetch` retries the SAME method once.
TIMEOUT = 45


class NoBrowser(RuntimeError):
    """No headless browser on this machine. Names the fix, never guesses one."""


def find(env=None, candidates=None) -> str:
    """The browser to use, or raise saying how to supply one.

    AT CALL TIME AND NEVER AT IMPORT. Every test in this suite imports this
    module; a module-level lookup would make importing it a statement about the
    machine, and the suite runs where there may be no browser at all.
    """
    env = os.environ if env is None else env
    # `candidates` IS INJECTABLE BECAUSE THE LIST HOLDS ABSOLUTE PATHS. Emptying
    # PATH does not make a machine browserless when `/opt/pw-browsers/chromium`
    # is checked by name -- so a test that wanted "no browser anywhere" and set
    # only PATH would find one and pass for the wrong reason. Found by that test
    # failing.
    named = (env.get(ENV_VAR) or "").strip()
    if named:
        if shutil.which(named) or os.path.isfile(named):
            return named
        raise NoBrowser(
            f"{ENV_VAR} is set to {named!r} and there is nothing there. Point "
            f"it at a Chromium or Chrome executable, or unset it and let this "
            f"look in the usual places.")
    for name in (CANDIDATES if candidates is None else candidates):
        found = shutil.which(name) or (name if os.path.isfile(name) else "")
        if found:
            return found
    raise NoBrowser(
        "no headless browser found. The firm's answer on 8 September 2026 was "
        "a REAL headless browser rather than a client claiming to be one, so "
        "there is no fallback here by design: install Chromium or Chrome, or "
        f"set {ENV_VAR} to one. Until then a citation no desk holds cannot be "
        "proved, and it refuses rather than being served on our own word.")


def command(url: str, binary: str, *, user_data_dir: str = "",
            proxy: str = "") -> list[str]:
    """The exact argv. Built here so a test can read it without launching one."""
    if not str(url).strip():
        raise ValueError("no url to fetch")
    out = [binary, *FLAGS]
    # `geteuid` IS ABSENT ON WINDOWS, which is where the firm's machine is. A
    # bare `os.geteuid()` here would be an AttributeError on the one platform
    # that never needs the flag.
    if getattr(os, "geteuid", lambda: 1)() == 0:
        out += list(ROOT_ONLY)
    if proxy:
        out.append(f"--proxy-server={proxy}")
    if user_data_dir:
        out.append(f"--user-data-dir={user_data_dir}")
    out.append(url)
    return out


def _landed(dom: str, asked: str) -> str:
    """Where the page says it is, falling back to what we asked for.

    THE WHOLE POINT OF THIS TRANSPORT, and the field the guard in `proving`
    depends on. Chromium's `--dump-dom` prints the DOM and not the final URL, so
    it is read out of the document: a bounce lands on a page whose own canonical
    link or base href names the interstitial's host. Where the document says
    nothing, the requested URL is returned -- which is honest (we cannot tell)
    and leaves `proving`'s landed-host check comparing a host with itself, i.e.
    silent. That is a real limit of this method and it is why #344 exists.
    """
    import re
    for pattern in (r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)',
                    r'<base[^>]+href=["\']([^"\']+)'):
        m = re.search(pattern, dom, re.I)
        if m and m.group(1).strip().startswith("http"):
            return m.group(1).strip()
    return asked


def transport(source, access="", *, binary: str = "", run=None) -> Response:
    """Fetch this source's page with a real browser. The `fetch` signature.

    `run` IS INJECTED FOR TESTS AND FOR NOTHING ELSE. The suite replaces the
    socket layer, so nothing here can reach a network in CI even by mistake;
    what a test can do is check the SHAPE -- that the argv is what it claims,
    that the landed URL is read back, that the three failures are told apart.
    Whether a real publisher serves a real browser the real document is #344.
    """
    url = getattr(source, "url", "") or str(source)
    binary = binary or find()
    runner = run or _run
    proxy = next((v for v in (os.environ.get(n) for n in PROXY_VARS) if v), "")
    with tempfile.TemporaryDirectory(prefix="satc-desk-") as profile:
        argv = command(url, binary, user_data_dir=profile, proxy=proxy)
        return runner(argv, url)


def _run(argv, url, *, launch=None) -> Response:
    """Launch it, then read what came back. Two jobs, split on purpose.

    THE SPLIT IS WHAT MAKES THIS TESTABLE AT ALL. Reading a completed process
    is decided entirely by the code; launching one is decided by the machine.
    Patching `subprocess.run` to test the first would drag `unittest.mock` in,
    which imports `asyncio`, which imports `ssl` -- and this suite replaces the
    socket layer, so `ssl` dies on import. `comparing.py` records the same
    collision from the other direction. So the interpretation is its own
    function and the tests call it directly.
    """
    return _read((launch or _launch)(argv), url)


def _launch(argv):
    """One browser, once. Raises the two failures that are ours, not theirs.

    `TimeoutError` is in `fetch.TRANSIENT_ERRORS`, so a slow publisher is
    retried by the SAME method rather than escalated to a different one -- a
    different client is a different permission and a timeout is not a reason to
    take one.
    """
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              timeout=TIMEOUT, check=False,
                              encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"the browser did not finish in {TIMEOUT}s") from exc
    except OSError as exc:
        raise NoBrowser(f"could not launch {argv[0]!r}: {exc}") from exc


def _read(done, url) -> Response:
    """What a finished browser run means. Decided by the code, so tested.

    AN UNREACHABLE ORIGIN RAISES RATHER THAN RETURNING AN EMPTY BODY. An empty
    body reaches `proving` as a document that does not contain our passage,
    which is DIFFERS, which `ask.answer` turns into `authority_has_moved` -- a
    claim about the PUBLISHER made out of a failure that was ours.
    """
    dom, err = done.stdout or "", (done.stderr or "")
    if done.returncode != 0 and not dom.strip():
        # OUR OWN EGRESS, TOLD APART FROM THE ORIGIN'S REFUSAL. `fetch.classify`
        # turns `egress_blocked` into `source_blocked_by_us`, whose fix is the
        # allow-list, and everything else into `source_refuses_us`, whose fix is
        # emphatically not. Getting this backwards sent a person to change a
        # setting that was already correct, and the record says so.
        blocked = any(m in err.lower() for m in (
            "err_blocked_by_client", "err_blocked_by_administrator",
            "proxy", "err_tunnel_connection_failed"))
        if blocked:
            return Response(status=0, body="", egress_blocked=True, url=url)
        raise ConnectionError(
            f"the browser exited {done.returncode} with no page: "
            f"{' '.join(err.split())[:300]}")

    if not dom.strip():
        # A PAGE WITH NOTHING IN IT IS NOT A DOCUMENT AND MUST NOT LOOK LIKE
        # ONE. `fetch.classify` calls this `empty`; here there is no heavier
        # client left to escalate to, so it raises.
        raise ConnectionError(
            "the browser returned an empty document; there is no heavier "
            "client than this one, so nothing further can be tried")

    if (code := error_page(dom)) is not None:
        # THE BROWSER EXITED 0 AND RENDERED ITS OWN FAILURE. Everything below
        # this line would otherwise treat it as the publisher's document.
        if any(c in code for c in EGRESS_CODES):
            return Response(status=0, body="", egress_blocked=True, url=url)
        raise ConnectionError(
            f"the browser rendered its own error page for {url}"
            + (f" ({code})" if code else "")
            + ". Nothing here is a finding about the publisher — it is a "
              "finding about this fetch, and serving it as a document would "
              "withdraw the answer as though the rule had moved.")

    return Response(status=200, body=dom, url=_landed(dom, url),
                    headers=(("x-satc-transport", "headless-browser"),))


def error_page(dom: str):
    """The error code when this DOM is one of Chromium's own pages, else None.

    RETURNS A STRING THAT MAY BE EMPTY, so "an error page with no code found"
    and "not an error page" stay different answers. A bare boolean collapsed
    them, and the empty case is the one where a reader most needs telling that
    the page was ours rather than the publisher's.
    """
    import re
    m = re.search(r"<body[^>]*\bclass=[\"']([^\"']*)[\"']", dom, re.I)
    if not m:
        return None
    classes = set(m.group(1).lower().split())
    if not classes & set(ERROR_PAGE_CLASSES):
        return None
    found = re.search(r"\bERR_[A-Z0-9_]+", dom)
    return found.group(0) if found else ""


def as_text(resp: Response):
    """What `proving.prove_passage` reads off a transport's reply.

    `proving` accepts anything carrying `.text`; `fetch.Response` carries
    `.body`. This adapts one to the other without either learning about the
    other, and `.url` travels so the landed-host check keeps working.
    """
    class _Reply:
        text = resp.body
        body = resp.body.encode("utf-8")
        url = resp.url
        nbytes = len(resp.body.encode("utf-8"))
    return _Reply()


def for_proving(*, binary: str = "", run=None):
    """A transport in the shape `proving` wants: `(source, citation) -> reply`.

    TWO SHAPES EXIST AND THEY ARE NOT THE SAME. `fetch.fetch` passes
    `(source, access)`; `proving.prove_passage` passes `(source, citation)` and
    reads `.text`. Rather than teach either about the other, this wraps.
    """
    def go(source, citation=""):
        return as_text(transport(source, binary=binary, run=run))
    return go
