# Windows app packaging (zero-install build)

This directory builds a **single, double-clickable `SATC.exe`** with
[PyInstaller](https://pyinstaller.org), so a non-developer can download one file
and run it — no Python, no `pip`, no setup.

Files here:

| File             | Purpose |
|------------------|---------|
| `entry.py`       | Frozen entry point — calls `satc.app.server.main()`. |
| `satc_app.spec`  | PyInstaller spec: bundles the `configs/` tree, the Flask `templates/` and `static/` dirs, and the needed hidden imports into one `SATC` executable. |

When frozen, the app is self-locating:

* **Configs** are read from inside the bundle (`sys._MEIPASS/configs`) — see the
  frozen-aware `CONFIG_ROOT` in `src/satc/config.py`.
* **Data** (the SQLite vault + mart) is written to a per-user, writable directory
  `~/.satc/data` — see the frozen-aware `DEFAULT_DIR` in
  `src/satc/persistence/store.py`. Set `SATC_DATA_DIR` to override.

Nothing changes for the normal dev/test workflow: outside a PyInstaller bundle
the configs and data dir resolve exactly as before.

## Build it locally (on Windows)

From the `satc_system\` directory:

```bat
pip install -e ".[local,build]"     REM installs the app deps + pyinstaller
pyinstaller packaging\satc_app.spec
```

The result is `dist\SATC.exe`. Double-click it (or run `dist\SATC.exe`). It picks a
free port, starts the local web server, and opens the app in your browser. Stop it
by closing the console window.

Useful environment toggles when launching:

* `SATC_NO_BROWSER=1` — don't auto-open a browser (handy for smoke tests).
* `SATC_PORT=5099` — prefer a specific port (falls back to a free one if taken).
* `SATC_DATA_DIR=C:\path` — store the databases somewhere other than `~/.satc/data`.

## What CI produces

`.github/workflows/build-desktop-app.yml` builds `SATC.exe` on `windows-latest`:

* **Triggers:** manual (`workflow_dispatch`) and version tags (`push` of `v*`).
* **The job:** checks out the repo, sets up Python 3.11, installs `.[local,build]`,
  runs `pyinstaller packaging/satc_app.spec`, and uploads `dist/SATC.exe` as a
  build artifact.
* **On a tag push** (e.g. `v0.1.1`): `SATC.exe` is also attached to the matching
  GitHub Release.

So cutting a release is: push a `v*` tag (or publish a Release in the UI), wait for
the build, and the ready-to-run **`SATC.exe`** appears on the Release page.

> The build is Windows-only by design. PyInstaller is not a cross-compiler, so the
> Windows `.exe` is produced on a Windows runner.
