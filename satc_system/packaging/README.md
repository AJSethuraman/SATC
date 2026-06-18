# Desktop app packaging (zero-install build)

This directory builds a **single, double-clickable executable** of the SATC app
with [PyInstaller](https://pyinstaller.org), so a non-developer can download one
file and run it — no Python, no `pip`, no setup. The executable is named `SATC`.

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

## Build it locally

From the `satc_system/` directory:

```bash
pip install -e ".[local,build]"     # installs the app deps + pyinstaller
pyinstaller packaging/satc_app.spec
```

The result is a single executable:

* macOS / Linux: `dist/SATC`
* Windows: `dist/SATC.exe`

Run it by double-clicking (or `./dist/SATC` from a terminal). It picks a free
port, starts the local web server, and opens the app in your browser. Stop it
with `Ctrl+C` in the console window.

Useful environment toggles when launching:

* `SATC_NO_BROWSER=1` — don't auto-open a browser (handy for smoke tests).
* `SATC_PORT=5099` — prefer a specific port (falls back to a free one if taken).
* `SATC_DATA_DIR=/path` — store the databases somewhere other than `~/.satc/data`.

Quick smoke test (Linux/macOS):

```bash
SATC_NO_BROWSER=1 SATC_PORT=5099 ./dist/SATC &
sleep 4
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5099/   # expect 200
kill %1
```

## What CI produces

`.github/workflows/build-desktop-app.yml` builds the executable on a matrix of
**macOS, Windows, and Linux**:

* **Triggers:** manual (`workflow_dispatch`) and version tags (`push` of `v*`).
* **Each OS job:** checks out the repo, sets up Python 3.11, installs
  `.[local,build]`, runs `pyinstaller packaging/satc_app.spec`, and uploads the
  resulting `dist/SATC*` as a build artifact (`SATC-<os>`).
* **On a tag push** (e.g. `v1.0.0`): the binaries are also attached to the
  matching GitHub Release.

So cutting a release is: push a `v*` tag, wait for the three jobs, and the
ready-to-run `SATC` executables appear on the Release page — one download per OS.
