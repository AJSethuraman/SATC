"""The pure-ASCII bundle: the way the tool crosses a bank's email boundary.

Binary files do not survive a corporate DLP filter; plain text does. So the
tool is never sent as a package. `pack bundle CONFIG` writes one ASCII Python
script that carries the package and the question file inside it (gzip, then
base64, so every byte is printable) and nothing else — never the data, which
stays at the desk. On the target, `python build_pack.py --data X --asof D`
unpacks the package beside itself, builds the pack with openpyxl and PyYAML
alone, and prints the SHA-256 of what it wrote. Because the build is
deterministic, that hash equals a build made anywhere else from the same
inputs, which is how a reviewer proves the desk copy is the same deliverable.

Prior art: credit-review-os/src/credit_review/bundle.py, the same contract
section 11 pattern.
"""

from __future__ import annotations

import base64
import gzip
from pathlib import Path

PACKAGE_DIR = Path(__file__).parent

#: The build path travels, and the made-up-book generator so a desk can make a
#: book with a known answer and test on it. The test helpers and the render
#: harness stay home; so does anything importing `formulas`.
BUNDLED = (
    "__init__.py", "config.py", "ingest.py", "population.py", "stats.py", "ladder.py",
    "model.py", "notes.py", "wording.yaml", "workbook.py", "keybank_style.py", "cli.py", "suggest.py",
    "designate.py", "synth.py",
)

_RUNNER = '''#!/usr/bin/env python3
# Portfolio Analysis Pack -- build-on-target bundle. Pure ASCII by construction.
#
#   python {script_name} --synth demo [--loans 40000] [--null | --confounded]
#                                                              # a made-up book with a known answer, to test on
#   python {script_name} --inspect EXTRACT.csv                 # list the columns first
#   python {script_name} --init EXTRACT.csv [-o question.yaml]  # write a question file to fill in
#   python {script_name} --validate EXTRACT.csv --asof YYYY-MM-DD [--config question.yaml]
#   python {script_name} --data EXTRACT.csv --asof YYYY-MM-DD [--config question.yaml]
#                        [--run-date YYYY-MM-DD] [-o OUT.xlsx]
#
# Needs: Python 3.10+, openpyxl, PyYAML   (pip install openpyxl PyYAML)
# Carries: the analysis_pack package and the question file `{config_name}`, which
# is used when --config names none. Never the data. Any extract: designate its
# columns in a question file beside this script, and nothing leaves the desk.
import base64, gzip, hashlib, os, sys

FILES = {files_literal}

CONFIG_NAME = {config_name!r}


def _unpack():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analysis_pack_bundle_src")
    for relpath, blob in FILES.items():
        dest = os.path.join(root, *relpath.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as fh:
            fh.write(gzip.decompress(base64.b64decode(blob)))
    return root


def main(argv):
    root = _unpack()
    sys.path.insert(0, root)
    from analysis_pack.cli import main as pack_main
    config_path = os.path.join(root, "question", CONFIG_NAME)
    args = list(argv)
    if "--config" in args:
        i = args.index("--config")
        if i + 1 >= len(args):
            print("--config needs the path of a question file", file=sys.stderr)
            return 1
        config_path = args[i + 1]
        del args[i:i + 2]
    if args and args[0] == "--synth":
        if len(args) < 2:
            print("--synth needs a folder to write the made-up book into", file=sys.stderr)
            return 1
        return pack_main(["synth", "--out", args[1]] + args[2:])
    if args and args[0] == "--inspect":
        return pack_main(["inspect"] + args[1:])
    if args and args[0] == "--init":
        return pack_main(["init"] + args[1:])
    if args and args[0] == "--validate":
        rest = args[1:]
        data = rest[0]
        return pack_main(["validate", config_path, "--data", data] + rest[1:])
    rc = pack_main(["build", config_path] + args)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


def _blob(data: bytes) -> str:
    return base64.b64encode(gzip.compress(data, mtime=0)).decode("ascii")


def make_bundle(config_path: str | Path, out_path: str | Path | None = None) -> Path:
    """Write the bundle script. The config and any `groups_file` it names go
    in beside the package under `question/`; the data never does."""
    import yaml
    cfg_path = Path(config_path)
    files: dict[str, str] = {}
    for name in BUNDLED:
        files[f"analysis_pack/{name}"] = _blob((PACKAGE_DIR / name).read_bytes())
    files[f"question/{cfg_path.name}"] = _blob(cfg_path.read_bytes())
    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    for spec in (raw.get("fields") or {}).values():
        steps = spec.get("derive") if isinstance(spec, dict) else None
        steps = steps if isinstance(steps, list) else ([steps] if steps else [])
        for step in steps:
            if isinstance(step, dict) and step.get("groups_file"):
                gp = cfg_path.parent / str(step["groups_file"])
                files[f"question/{step['groups_file']}"] = _blob(gp.read_bytes())
    lines = ["{"]
    for k in sorted(files):
        lines.append(f"    {k!r}: {files[k]!r},")
    lines.append("}")
    script = _RUNNER.format(script_name=(Path(out_path).name if out_path else "build_pack.py"),
                            config_name=cfg_path.name, files_literal="\n".join(lines))
    script.encode("ascii")            # raises if anything non-ASCII slipped in
    out = Path(out_path) if out_path else cfg_path.parent / "build_pack.py"
    out.write_text(script, encoding="ascii", newline="\n")
    return out
