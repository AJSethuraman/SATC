"""client-documents' front door: `cli.main([...])`, stdout captured.

Every call passes `--store`. The library defaults are bound at import time
(`engagements.py:28`, `lifecycle.py:161`), so pointing a module-level STORE
somewhere else would not be enough -- the store has to travel on every call.

`invoice` always carries `--no-link`; `event` always carries `--skip-render
--no-pdf --out RUN/out` (without `--out` it writes to `./out/<ref>` relative to
the working directory, `cli.py:1682`). `payments` and `square_setup` are never
called; the guard makes them raise if anything tries.

Output is normalised: the run directory is replaced by `<RUN>` so two runs of
the same seed produce byte-identical evidence.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

from season_sim import guard
from season_sim.doors_satc import Call


class CdDoors:
    def __init__(self, iso, log: list):
        self.store = str(iso.engagements)
        self.out = str(iso.out)
        self.run = str(iso.run)
        self.answers_dir = Path(iso.run) / "answers"
        self.answers_dir.mkdir(parents=True, exist_ok=True)
        self.log = log
        import cli
        self._cli = cli

    def _norm(self, text: str) -> str:
        for form in (self.run, self.run.replace("\\", "/")):
            text = text.replace(form, "<RUN>")
        return text.replace("\\", "/")

    def run_cli(self, argv: list[str], *, log: bool = True) -> tuple[Call, str]:
        buf, err = io.StringIO(), io.StringIO()
        attempts = len(guard.BANNED_ATTEMPTS)
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
            try:
                rc = self._cli.main(argv)
            except SystemExit as exc:          # argparse, or a refusal that exits
                rc = f"exit {exc.code}"
            except guard.SimRefused:
                raise                           # a banned door ends the run; never evidence
            except Exception as exc:            # noqa: BLE001 -- a door that crashes is evidence
                import traceback
                rc = f"exception {type(exc).__name__}"
                print(f"[the command raised] {type(exc).__name__}: {exc}")
                print("".join(traceback.format_exc().splitlines(True)[-4:]))
        if len(guard.BANNED_ATTEMPTS) > attempts:
            # The command swallowed the refusal itself; the count at the ban did not.
            raise guard.SimRefused(f"cli.main({argv[:1]}) tried a banned door: "
                                   f"{guard.BANNED_ATTEMPTS[attempts:]}")
        said = err.getvalue()
        out = self._norm(buf.getvalue() + (f"\n[stderr]\n{said}" if said else ""))
        shown = [self._norm(a) for a in argv]
        call = Call("cli", "cli.main", {"argv": shown}, rc, out[-600:])
        if log:
            self.log.append(call)
        return call, out

    def _answers_file(self, name: str, payload: dict) -> str:
        path = self.answers_dir / f"{name}.json"
        path.write_text(json.dumps(payload, indent=1, sort_keys=True), encoding="utf-8")
        return str(path)

    # -- owner acts -------------------------------------------------------
    def interview(self, ref: str, answers: dict) -> tuple[Call, str]:
        f = self._answers_file(f"interview-{ref}", answers)
        return self.run_cli(["interview", "--answers", f, "--ref", ref, "--store", self.store])

    def returning(self, prior_ref: str, ref: str, answers: dict) -> tuple[Call, str]:
        f = self._answers_file(f"returning-{ref}", answers)
        return self.run_cli(["returning", "--engagement", prior_ref, "--answers", f,
                             "--ref", ref, "--store", self.store])

    def sent(self, ref: str, on: str) -> tuple[Call, str]:
        return self.run_cli(["sign", "--engagement", ref, "--sent", "encyro", "--on", on,
                             "--store", self.store])

    def record_signature(self, ref: str, what: str, on: str, how: str = "e-signed") -> tuple[Call, str]:
        """E-signed through the signing service the pack went out on (`--sent
        encyro`), so it carries the envelope reference the service issued."""
        envelope = f"SIM-ENV-{ref}-{what.split('/')[0].replace(' ', '')}"
        return self.run_cli(["sign", "--engagement", ref, "--record", what, "--on", on,
                             "--how", how, "--reference", envelope, "--store", self.store])

    def event(self, ref: str, kind: str, payload: dict, *, force_reason: str = "") -> tuple[Call, str]:
        f = self._answers_file(f"event-{kind}-{ref}", payload)
        argv = ["event", "--kind", kind, "--engagement", ref, "--answers", f,
                "--skip-render", "--no-pdf", "--out", self.out, "--store", self.store]
        if force_reason:
            argv += ["--force", "--reason", force_reason]
        return self.run_cli(argv)

    def invoice(self, ref: str, number: str, billed: str) -> tuple[Call, str]:
        return self.run_cli(["invoice", "--engagement", ref, "--billed", billed,
                             "--number", number, "--no-link", "--store", self.store])

    def close(self, ref: str, filed: dict) -> tuple[Call, str]:
        f = self._answers_file(f"close-{ref}", filed)
        return self.run_cli(["close", "--engagement", ref, "--filed", f, "--store", self.store])

    def requote(self, ref: str, sets: list[str], reason: str) -> tuple[Call, str]:
        argv = ["requote", "--engagement", ref]
        for s in sets:
            argv += ["--set", s]
        argv += ["--reason", reason, "--store", self.store]
        return self.run_cli(argv)

    def season(self, today: str) -> tuple[Call, str]:
        """A READ, not logged as an owner act."""
        return self.run_cli(["season", "--today", today, "--store", self.store], log=False)
