"""Load ServiceInviter.lua into a real Lua 5.1 against stubbed game functions."""
from pathlib import Path

import pytest
from lupa import lua51

HERE = Path(__file__).parent
ADDON = HERE.parent / "ServiceInviter" / "ServiceInviter.lua"
CORE = HERE.parent / "ServiceInviter" / "Services.lua"
CHANAUTO = True   # see Game.__init__

# A party of two others: the lock and a customer, both targetable and in range.
GROUP = """
UNITNAMES = { party1 = "Lock", party2 = "Bob" }
function UnitExists(u) return UNITNAMES[u] ~= nil end
function GetUnitName(u) return UNITNAMES[u] end
function UnitIsVisible() return true end
function CheckInteractDistance() return true end
function UnitClass(u) return "Warlock", "WARLOCK" end
GROUP = { Lock = true, Bob = true }
"""


class Game:
    def __init__(self, before=""):
        self.lua = lua51.LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((HERE / "stubs.lua").read_text())
        if before:
            self.lua.execute(before)
        self.lua.execute(CORE.read_text())
        self.lua.execute(ADDON.read_text())
        # the tests written before 3.9.26 start their customers from a buyer's line in Trade, which
        # invited by itself until then; that is now a switch, off unless you turn it on
        # (tests/test_whisper_only.py covers the default)
        if CHANAUTO:
            self.lua.execute("ServiceInviterDB.chanauto = true")
        self.g = self.lua.globals()

    def run(self, code):
        return self.lua.execute(code)

    def eval(self, expr):
        return self.lua.eval(expr)

    def event(self, name, *args):
        self.g.FRAMES[1]._scripts.OnEvent(None, name, *args)

    def evaluate(self, message):
        r = self.eval("function(m) return ServiceInviter_Test.Evaluate(ServiceInviter_Test.Norm(m)) end")(message)
        r = r if isinstance(r, tuple) else (r,)
        return bool(r[0]), r[1] if len(r) > 1 else None

    def sent(self):
        s = self.g.SENT
        return [(s[i].ch, s[i].to, s[i].m) for i in range(1, len(s) + 1)]

    def printed(self):
        p = self.g.PRINTED
        return [p[i] for i in range(1, len(p) + 1)]

    def plain(self):
        """What was printed, without the color codes."""
        import re
        return [re.sub(r"\|c[0-9a-fA-F]{8}|\|r", "", l) for l in self.printed()]

    def status(self, name):
        return self.eval(f'ServiceInviter_Test.Jobs.Get("{name}").status')


@pytest.fixture
def game():
    return Game()


@pytest.fixture
def party():
    return Game(GROUP)
