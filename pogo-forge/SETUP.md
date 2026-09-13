# Setting up on the Forge

## First: get the files there

Download the `pogo-forge` folder from the chat and put it somewhere on the
Forge — say `C:\srv\pogo-forge`. Don't have Claude Code rewrite it from
scratch; the detector thresholds and the extracted game data are the result of
a lot of testing and would not survive being retyped.

Check you have all eleven files plus `static/index.html` before starting.

## Quickstart, by hand

```
cd C:\srv\pogo-forge
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then from the Forge itself, open `http://localhost:8737`. If that works, the
app is fine and everything left is networking.

## The four things that will actually bite

**ffmpeg is not bundled.** The Triage tab's video path shells out to `ffmpeg`
and there is no Windows fallback. Screenshots work without it; recordings fail
with a confusing error. Install it and confirm `ffmpeg -version` resolves on
PATH:

```
winget install Gyan.FFmpeg
```

**Windows Firewall blocks inbound 8737 by default.** The app binds `0.0.0.0`,
so this is the usual reason "it works on the Forge but not on my phone." Allow
it on the Tailscale interface only — not on your LAN profile, and never on
public:

```
New-NetFirewallRule -DisplayName "pogo-forge" -Direction Inbound `
  -LocalPort 8737 -Protocol TCP -Action Allow -InterfaceAlias "Tailscale"
```

**MagicDNS name.** `tailscale status` gives the Forge's name. The phone URL is
`http://<that-name>:8737`. Plain HTTP over the tailnet is fine — it is already
an encrypted tunnel — but that also means no HTTPS, so don't expose this port
anywhere else.

**Where the database lives.** `pogo-forge.db` is created next to `app.py` on
first run. Override with the `POGO_FORGE_DB` environment variable if you want
it on the mirrored volume with everything else worth keeping. It is a normal
SQLite file; back it up by copying it.

## Keeping it running

Task Scheduler is enough: trigger At startup, action
`C:\srv\pogo-forge\.venv\Scripts\python.exe` with argument `app.py` and Start
in set to the project folder. Tick "Run whether user is logged on or not."

NSSM is nicer if you want real service semantics and automatic restart, but
it's not necessary for something only you hit.

## One thing to decide

Your Claude Code sandbox runs under Hyper-V. If you set this up from inside
that VM, the app will be listening on the VM's interface, not the host's, and
your phone won't reach it over the host's tailnet name. Either run the service
on the host, or expose the VM properly. Worth settling before debugging
networking for an hour.

## Handoff prompt for Claude Code

Paste this once the folder is on the Forge:

> I have a Python project at `C:\srv\pogo-forge` — a local FastAPI app I want
> reachable from my phone over Tailscale. Read `README.md` and `SETUP.md`
> first, then:
>
> 1. Create a venv and install `requirements.txt`.
> 2. Verify `ffmpeg` is on PATH; install it via winget if not.
> 3. Start the app and confirm `http://localhost:8737` serves the UI and
>    `http://localhost:8737/api/plan` returns JSON.
> 4. Add a Windows Firewall rule allowing inbound TCP 8737 on the Tailscale
>    interface only.
> 5. Tell me the Forge's MagicDNS name and the exact URL to open on my phone.
> 6. Set it up under Task Scheduler to start at boot.
>
> Don't modify `appraisal.py`, `costs.py`, `pvp.py`, or `gamedata.json` — the
> thresholds and data in those are tested and I don't want them adjusted as
> part of setup. If something doesn't work, tell me what failed rather than
> changing those files to route around it.

## First thing to try once it's up

Cost tab, type `Ralts`, CP `296`, HP `66`, then drop in the screenshot you
took at Rheinfall. It should read 13/14/13 and confirm level 20. If it does,
the whole pipeline is working.
