"""Every function this app calls has to exist.

THIS EXISTS BECAUSE FIVE FUNCTIONS WERE DELETED AND NOTHING NOTICED. Rewriting
the head of `stripe_utils.py` to carry the currency allowlist took `configure`,
`create_connect_account`, `create_account_link`, `get_account` and
`_platform_fee_cents` out with it. `app.py` calls four of them and
`create_checkout_session` calls the fifth. Connecting a Stripe account raised
NameError; creating a Checkout Session raised NameError. The entire payment
feature was dead for three commits and the suite was green the whole time.

It was green because a suite tests what it can call, and not one of those five
can be called without talking to Stripe. They were covered by nothing, so
"the tests pass" said nothing whatever about them.

Two checks, both deliberately dumb. Neither says anything about behaviour;
they say the wiring is connected, which is the failure that actually happened.

1. **Across modules** — every `module.attribute` the app reaches for resolves.
2. **Within a module** — every bare `name()` call resolves somewhere in its
   scope chain: locals, enclosing functions (this codebase is full of closures
   defined inside `create_app`), module globals, builtins.
3. **Across an import** — every `from <ours> import <name>` resolves, including
   the function-local ones. Checks 1 and 2 both walk past those: check 2 binds
   the imported name and asks no further, and check 1 only sees
   `module.attribute`. So deleting `pdf._business_context`, imported inside
   `app.generate_pdf`, left both green while downloading a PDF raised
   ImportError.

Both were run against a checkout with the five functions removed and both
failed; that is why they are here rather than as a note in a commit message.

What still slips past: `getattr(module, computed_name)`, a name called only
from a template, and anything reached through `**kwargs`. None of those is
used here today. If one appears, this file needs to grow rather than be
trusted as complete.
"""
import ast
import builtins
import importlib
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent

#: The modules this app owns. A missing attribute on one of these is our bug;
#: on `stripe` or `flask` it is a version problem and a different question.
OURS = (
    "stripe_utils", "email_utils", "pdf", "models", "designs", "currencies",
    "helpers", "config", "api", "app",
)

#: The files that do the reaching.
CALLERS = ("app.py", "api.py", "pdf.py", "exercise.py", "models.py")


# --- one: across modules ---------------------------------------------------

def cross_module_references(path):
    """Every `module.attribute` in this file, as (module, attribute, line)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.asname or alias.name)
    return {
        (node.value.id, node.attr, node.lineno)
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in OURS
        and node.value.id in imported
    }


ALL_REFERENCES = sorted(
    (caller, module, attribute, line)
    for caller in CALLERS
    for module, attribute, line in cross_module_references(ROOT / caller)
)


def test_the_scan_found_something():
    """A scan that silently matches nothing is a test that always passes."""
    assert len(ALL_REFERENCES) > 20
    assert any(m == "stripe_utils" for _, m, _, _ in ALL_REFERENCES)


@pytest.mark.parametrize(
    "caller, module, attribute, line",
    ALL_REFERENCES,
    ids=[f"{c}:{ln}:{m}.{a}" for c, m, a, ln in ALL_REFERENCES],
)
def test_the_attribute_exists(caller, module, attribute, line):
    assert hasattr(importlib.import_module(module), attribute), (
        f"{caller}:{line} calls {module}.{attribute}, which does not exist"
    )


# --- two: within a module --------------------------------------------------

def _binds_directly(node):
    """Names bound in THIS scope, not descending into nested ones.

    Python's scoping is the whole difficulty here: a first attempt looked only
    at the function itself and reported 37 false positives, every one of them
    a closure calling a sibling defined in `create_app`. A scope is a chain,
    so the check has to be one too.
    """
    names = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        args = node.args
        names |= {a.arg for a in args.posonlyargs + args.args + args.kwonlyargs}
        if args.vararg:
            names.add(args.vararg.arg)
        if args.kwarg:
            names.add(args.kwarg.arg)
    stack = list(ast.iter_child_nodes(node))
    while stack:
        child = stack.pop()
        if isinstance(
            child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            names.add(child.name)
            continue                      # its body is a scope of its own
        if isinstance(child, ast.Lambda):
            continue
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
            for alias in child.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(child, ast.ExceptHandler) and child.name:
            names.add(child.name)
        elif isinstance(child, (ast.Global, ast.Nonlocal)):
            names.update(child.names)
        stack.extend(ast.iter_child_nodes(child))
    return names


def unresolved_calls(module_name):
    """Bare `name()` calls that resolve nowhere in their scope chain."""
    module = importlib.import_module(module_name)
    tree = ast.parse((ROOT / f"{module_name}.py").read_text(encoding="utf-8"))
    found = []

    def walk(node, chain):
        if isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
        ):
            inner = chain + [_binds_directly(node)]
            for child in ast.iter_child_nodes(node):
                walk(child, inner)
            return
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if not any(name in scope for scope in chain):
                found.append(f"{module_name}.py:{node.lineno} calls {name}()")
        for child in ast.iter_child_nodes(node):
            walk(child, chain)

    base = [set(vars(module)) | set(dir(builtins))]
    for child in ast.iter_child_nodes(tree):
        walk(child, base)
    return sorted(set(found))


@pytest.mark.parametrize("module_name", OURS)
def test_every_call_in_the_module_resolves(module_name):
    unresolved = unresolved_calls(module_name)
    assert not unresolved, "\n".join(unresolved)


# --- three: names imported out of one of our modules --------------------
#
# THE FIRST TWO SCANS BOTH MISS A FUNCTION-LOCAL `from … import …`, and this
# codebase is full of them. `_binds_directly` adds an imported name to the
# scope so the call resolves, and the cross-module scan only looks at
# `module.attribute`, so deleting `pdf._business_context` — imported inside
# `app.generate_pdf` — left both scans green while the route raised
# ImportError the moment anybody downloaded a PDF. That is the same class of
# deletion this file exists to stop, walking straight past it.
#
# Raised by Codex on PR #289, round six.

def imported_names(path):
    """Every `from <ours> import <name>`, as (module, name, line)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or node.level:
            continue                       # relative imports are not ours
        if node.module not in OURS:
            continue
        for alias in node.names:
            if alias.name == "*":
                continue                   # nothing to resolve
            found.add((node.module, alias.name, node.lineno))
    return found


ALL_IMPORTS = sorted(
    (str(path.name), module, name, line)
    for path in (ROOT / f"{m}.py" for m in OURS)
    if path.exists()
    for module, name, line in imported_names(path)
)


def test_the_import_scan_found_something():
    """The scan that always passes is the scan nobody notices is broken."""
    assert len(ALL_IMPORTS) > 5
    assert any(m == "pdf" for _, m, _, _ in ALL_IMPORTS)


@pytest.mark.parametrize(
    "caller, module, name, line",
    ALL_IMPORTS,
    ids=[f"{c}:{ln}:from {m} import {n}" for c, m, n, ln in ALL_IMPORTS],
)
def test_the_imported_name_exists(caller, module, name, line):
    assert hasattr(importlib.import_module(module), name), (
        f"{caller}:{line} imports {name} from {module}, which does not have it"
    )


def test_the_five_that_were_lost_are_back():
    """Named, so the incident is not just a shape in a parametrised list."""
    import stripe_utils

    for name in (
        "configure",
        "create_connect_account",
        "create_account_link",
        "get_account",
        "_platform_fee_cents",
    ):
        assert hasattr(stripe_utils, name), name


def test_no_function_in_app_py_is_defined_twice():
    """A second `def` of the same name silently replaces the first, and Flask
    only objects when two routes share an endpoint name — which a rewrite that
    drops one of them does not trigger."""
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    names = re.findall(r"^\s*def (\w+)\(", source, re.M)
    duplicates = {n for n in names if names.count(n) > 1}
    assert not duplicates, f"defined more than once in app.py: {duplicates}"
