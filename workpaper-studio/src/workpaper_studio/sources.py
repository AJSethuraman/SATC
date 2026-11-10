"""Where the work list comes from: the organization's master database, read and never written.

The owner's work version has the workbook query the database directly. Here the installation names the source in
`sources.json` (beside the data), and a tool pack's `intake` says which of its columns fill which of the tool's
fields and table rows. Two kinds of source are supported: a SQLite database (opened read-only, standing in for any
SQL database the organization runs) and CSV files exported from one. Nothing is ever written back to the source.

    {"Credit file review": {"kind": "sqlite", "path": "master.db", "lines": "credit_lines",
                            "tables": {"facilities": "credit_facilities"}}}
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path

IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SourceError(ValueError):
    pass


def configured(data_dir):
    p = Path(data_dir) / "sources.json"
    return json.loads(p.read_text()) if p.exists() else {}


def describe(cfg):
    if cfg["kind"] == "sqlite":
        return f'{cfg["path"]}, table {cfg["lines"]}'
    return cfg["lines"]


def read(cfg, data_dir):
    """(lines, child tables) as lists of dicts, exactly as the source holds them."""
    base = Path(data_dir)
    kind = cfg.get("kind")
    if kind == "sqlite":
        path = base / cfg["path"]
        if not path.exists():
            raise SourceError(f"The master database {cfg['path']} is not where the installation says it is.")
        for t in [cfg["lines"], *cfg.get("tables", {}).values()]:
            if not IDENT.match(t):
                raise SourceError(f"{t!r} is not a table name this will read.")
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)     # read-only: the master database is never written
        db.row_factory = sqlite3.Row
        try:
            lines = [dict(r) for r in db.execute(f"SELECT * FROM {cfg['lines']}")]
            children = {name: [dict(r) for r in db.execute(f"SELECT * FROM {t}")] for name, t in cfg.get("tables", {}).items()}
        except sqlite3.Error as e:
            raise SourceError(f"The master database could not be read: {e}.") from None
        finally:
            db.close()
        return lines, children
    if kind == "csv":
        def rows(name):
            p = base / name
            if not p.exists():
                raise SourceError(f"The file {name} is not where the installation says it is.")
            with p.open(newline="", encoding="utf-8-sig") as fh:
                return list(csv.DictReader(fh))
        return rows(cfg["lines"]), {name: rows(f) for name, f in cfg.get("tables", {}).items()}
    raise SourceError(f"A source must be sqlite or csv, not {kind!r}.")
