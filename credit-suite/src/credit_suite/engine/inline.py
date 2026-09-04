"""The build-time inliner: a shared library, shipped as one self-contained file.

TEMPLATE_CONTRACT section 11 exists because of a plain fact about corporate
email: binary attachments are rewritten or blocked, and plain text is not. So the
workbook is never transmitted -- a single pure-ASCII script is, and the workbook
is *built* where it will live.

Consolidation put that property at risk. A monitor used to carry a hand-copied
runner it could embed wholesale; now its code is spread across
``credit_suite.engine.*`` and ``credit_suite.sources.<name>.*``. This module
closes that gap: it walks the import graph from a source's entry modules,
collects every ``credit_suite`` module reachable from them, and emits them into
one file that registers them in ``sys.modules`` under their real dotted names
before executing them in dependency order. Because the names are real, the
inlined modules' own ``from credit_suite.engine.config import ...`` statements
resolve against the registry rather than the filesystem -- no import rewriting,
so the code that ships is the code that was tested.

**Determinism is a requirement, not a nicety.** A bundle that differs run to run
cannot be diffed, cannot be checksummed by a recipient, and makes "did this
change?" unanswerable. ``gzip`` writes a timestamp into its header by default,
which quietly breaks that; :func:`encode` pins it to zero.
"""

from __future__ import annotations

import ast
import base64
import gzip
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

PACKAGE = "credit_suite"


class InlineError(RuntimeError):
    """The bundle could not be built. Never a partial bundle."""


# --------------------------------------------------------------------------
# deterministic encoding
# --------------------------------------------------------------------------

def encode(data: bytes) -> str:
    """gzip + base64, byte-identical for identical input.

    ``gzip.compress`` stamps the current time into the header, so two runs over
    the same bytes produce different output. ``mtime=0`` removes the clock; the
    fixed compresslevel removes the other source of drift.
    """
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=9, mtime=0) as gz:
        gz.write(data)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def decode_expr() -> str:
    """The one-line decoder the emitted bundle carries."""
    return ('def _decode(b):\n'
            '    return gzip.decompress(base64.b64decode(b)).decode("utf-8")')


def chunk(text: str, width: int = 120) -> str:
    """Wrap a base64 blob into quoted lines an email client will not reflow."""
    return "\n".join('    "%s"' % text[i:i + width]
                     for i in range(0, len(text), width))


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------

def package_root() -> Path:
    """The directory containing the ``credit_suite`` package."""
    return Path(sys.modules[PACKAGE].__file__).parent.parent


def _module_path(name: str, root: Optional[Path] = None) -> Path:
    """Resolve a dotted module name to its source file, without importing it."""
    root = root or package_root()
    candidate = root / Path(*name.split("."))
    if candidate.with_suffix(".py").is_file():
        return candidate.with_suffix(".py")
    if (candidate / "__init__.py").is_file():
        return candidate / "__init__.py"
    raise InlineError("cannot locate source for module %r" % name)


def _imported_names(tree: ast.AST, module: str, top_level_only: bool,
                    root: Optional[Path] = None) -> Set[str]:
    """Every ``credit_suite`` module this file imports.

    ``top_level_only`` distinguishes the two questions that look alike. For
    *discovery* we want every import anywhere, including inside functions.
    For *ordering* we want only module-scope imports, because an import inside a
    function has not run yet when the module executes -- which is exactly how a
    deliberate import cycle is broken, and treating it as an ordering constraint
    would report a cycle that does not exist at runtime.
    """
    found: Set[str] = set()
    body = getattr(tree, "body", [])
    nodes = body if top_level_only else ast.walk(tree)
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == PACKAGE:
                    found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:                      # relative import
                parts = module.split(".")[:-node.level]
                base = ".".join(parts + ([node.module] if node.module else []))
            else:
                base = node.module or ""
            if base.split(".")[0] != PACKAGE:
                continue
            found.add(base)
            # `from pkg.mod import thing` may name a SUBMODULE rather than an
            # attribute; include it when such a module exists.
            for alias in node.names:
                candidate = "%s.%s" % (base, alias.name)
                try:
                    _module_path(candidate, root)
                except InlineError:
                    continue
                found.add(candidate)
    return found


def _parents(name: str) -> List[str]:
    """Every package above a module, outermost first."""
    parts = name.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts))]


def discover(roots: Sequence[str],
             root: Optional[Path] = None) -> List[str]:
    """Every ``credit_suite`` module reachable from ``roots``, in execution order.

    Execution order matters: ``from x import y`` needs ``x`` already executed or
    ``y`` will not exist. The order is a topological sort over module-scope
    imports only, with packages placed before their contents.
    """
    seen: Set[str] = set()
    deps: Dict[str, Set[str]] = {}
    queue = list(roots)

    while queue:
        name = queue.pop()
        if name in seen:
            continue
        seen.add(name)
        source = _module_path(name, root).read_text(encoding="utf-8")
        tree = ast.parse(source, filename=name)
        for parent in _parents(name):
            if parent not in seen:
                queue.append(parent)
        for found in _imported_names(tree, name, top_level_only=False,
                                     root=root):
            if found not in seen:
                queue.append(found)
        deps[name] = set(_imported_names(tree, name, top_level_only=True,
                                         root=root))

    # A package must exist before anything inside it.
    for name in list(deps):
        deps[name] |= {p for p in _parents(name) if p in deps}

    ordered: List[str] = []
    placed: Set[str] = set()
    remaining = sorted(deps)
    while remaining:
        ready = [n for n in remaining if deps[n] <= placed]
        if not ready:
            raise InlineError(
                "import cycle among module-scope imports: %s" % remaining)
        for name in ready:                       # sorted -> deterministic
            ordered.append(name)
            placed.add(name)
        remaining = [n for n in remaining if n not in placed]
    return ordered


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

@dataclass
class BundleSpec:
    """What one monitor needs inlined."""

    name: str                       # "fdic"
    workbook: str                   # "Bank_Peer_Monitor"
    roots: Sequence[str]            # entry modules
    layout_module: str
    runner_module: str
    macro_module: str               # the VBA module name
    macro_path: Path
    requirements: str = "pandas>=1.5\nopenpyxl>=3.0\n"
    asof: Optional[str] = None      # pin the demo run, for a reproducible build
    extra_notes: Sequence[str] = field(default_factory=tuple)


def _module_blob(name: str) -> Tuple[str, str]:
    """A module's constant name and its encoded source."""
    const = name.replace(".", "__").upper() + "_B64"
    return const, encode(_module_path(name).read_bytes())


def _emit_modules(modules: Sequence[str], lines: List[str]) -> None:
    for name in modules:
        const, blob = _module_blob(name)
        lines.append("%s = (" % const)
        lines.append(chunk(blob))
        lines.append(")")
        lines.append("")
    lines.append("_SRC = {")
    for name in modules:
        const, _ = _module_blob(name)
        lines.append("    %r: %s," % (name, const))
    lines.append("}")
    lines.append("_ORDER = %r" % (tuple(modules),))
    lines.append("")


LOADER = '''
def _install():
    """Register the inlined modules under their real dotted names.

    Real names matter: the modules' own `from credit_suite... import ...`
    statements then resolve against sys.modules instead of the filesystem, so
    nothing had to be rewritten to travel -- the code that ships is the code
    that was tested.
    """
    for name in _ORDER:
        module = types.ModuleType(name)
        module.__file__ = name.replace(".", "/") + ".py"
        if name in _PACKAGES:
            module.__path__ = []
            module.__package__ = name
        else:
            module.__package__ = name.rpartition(".")[0]
        sys.modules[name] = module
    for name in _ORDER:
        parent, _, leaf = name.rpartition(".")
        if parent:
            setattr(sys.modules[parent], leaf, sys.modules[name])
    for name in _ORDER:
        exec(compile(_decode(_SRC[name]), sys.modules[name].__file__, "exec"),
             sys.modules[name].__dict__)
'''


def _packages(modules: Sequence[str]) -> Tuple[str, ...]:
    return tuple(n for n in modules if _module_path(n).name == "__init__.py")


def render_runner(spec: BundleSpec) -> str:
    """The `_code_py` payload: a self-contained runner.

    This is what the VBA button writes out as `runner.py`. It must run with
    nothing but the documented runtime dependencies present -- no
    ``credit-suite`` on the machine, no folder layout, no PYTHONPATH.
    """
    modules = discover(list(spec.roots))
    lines: List[str] = [
        "#!/usr/bin/env python3",
        '"""%s -- self-contained runner (TEMPLATE_CONTRACT section 11).' % spec.workbook,
        "",
        "Extracted from the workbook's _code_py tab by the ExtractFiles macro.",
        "The shared credit-suite engine is inlined below as gzip+base64, so this",
        "file needs only the documented runtime dependencies -- nothing else has",
        "to be installed and no folder layout is assumed.",
        "",
        "    python -m pip install -r requirements.txt",
        '    python runner.py --workbook "%s.xlsm" --demo' % spec.workbook,
        '"""',
        "import base64, gzip, sys, types",
        "",
    ]
    _emit_modules(modules, lines)
    lines.append("_PACKAGES = %r" % (_packages(modules),))
    lines.append("")
    lines.append(decode_expr())
    lines.append(LOADER)
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    _install()")
    lines.append("    sys.exit(sys.modules[%r].main(sys.argv[1:]))"
                 % spec.runner_module)
    lines.append("")
    text = "\n".join(lines)
    _assert_ascii(text, "runner")
    return text


def render_bundle(spec: BundleSpec) -> str:
    """The emailable builder: one pure-ASCII file that builds everything locally."""
    modules = discover(list(spec.roots))
    runner_source = render_runner(spec)
    # Read as TEXT, not bytes: macro.bas is CRLF on disk, and the
    # file-path route through write_code_tab reads it with universal
    # newlines. Encoding the raw bytes instead left a stray carriage return
    # on the end of every _code_vba cell -- caught by the parity golden,
    # which is exactly the class of difference it exists to catch.
    macro_source = spec.macro_path.read_text(encoding="utf-8")

    lines: List[str] = [
        "#!/usr/bin/env python3",
        '"""One-file builder for %s.' % spec.workbook,
        "",
        "Plain ASCII (the code rides inside as base64), so it survives corporate",
        "email and DLP intact. Run it on the target machine and it BUILDS the",
        "workbook locally -- nothing binary is ever transmitted.",
        "",
        "USAGE (PowerShell):",
        "    python -m pip install pandas openpyxl",
        "    python build_%s.py" % spec.name,
        "",
        "It writes into the current folder:",
        "    %s.xlsm           (macro embedded, demo-populated)" % spec.workbook,
        "    %s_fallback.xlsx  (no VBA; if Excel rejects the .xlsm, open this," % spec.workbook,
        "                      paste macro.bas via Alt+F11, save as .xlsm)",
        "    runner.py, macro.bas, requirements.txt",
        "",
        "Refresh later, with the workbook CLOSED:",
        '    python runner.py --workbook ".\\\\%s.xlsm" --demo' % spec.workbook,
    ]
    lines.extend("    %s" % note for note in spec.extra_notes)
    lines.append('"""')
    lines.append("import base64, gzip, os, sys, types")
    lines.append("")

    _emit_modules(modules, lines)
    lines.append("_PACKAGES = %r" % (_packages(modules),))
    lines.append("")
    lines.append("MACRO_B64 = (")
    lines.append(chunk(encode(macro_source.encode("utf-8"))))
    lines.append(")")
    lines.append("")
    lines.append("RUNNER_B64 = (")
    lines.append(chunk(encode(runner_source.encode("utf-8"))))
    lines.append(")")
    lines.append("")
    lines.append("REQUIREMENTS = %r" % spec.requirements)
    lines.append("")
    lines.append(decode_expr())
    lines.append(LOADER)
    lines.append("")
    lines.append('def _write(path, text):')
    lines.append('    with open(path, "w", encoding="utf-8", newline="\\n") as fh:')
    lines.append('        fh.write(text)')
    lines.append("")
    lines.append("def main():")
    lines.append("    cwd = os.getcwd()")
    lines.append("    # The files the refresh and fallback flows need, first.")
    lines.append('    _write(os.path.join(cwd, "runner.py"), _decode(RUNNER_B64))')
    lines.append('    _write(os.path.join(cwd, "macro.bas"), _decode(MACRO_B64))')
    lines.append('    _write(os.path.join(cwd, "requirements.txt"), REQUIREMENTS)')
    lines.append("    _install()")
    lines.append('    base = os.path.join(cwd, "%s_fallback.xlsx")' % spec.workbook)
    lines.append('    out = os.path.join(cwd, "%s.xlsm")' % spec.workbook)
    lines.append("    layout = sys.modules[%r]" % spec.layout_module)
    lines.append("    runner = sys.modules[%r]" % spec.runner_module)
    lines.append("    package = sys.modules['credit_suite.engine.package']")
    # The inlined layout has no files beside it, so the two source tabs are
    # handed in rather than read off disk -- that is the whole point of a
    # bundle that runs in an empty folder.
    lines.append("    layout.build(base, code_py=_decode(RUNNER_B64),")
    lines.append("                 code_vba=_decode(MACRO_B64))")
    lines.append("    package.assemble(base, out, os.path.join(cwd, 'macro.bas'),")
    lines.append("                     %r)" % spec.macro_module)
    if spec.asof:
        lines.append("    from datetime import date")
        lines.append("    asof = date.fromisoformat(%r)" % spec.asof)
        lines.append("    runner.run(out, demo=True, asof=asof)")
        lines.append("    runner.run(base, demo=True, asof=asof)")
    else:
        lines.append("    runner.run(out, demo=True)")
        lines.append("    runner.run(base, demo=True)")
    lines.append('    print("Built:", out)')
    lines.append('    print("Fallback (no VBA):", base)')
    lines.append('    print("Also wrote runner.py, macro.bas, requirements.txt in", cwd)')
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    try:")
    lines.append("        main()")
    lines.append("    except ImportError as exc:")
    lines.append('        sys.stderr.write("Missing dependency: %s\\n"')
    lines.append('                         "Run: python -m pip install pandas openpyxl\\n" % exc)')
    lines.append("        sys.exit(1)")
    lines.append("")

    text = "\n".join(lines)
    _assert_ascii(text, "bundle")
    return text


def _assert_ascii(text: str, what: str) -> None:
    for index, char in enumerate(text):
        if ord(char) >= 128:
            line = text[:index].count("\n") + 1
            raise InlineError(
                "%s is not pure ASCII: %r at line %d. Contract section 11 -- "
                "anything non-ASCII may not survive the email boundary."
                % (what, char, line))
