"""Changing a price — in the file the prices actually live in.

The owner changes rates more often than anything else in this system, and until
now the only way was to open `configs/billing/services.yaml` in an editor. This
module is what a screen calls instead. It is deliberately NOT the pattern the
questionnaire editor uses.

WHY NOT DATABASE OVERRIDES. A row in SQLite that quietly wins over the YAML is a
trap with a long fuse: the owner edits the file — which they have been told is
the source of truth, and which still reads as the source of truth — nothing
changes, and nothing anywhere says why. The file stays the single source of
truth, so a hand edit and a screen edit are the same act by two routes.

WHY NOT RE-SERIALISE. ruamel is not installed, so round-tripping through
`yaml.safe_dump` would drop every comment in these files. In this codebase the
comments ARE the reasoning — read the header of `rate_plans.yaml`: the whole
argument for showing a discount rather than hiding it lives there, and nowhere
else. Destroying it to change one number is a regression, not a reformat. So the
change is surgical: find the line, replace the value on it, leave every other
byte exactly as it was, including line endings, quoting style and the blank
lines. The diff a rate change produces is one line, and reviewable in git.

Which means TWO readers of the same file, and they have to agree. `read_yaml`
says what the file MEANS — which entries exist, in what order. The text scan
says where each of those entries LIVES. If the two lists do not line up, the
edit is refused rather than applied to whatever the text scan happened to land
on: matching the wrong block is the failure that silently reprices the wrong
service, and it would look like a clean one-line diff on the way past.

NEVER LEAVE THE FILE BROKEN. This is the practice's price list; a half-written
one takes down every screen that quotes. The candidate is written to a temp
directory and loaded back through the REAL loader — `load_services` /
`load_plans`, which is where the contingent-fee, unit and range refusals live —
and only a file that loads is moved into place, in one `os.replace`. A rate the
loader would reject never reaches disk (principle 5).

WHO changed it and WHEN are not this module's business. The actor is derived
from the request context, never accepted as an argument (principle 6), so the
route records the history row from `acting_actor()` and the `Edit` returned
here. This layer answers only "what would this change, and did it stick".
"""

from __future__ import annotations

import difflib
import hashlib
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping, get_args

from satc.billing import catalogue
from satc.config import ConfigError, read_yaml


class PriceEditError(ConfigError):
    """An edit to the price list was refused, and the file was not touched.

    Subclasses :class:`ConfigError` so a screen that already catches "the
    billing config will not load" catches "the billing config will not accept
    this" with the same hand — from the owner's side they are the same
    sentence: the price list did not change, and here is what to do about it.
    """


# The two files this module knows how to edit, and how to find one entry in
# each: (filename, the top-level list, the key that identifies an entry).
_FILES: dict[str, tuple[str, str, str]] = {
    "services": ("services.yaml", "services", "code"),
    "plans": ("rate_plans.yaml", "plans", "key"),
}

# What `add_service` will write. Anything else is refused rather than dropped:
# a UI that posts `rate` instead of `standard_rate` would otherwise create a
# service the loader reads as free, which is principle 1 backwards — a value
# invented (zero) out of a field nobody supplied.
_SERVICE_KEYS = ("code", "name", "client_label", "category", "unit",
                 "standard_rate", "description")
_SERVICE_REQUIRED = ("code", "name", "unit", "standard_rate")

_CODE_SHAPE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*$")


@dataclass(frozen=True, slots=True)
class Edit:
    """What one change did: which file, to what, from what, to what.

    This is the record a history row is built from, and it is built from what
    was actually on disk rather than from what the caller asked for — `old` is
    the text that was in the file, not what the screen believed was there.
    """

    file: Path
    subject: str
    """The code or plan key that was edited."""

    field: str
    """`standard_rate`, `discount_pct`, or `service` for a whole new entry."""

    label: str
    """How the entry names itself in the file, so a history row reads in the
    owner's language rather than in codes."""

    old: str
    new: str
    line: int
    """1-based line number of the line that changed (or the first line added)."""

    diff: str
    """The exact change, unified. Empty when nothing changed."""

    stamp: str
    """What the file looks like NOW. A screen hands this back on the next edit
    so a change made in another window cannot be silently overwritten."""

    @property
    def is_change(self) -> bool:
        """False when the file already said this. Re-asking is success, not an
        error (principle 8) — but it is not history, and it did not rewrite the
        file, so nothing downstream should record it."""
        return bool(self.diff)

    def summary(self) -> str:
        """One line carrying its own evidence — principle 13. Two rows in the
        price history never read the same, because each states the numbers."""
        if not self.is_change:
            return f"{self.label} was already {self.new}; nothing changed."
        if self.field == "service":
            return f"Added {self.label} ({self.subject}) at {self.new}"
        moved = "discount" if self.field == "discount_pct" else "standard rate"
        return f"{self.label}: {moved} {self.old} → {self.new}"


# --- the public verbs -------------------------------------------------------


def price_file(which: str, *, config_root: Path | None = None) -> Path:
    """Where the prices of a given kind live."""
    try:
        name = _FILES[which][0]
    except KeyError:
        raise PriceEditError(
            f"There is no price file called {which!r}. It is one of: "
            f"{', '.join(sorted(_FILES))}.") from None
    return catalogue.billing_dir(config_root) / name


def file_stamp(which: str, *, config_root: Path | None = None) -> str:
    """A cheap token for "the file still looks the way you last saw it".

    A screen renders the current rates, the owner leaves the tab open over
    lunch, edits the YAML by hand, then submits the stale form. Handing this
    back as `expected_stamp` turns that from a silent revert into a refusal.
    """
    return _stamp(price_file(which, config_root=config_root))


def set_rate(code: str, new_rate: Decimal | int | str, *,
             config_root: Path | None = None,
             expected_stamp: str | None = None) -> Edit:
    """Change one service's standard rate in `services.yaml`.

    The rate is the STANDARD rate — what the work is worth, before any rate
    plan. Changing it changes nothing about invoices already issued: an
    `InvoiceLine` keeps the rate it was raised at, on the line and in the
    `invoice_lines` table, precisely so a rate that moves in March cannot
    reprice February.
    """
    return _set_value(
        which="services", subject=str(code).strip(), field="standard_rate",
        value=_amount(new_rate, what=f"The rate for {str(code).strip()!r}"),
        config_root=config_root, expected_stamp=expected_stamp)


def set_discount(plan_key: str, new_pct: Decimal | int | str, *,
                 config_root: Path | None = None,
                 expected_stamp: str | None = None) -> Edit:
    """Change one rate plan's discount in `rate_plans.yaml`."""
    return _set_value(
        which="plans", subject=str(plan_key).strip(), field="discount_pct",
        value=_percent(new_pct, plan_key=str(plan_key).strip()),
        config_root=config_root, expected_stamp=expected_stamp)


def add_service(spec: Mapping[str, Any], *, config_root: Path | None = None,
                expected_stamp: str | None = None) -> Edit:
    """Append a new service to the catalogue.

    Appended at the end of the list, in the indentation the file already uses,
    after a blank line — the shape a hand edit would have taken. Everything
    already in the file is untouched.

    An existing code is refused rather than merged. "Already exists as
    requested" is success everywhere else in this system (principle 8), but
    here "as requested" would mean comparing a whole spec against a block that
    may carry hand-written notes this module did not write — so it names the
    verb that does change a price instead of guessing which half wins.
    """
    path = price_file("services", config_root=config_root)
    _refuse_if_bundled(path)
    clean = _check_service_spec(spec)
    text, stamp = _read(path)
    if expected_stamp is not None and expected_stamp != stamp:
        raise _moved_under_you(path)

    lines = _split_lines(text)
    entries, after_last = _read_section(lines, path, "services", "code")
    _agree(entries, _parsed_entries(path, "services", "code"), path, "services")
    code = clean["code"]
    if any(entry.ident == code for entry in entries):
        raise PriceEditError(
            f"There is already a service called {code!r} in {path.name} "
            f"(line {next(e.start + 1 for e in entries if e.ident == code)}). "
            f"To change what it costs, edit that service's rate rather than "
            f"adding a second one — two entries with the same code is the "
            f"state this editor refuses to touch at all.")

    eol = _dominant_eol(text)
    # Shaped like the entry above it: a file the owner still recognises is a
    # file the owner will keep editing by hand, which is the whole premise.
    block = _render_service(clean, indent=entries[-1].dash_indent,
                            key_indent=entries[-1].key_indent, eol=eol)

    head = list(lines[:after_last])
    if head and not head[-1].endswith("\n"):
        # The file ended without a newline. One has to be added or the new
        # entry would be glued onto the last line of the old one.
        head[-1] = head[-1] + eol
    new_lines = head + [eol] + block + list(lines[after_last:])
    new_text = "".join(new_lines)

    stamp_after = _commit(path, new_text, catalogue.load_services, stamp)
    return Edit(
        file=path, subject=code, field="service", label=clean["name"],
        old="", new=f"{_render(clean['standard_rate'])} {clean['unit']}",
        line=after_last + 2, diff=_diff(text, new_text, path), stamp=stamp_after)


# --- changing one value on one line -----------------------------------------


def _set_value(*, which: str, subject: str, field: str, value: Decimal,
               config_root: Path | None, expected_stamp: str | None) -> Edit:
    """The shared body of `set_rate` and `set_discount`.

    Read the file once as text and once as YAML, make the two agree about which
    entry is being edited, replace the value on exactly one line, and only then
    let the real loader decide whether the result is allowed to exist.
    """
    _, section, id_key = _FILES[which]
    path = price_file(which, config_root=config_root)
    _refuse_if_bundled(path)
    text, stamp = _read(path)
    if expected_stamp is not None and expected_stamp != stamp:
        raise _moved_under_you(path)

    lines = _split_lines(text)
    entries, _ = _read_section(lines, path, section, id_key)
    parsed = _parsed_entries(path, section, id_key)
    _agree(entries, parsed, path, section)

    found = [entry for entry in entries if entry.ident == subject]
    if not found:
        raise PriceEditError(
            f"There is no {'service' if which == 'services' else 'rate plan'} "
            f"called {subject!r} in {path.name}. It is one of: "
            f"{', '.join(sorted(e.ident for e in entries))}. Check the spelling, "
            f"or add it to the file first.")
    if len(found) > 1:
        where = ", ".join(str(e.start + 1) for e in found)
        raise PriceEditError(
            f"{subject!r} appears {len(found)} times in {path.name} (lines "
            f"{where}), so there is no telling which one is meant to be the "
            f"price. Nothing was changed. Open {path.name}, delete the entry "
            f"that is wrong, and try again — YAML keeps both, and the loader "
            f"silently uses the last, so this file is already lying to some "
            f"screen.")

    entry = found[0]
    hits = _key_lines(lines, entry, field)
    if not hits:
        raise PriceEditError(
            f"{subject!r} in {path.name} has no {field} line to change (the "
            f"entry starts at line {entry.start + 1}). Add `{field}:` to that "
            f"entry by hand — this editor changes a value that is already "
            f"there rather than deciding where a new one belongs.")
    if len(hits) > 1:
        where = ", ".join(str(h.index + 1) for h in hits)
        raise PriceEditError(
            f"{subject!r} in {path.name} sets {field} more than once (lines "
            f"{where}). Nothing was changed. Delete the line that is wrong — "
            f"the loader uses the last one, which is unlikely to be the one "
            f"anybody is reading.")

    hit = hits[0]
    if not hit.value.strip() or hit.value[:1] in "|>[{&*":
        raise PriceEditError(
            f"{field} for {subject!r} is not a plain number on one line "
            f"({path.name} line {hit.index + 1}). Change it by hand — this "
            f"editor will not guess how to rewrite that.")

    old_text = _unquote(hit.value)
    old_value = _as_decimal(old_text)
    new_text_value = _render(value)
    quote = hit.value[0] if hit.value[:1] in "\"'" else ""
    label = str(parsed[entry.ident].get("name") or entry.ident)

    if old_value is not None and old_value == value:
        # The file already says this. Not an error and not history — and
        # crucially not a write, so the mtime does not move and nothing that
        # watches the file thinks a price changed (principle 8).
        return Edit(file=path, subject=subject, field=field, label=label,
                    old=old_text, new=old_text, line=hit.index + 1, diff="",
                    stamp=stamp)

    new_lines = list(lines)
    new_lines[hit.index] = (hit.head + quote + new_text_value + quote
                            + hit.tail + _eol(lines[hit.index]))
    new_file = "".join(new_lines)
    stamp_after = _commit(path, new_file, _loader_for(which), stamp)
    return Edit(file=path, subject=subject, field=field, label=label,
                old=old_text, new=new_text_value, line=hit.index + 1,
                diff=_diff(text, new_file, path), stamp=stamp_after)


def _loader_for(which: str) -> Callable[[Path], Any]:
    return catalogue.load_services if which == "services" else catalogue.load_plans


# --- writing it down, or not ------------------------------------------------


def _commit(path: Path, after: str, loader: Callable[[Path], Any],
            stamp_before: str) -> str:
    """Put `after` in place of the file at `path` — but only if it loads.

    The candidate goes into a temp directory shaped like a config root, so the
    REAL loader reads it by exactly the route the app does. That is the point:
    the contingent-fee refusal, the unit check and the range checks live in the
    loader, and a second copy of them here would be a second copy to drift.

    The temp directory sits next to the file (rather than in the system temp
    dir) so the final `os.replace` is a rename within one filesystem, which is
    the part that is atomic. A reader mid-swap sees the old file or the new
    one, never half of either.
    """
    holder = Path(tempfile.mkdtemp(prefix=".satc-price-", dir=str(path.parent)))
    try:
        room = holder / "billing"
        room.mkdir()
        candidate = room / path.name
        _write(candidate, after)
        try:
            loader(holder)
        except Exception as refused:  # noqa: BLE001
            # Anything at all. A ConfigError is the loader refusing, which is
            # the expected shape; a TypeError is the loader tripping over a
            # structure it never expected, which means the same thing here —
            # the candidate is not a price list, so it does not become one.
            raise PriceEditError(
                f"That change was NOT saved: {path.name} would no longer load.\n\n"
                f"{refused}\n\n"
                f"The file on disk is exactly as it was. Fix the value and try "
                f"again.") from refused
        if _stamp(path) != stamp_before:
            raise _moved_under_you(path)
        try:
            shutil.copymode(path, candidate)
        except OSError:  # pragma: no cover - permissions are not portable
            pass
        os.replace(candidate, path)
    finally:
        shutil.rmtree(holder, ignore_errors=True)
    # The catalogue notices a changed file on its own (mtime and size), but an
    # edit made in-process can land inside the same clock tick as the read
    # before it. Dropping the cache here makes "the app shows the new price"
    # true immediately rather than usually.
    catalogue.forget_prices()
    return _stamp(path)


def _moved_under_you(path: Path) -> PriceEditError:
    return PriceEditError(
        f"{path.name} changed on disk while this edit was being made, so saving "
        f"would have thrown away whatever the other change was. Nothing was "
        f"written. Reload the prices screen to see what it says now, and make "
        f"the change again.")


def _refuse_if_bundled(path: Path) -> None:
    """A packaged SATC.exe reads its configs from inside the bundle, which is a
    temp directory unpacked at launch and deleted at exit. Writing a price
    there succeeds, shows the new number all afternoon, and is gone tomorrow —
    the silent-loss failure this whole module exists to avoid, so it is refused
    where it can be recognised."""
    if not getattr(sys, "frozen", False):
        return
    bundle = getattr(sys, "_MEIPASS", None)
    if not bundle:
        return
    try:
        path.resolve().relative_to(Path(bundle).resolve())
    except ValueError:
        return
    raise PriceEditError(
        "This packaged copy of SATC reads its price list from inside the "
        "application bundle, which is discarded when SATC closes — a price "
        "changed here would look right until the next restart and then be "
        "gone. Edit configs/billing/ in the SATC source folder and rebuild, or "
        "run SATC from source, where this screen writes to the real file.")


# --- reading the file both ways ---------------------------------------------


def _parsed_entries(path: Path, section: str, id_key: str) -> dict[str, dict]:
    """What the file MEANS, through the one parser (`read_yaml`), which is also
    the thing that turns a stray space into a sentence naming the line."""
    data = read_yaml(path)
    if not isinstance(data, dict):
        raise PriceEditError(f"{path} is not a mapping, so it holds no {section}.")
    out: dict[str, dict] = {}
    for entry in data.get(section) or []:
        if isinstance(entry, dict):
            out[str(entry.get(id_key, "")).strip()] = entry
    return out


@dataclass(frozen=True, slots=True)
class _Entry:
    """Where one entry LIVES in the text."""

    ident: str
    start: int
    end: int
    dash_indent: str
    key_indent: int


@dataclass(frozen=True, slots=True)
class _KeyLine:
    index: int
    head: str
    """Everything up to and including the colon and the spaces after it."""
    value: str
    tail: str
    """Trailing spaces and any inline comment — kept, because `# was 400 in
    2025` is the owner explaining a price to themselves."""


def _read_section(lines: list[str], path: Path, section: str,
                  id_key: str) -> tuple[list[_Entry], int]:
    """Find each entry of the top-level list, and where the list ends.

    Purely textual, and deliberately narrow: it understands a list of mappings
    indented under a key at column 0, which is what these two files are and
    what a hand edit keeps them as. Anything else is refused rather than
    guessed at.
    """
    top = None
    header = re.compile(r"^" + re.escape(section) + r"[ \t]*:[ \t]*(#.*)?$")
    for index, line in enumerate(lines):
        if header.match(_body(line)):
            top = index
            break
    if top is None:
        raise PriceEditError(
            f"{path} has no `{section}:` list at the start of a line, so there "
            f"is nothing here this editor knows how to change. Edit the file by "
            f"hand.")

    entries: list[tuple[int, str, int]] = []
    section_end = len(lines)
    for index in range(top + 1, len(lines)):
        body = _body(lines[index])
        if not body.strip() or body.lstrip().startswith("#"):
            continue
        if not body[:1].isspace():
            section_end = index
            break
        dash = re.match(r"^([ ]*)-([ \t]+|$)", body)
        if not dash:
            continue
        indent = dash.group(1)
        if entries and len(indent) != len(entries[0][1]):
            continue  # a nested list inside an entry, not a new entry
        opener = re.match(r"^([ ]*-[ \t]+)", body)
        key_indent = len(opener.group(1)) if opener else len(indent) + 2
        entries.append((index, indent, key_indent))

    if not entries:
        raise PriceEditError(
            f"{path} lists no {section}. Add one by hand before editing prices "
            f"through the app.")

    out: list[_Entry] = []
    for position, (start, indent, key_indent) in enumerate(entries):
        stop = entries[position + 1][0] if position + 1 < len(entries) else section_end
        while stop > start + 1:
            body = _body(lines[stop - 1])
            if body.strip() and not body.lstrip().startswith("#"):
                break
            stop -= 1
        skeleton = _Entry(ident="", start=start, end=stop, dash_indent=indent,
                          key_indent=key_indent)
        found = _key_lines(lines, skeleton, id_key)
        if len(found) != 1:
            raise PriceEditError(
                f"The entry at {path.name} line {start + 1} does not have "
                f"exactly one `{id_key}:` line, so there is no saying which "
                f"{section[:-1]} it is. Nothing was changed — fix that entry by "
                f"hand.")
        out.append(_Entry(ident=_unquote(found[0].value), start=start, end=stop,
                          dash_indent=indent, key_indent=key_indent))
    return out, out[-1].end


def _key_lines(lines: list[str], entry: _Entry, key: str) -> list[_KeyLine]:
    """Every line inside one entry that sets `key` at the entry's own level.

    The indentation has to match EXACTLY. That is what keeps the search out of
    a block-scalar description that happens to contain the words
    `standard_rate: 999`, and out of the next entry — a match one line too far
    down reprices the wrong service and still produces a tidy one-line diff.

    A comment cannot match either: `#` is not the first character of the key.
    """
    escaped = re.escape(key)
    on_dash = re.compile(r"^(?P<head>[ ]*-[ \t]+" + escaped
                         + r"[ \t]*:(?=[ \t]|$)[ \t]*)(?P<rest>.*)$")
    on_key = re.compile(r"^(?P<head>[ ]{" + str(entry.key_indent) + r"}" + escaped
                        + r"[ \t]*:(?=[ \t]|$)[ \t]*)(?P<rest>.*)$")
    out: list[_KeyLine] = []
    for index in range(entry.start, entry.end):
        body = _body(lines[index])
        found = (on_dash if index == entry.start else on_key).match(body)
        if not found:
            continue
        value, tail = _value_and_tail(found.group("rest"))
        out.append(_KeyLine(index=index, head=found.group("head"), value=value,
                            tail=tail))
    return out


def _value_and_tail(rest: str) -> tuple[str, str]:
    """Split what follows `key:` into the value and everything after it.

    "Everything after it" is trailing whitespace and an inline comment, both of
    which survive the edit — the point of doing this by hand is that the file
    comes back looking like the owner left it.
    """
    if not rest.strip():
        return "", rest
    quote = rest[0]
    if quote in "\"'":
        index = 1
        while index < len(rest):
            char = rest[index]
            if quote == '"' and char == "\\":
                index += 2
                continue
            if char == quote:
                if quote == "'" and rest[index + 1:index + 2] == "'":
                    index += 2
                    continue
                return rest[:index + 1], rest[index + 1:]
            index += 1
        return rest, ""  # unterminated quote: the loader will refuse it
    comment = re.search(r"[ \t]+#", rest)
    if comment:
        return rest[:comment.start()], rest[comment.start():]
    body = rest.rstrip()
    return body, rest[len(body):]


def _agree(entries: list[_Entry], parsed: dict[str, dict], path: Path,
           section: str) -> None:
    """Refuse unless the text scan and the YAML parser found the same entries,
    in the same order.

    They are two readers of one file and only one of them is authoritative
    about meaning. If they disagree, the text scan has mislocated something,
    and applying an edit at a location the parser does not recognise is how the
    wrong service gets repriced. There is no safe fallback here (principle 5).

    Duplicates are deliberately NOT judged here — the parser collapses them and
    the text scan does not, which is not a disagreement about location. That
    gets its own refusal, which can say which lines to look at.
    """
    seen: list[str] = []
    for entry in entries:
        if entry.ident not in seen:
            seen.append(entry.ident)
    if seen != list(parsed):
        raise PriceEditError(
            f"{path.name} reads one way as YAML and another way as text: the "
            f"parser finds {', '.join(parsed) or 'nothing'} and the line scan "
            f"finds {', '.join(seen) or 'nothing'}. Nothing was changed, "
            f"because an edit made at the wrong line reprices the wrong thing "
            f"and still looks like a tidy one-line diff. Edit {path.name} by "
            f"hand, then reload this screen.")


# --- values -----------------------------------------------------------------


def _as_decimal(text: str) -> Decimal | None:
    """The value that is in the file today, if it is a number at all.

    None rather than a raise: a file whose rate is currently unreadable is a
    file this editor can REPAIR, and the loader gets the final say on the way
    back in anyway.
    """
    try:
        value = Decimal(str(text).strip())
    except (InvalidOperation, ValueError, ArithmeticError):
        return None
    return value if value.is_finite() else None


def _number(raw: Any, *, what: str, shape: str) -> Decimal:
    text = str(raw).strip()
    if not text:
        raise PriceEditError(
            f"{what} is blank. {shape} A value nobody typed is not zero.")
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError, ArithmeticError):
        raise PriceEditError(
            f"{what} is not a number: {text!r}. {shape}") from None
    if not value.is_finite():
        # Decimal() accepts NaN and Infinity, and every guard written as a
        # comparison passes NaN silently — so this is asked before any
        # comparison, the same order invoice.py uses for the same reason.
        raise PriceEditError(f"{what} is not a number: {text!r}. {shape}")
    return value


def _amount(raw: Any, *, what: str) -> Decimal:
    value = _number(raw, what=what, shape="Write plain dollars — 450, or "
                                          "187.50. No dollar sign, no commas.")
    if value < 0:
        raise PriceEditError(
            f"{what} cannot be {value}. A price below zero is money owed back, "
            f"which is a credit note rather than a rate. Write 0 if the work is "
            f"free.")
    return value


def _percent(raw: Any, *, plan_key: str) -> Decimal:
    value = _number(raw, what=f"The discount for {plan_key!r}",
                    shape="Write a number between 0 and 100.")
    if value < 0:
        raise PriceEditError(
            f"A discount of {value}% on {plan_key!r} is a surcharge, which this "
            f"practice does not do. Write a number between 0 and 100.")
    if value > 100:
        raise PriceEditError(
            f"A discount of {value}% on {plan_key!r} would pay the client. Write "
            f"a number between 0 and 100 — 100 is the no-charge plan.")
    return value


def _render(value: Decimal) -> str:
    """The number as it will appear in the file: plain, never scientific."""
    return format(value, "f")


def _check_service_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, Mapping):
        raise PriceEditError(
            "A new service is described by a mapping of "
            f"{', '.join(_SERVICE_KEYS)} — not {type(spec).__name__}.")
    unknown = sorted(set(spec) - set(_SERVICE_KEYS))
    if unknown:
        raise PriceEditError(
            f"A service has no field called {', '.join(repr(u) for u in unknown)}. "
            f"It is written from: {', '.join(_SERVICE_KEYS)}. Nothing was added — "
            f"a field this editor did not recognise would have been dropped, and "
            f"a service with no rate loads as free.")
    missing = [key for key in _SERVICE_REQUIRED if not str(spec.get(key, "")).strip()]
    if missing:
        raise PriceEditError(
            f"A new service needs {', '.join(missing)}. Nothing is guessed here: "
            f"a service with no rate would load as free, and one with no name has "
            f"nothing to put on an invoice.")

    code = str(spec["code"]).strip()
    if not _CODE_SHAPE.match(code):
        raise PriceEditError(
            f"{code!r} is not usable as a service code. Use letters, digits and "
            f"underscores — like `return_1040` — because the code is what "
            f"invoices and workflows refer to.")
    units = get_args(catalogue.Unit)
    unit = str(spec["unit"]).strip()
    if unit not in units:
        raise PriceEditError(
            f"{unit!r} is not a unit. It is one of: {', '.join(units)} — fixed is "
            f"one charge however long it took, per_form is multiplied by how many, "
            f"per_hour is time-based.")
    clean: dict[str, Any] = {
        "code": code,
        "name": _flat(spec["name"]),
        "unit": unit,
        "standard_rate": _amount(spec["standard_rate"],
                                 what=f"The rate for {code!r}"),
    }
    for key in ("client_label", "category", "description"):
        text = _flat(spec.get(key, ""))
        if text:
            # Blank stays out of the file rather than going in as "". An absent
            # key gets the loader's documented default; an empty string is a
            # value nobody typed (principle 1).
            clean[key] = text
    return clean


def _flat(value: Any) -> str:
    """One line, collapsed — which is what the loader does with these anyway."""
    return " ".join(str(value).split())


def _render_service(clean: Mapping[str, Any], *, indent: str, key_indent: int,
                    eol: str) -> list[str]:
    """The new entry, in the shape the file already uses."""
    pad = " " * key_indent
    rows = [f"{indent}- code: {clean['code']}"]
    for key in ("name", "client_label", "category"):
        if key in clean:
            rows.append(f"{pad}{key}: {_quoted(clean[key])}")
    rows.append(f"{pad}unit: {clean['unit']}")
    rows.append(f"{pad}standard_rate: {_render(clean['standard_rate'])}")
    if "description" in clean:
        rows.append(f"{pad}description: {_quoted(clean['description'])}")
    return [row + eol for row in rows]


def _quoted(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _unquote(text: str) -> str:
    body = text.strip()
    if len(body) >= 2 and body[0] == body[-1] and body[0] in "\"'":
        inner = body[1:-1]
        if body[0] == "'":
            return inner.replace("''", "'")
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return body


# --- bytes ------------------------------------------------------------------
#
# Every read and write here is newline-transparent on purpose. `services.yaml`
# is CRLF in this repo and `rate_plans.yaml` is LF, and Python's default text
# mode would quietly rewrite one of them end to end — turning a one-line price
# change into a diff touching all 130 lines, which is exactly the review-proof
# blob this module exists to avoid.


def _read(path: Path) -> tuple[str, str]:
    if not path.exists():
        raise PriceEditError(
            f"There is no price list at {path}. Create it before changing "
            f"prices through the app — this editor changes what is there, it "
            f"does not invent a catalogue.")
    with open(path, "r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    # Stamped from the text just read rather than by re-reading the file, so
    # the token cannot describe a version this call never saw.
    return text, _stamp_of(text.encode("utf-8"))


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def _stamp(path: Path) -> str:
    """What the file says right now, as a short token.

    A hash of the CONTENT, not mtime and size — deliberately different from the
    catalogue's cache key, because this is answering a different question. The
    change this has to notice is a rate going 450 -> 475: the same number of
    bytes, quite possibly within the same clock tick as the read before it.
    mtime and size call that "unchanged", and the edit built on top of it would
    throw the other change away without a word.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return "-"
    return _stamp_of(raw)


def _stamp_of(raw: bytes) -> str:
    return hashlib.blake2b(raw, digest_size=12).hexdigest()


_AFTER_NEWLINE = re.compile(r"(?<=\n)")


def _split_lines(text: str) -> list[str]:
    """Split after every `\\n`, keeping the endings exactly as they are.

    Not `str.splitlines`, which also breaks on VT, FF, NEL and U+2028 — any of
    which inside a description would silently shift every line number after it.
    `"".join(_split_lines(text)) == text` always.
    """
    parts = _AFTER_NEWLINE.split(text)
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def _body(line: str) -> str:
    return line[:len(line) - len(_eol(line))]


def _eol(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def _dominant_eol(text: str) -> str:
    return "\r\n" if text.count("\r\n") * 2 > text.count("\n") else "\n"


def _diff(before: str, after: str, path: Path) -> str:
    """The exact change, unified — what a reviewer would see in git."""
    return "\n".join(difflib.unified_diff(
        [_body(line) for line in _split_lines(before)],
        [_body(line) for line in _split_lines(after)],
        fromfile=f"a/{path.name}", tofile=f"b/{path.name}", lineterm=""))
