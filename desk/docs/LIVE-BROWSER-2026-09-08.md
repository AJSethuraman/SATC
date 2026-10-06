# The first live run of the browser transport — what it found, and what it did not

**8 September 2026, desk 0.15.1, in the cloud container — NOT on the Forge.**
This is not #344. #344 is the run on the firm's own machine, against a real
publisher, end to end through a desk. This is the run that happened first
because sending someone else an untested transport is the thing this record
exists to stop.

It is written up because it **failed**, twice for good reasons and once for a
reason that is not ours — and the acceptance criterion for that class of run is
that *"a refusal or a failure is written up as a finding rather than retried
until it looks good"*.

---

## Two defects in code that had 20 green tests

Both were in `browser.py` as first committed. Neither could have been found by
anything in this repository, because both are decided by the machine rather than
by the code — the class the desk named on 8 September:

> *"A CONTROL WHOSE OUTCOME IS DECIDED BY THE ENVIRONMENT RATHER THAN BY THE
> CODE. Mutation cannot catch these, and that is precisely why they survive —
> you are mutating the code, and the code is not what is deciding."*

### 1. It would not start at all

```
ERROR zygote_host_impl_linux.cc:101: Running as root without --no-sandbox
is not supported.
```

Chromium refuses to launch as root. `--no-sandbox` is now added **only when the
process is root** — a real weakening, taken narrowly. The sandbox is what
contains a compromised renderer, and this transport fetches URLs a *searcher*
found rather than a fixed list; as root without it, a renderer exploit is root
on that machine. On any machine that is not root — the firm's included — nothing
is given up. **The better fix is not to run as root**, and the conditional is
not a substitute for it.

### 2. The browser's own error page came back as a document

This is the serious one, and it is the exact shape `browser.py`'s own header
warns about arriving through a door nothing was watching.

`--dump-dom` prints whatever was rendered. When the fetch fails, Chromium
renders **its own error page** and exits **0**. So:

```
bytes = 186,234        landed = www.ecfr.gov (the right host)
visible text = "This site can't be reached ... ERR_CONNECTION_RESET"
```

A full DOM, a successful exit, the correct landed host — and `proving` compares
our passage against it, does not find it, and returns `DIFFERS`, which
`ask.answer` reads as `authority_has_moved` and uses to **withdraw the answer**.
A failure that was *ours* becomes a published claim about the *publisher*.

Detected on the **body's class** (`neterror`, `ssl`, `main-frame-blocked`, …),
which is structure. A search for `ERR_` in the text would fire on any document
containing those characters — and this repository has twice shipped a guard that
read English and went red on its own documentation.

---

## What the run could not establish, and why

**The browser never reached ecfr.gov from this container.** The relay drops
Chromium's tunnel:

```
ws_closed_mid_exchange  www.ecfr.gov:443
tunnel closed (code 1006) after 6s; 1,760 B sent, 39 B received
```

Tried and did not help: `--proxy-server` pointed at the agent proxy,
`--disable-quic`, `--disable-http2`.

**It is not ecfr.gov refusing us, and that was checked rather than assumed.**
`curl` through the same proxy, with a browser user-agent:

```
http=200   bytes=558,400
url=https://www.ecfr.gov/current/title-26/chapter-I/subchapter-A/part-1/
    subject-group-ECFR210006225231fb0/section-1.263(a)-2
passage "must capitalize amounts paid to acquire or produce" -> PRESENT
```

558,400 bytes against the 584,798 the firm measured on their own machine, and
the passage is there. So the publisher serves a browser-shaped client the real
document; **this container's relay cannot carry a browser.**

Worth noting for the landed-host check: that URL **redirects** to a much longer
canonical path on the same host. The check compares hosts rather than URLs
precisely so a publisher's own canonicalisation is not read as a bounce, and
this is that case occurring in the wild.

---

## What CI covers, and what it does not

Said plainly, without dressing one up as the other.

| | Covered by | |
|---|---|---|
| the argv built, the profile flags, the proxy flag | CI | 27 tests |
| the landed URL read back rather than assumed | CI | fixture |
| an error page told apart from a document | CI | **added because of this run** |
| the sandbox dropped only as root | CI | **added because of this run** |
| our egress told apart from the origin refusing | CI | fixture |
| **a real publisher serving a real browser the real document** | **nothing yet** | **#344** |

The last row is the point of the whole transport and no test in this repository
touches it. `conftest.py` replaces the socket layer for every test, autouse, so
the one thing this module exists to do is the one thing CI can never exercise.

**#344 remains open and this run does not reduce it.** What it changes is that
the code the Forge will run has had its first two environment defects removed by
being run, rather than by being read.
