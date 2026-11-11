"""Spells.lua: the page of spell-effect models. The stand-in client cannot say what the real one draws; this proves the
data is sane, paging is right, and a client that refuses SetModel does not break the window."""
import re
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
ALL = {}
local function obj(kind)
  local o = { kind = kind, scripts = {}, models = {} }
  ALL[#ALL + 1] = o
  return setmetatable(o, { __index = function(t, k)
    if k == "SetScript" then return function(self, n, f) self.scripts[n] = f end end
    if k == "CreateTexture" or k == "CreateFontString" then return function() return obj(k == "CreateTexture" and "Texture" or "FontString") end end
    if k == "SetText" then return function(self, s) self.text = s end end
    if k == "SetModel" then return function(self, id) if REFUSE then error("refused") end self.model = id end end
    if k == "Show" then return function(self) self.shown = true end end
    if k == "Hide" then return function(self) self.shown = false end end
    return function(self, ...) return self end
  end })
end
function CreateFrame(kind) return obj(kind) end
UIParent = obj("UIParent")
'''


def boot(refuse=False):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute("REFUSE = " + ("true" if refuse else "false") + "\n" + MOCK)
    ns = lua.table()
    ld = lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")
    for f in ("SpellData", "Spells"):
        ld(str(DREAD / f"{f}.lua"), ns)
    return lua, ns


def test_every_candidate_is_a_positive_integer_id_with_a_plain_label_and_no_repeats():
    lua, ns = boot()
    rows = [(r[1], r[2]) for r in ns.SpellData.values()]
    assert len(rows) >= 100
    assert all(isinstance(i, int) and i > 0 and re.fullmatch(r"[a-z0-9_]+", n) for i, n in rows)
    assert len({i for i, _ in rows}) == len(rows)


def test_pages_cover_everything_once_and_out_of_range_pages_clamp():
    lua, ns = boot()
    seen = []
    for p in range(1, ns.Spells.pages() + 1):
        lst, got = ns.Spells.page(p)
        assert got == p and 1 <= len(list(lst.values())) <= 12
        seen += [e.n for e in lst.values()]
    assert seen == list(range(1, len(ns.SpellData) + 1))
    assert ns.Spells.page(0)[1] == 1 and ns.Spells.page(999)[1] == ns.Spells.pages() and ns.Spells.page("x")[1] == 1


def test_show_puts_each_models_id_on_its_cell_and_labels_it_with_the_same_number():
    lua, ns = boot()
    ns.Spells.show(2)
    models = [o for o in lua.eval("ALL").values() if o.kind == "PlayerModel"]
    assert len(models) == 12
    lst, _ = ns.Spells.page(2)
    assert [m.model for m in models] == [e.id for e in lst.values()]
    lst = {i + 1: e for i, e in enumerate(lst.values())}
    labels = [o.text for o in lua.eval("ALL").values() if o.text and o.kind == "FontString" and o.text[:1].isdigit()]
    assert labels[0].startswith(f"{lst[1].n}  {lst[1].id}  ")


def test_a_short_last_page_hides_the_unused_cells():
    lua, ns = boot()
    last = ns.Spells.pages()
    ns.Spells.show(last)
    n = len(list(ns.Spells.page(last)[0].values()))
    models = [o for o in lua.eval("ALL").values() if o.kind == "PlayerModel"]
    assert [m.shown for m in models][n:] == [False] * (12 - n)


def test_a_client_that_refuses_the_model_does_not_break_the_window():
    lua, ns = boot(refuse=True)
    assert ns.Spells.show(1) == 1
