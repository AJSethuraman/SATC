"""Load ServiceInviter.lua into a real Lua 5.1 against stubbed game functions."""
from pathlib import Path

import pytest
from lupa import lua51

HERE = Path(__file__).parent
ADDON = HERE.parent / "ServiceInviter" / "ServiceInviter.lua"

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
        self.lua.execute(ADDON.read_text())
        self.g = self.lua.globals()

    def run(self, code):
        return self.lua.execute(code)

    def eval(self, expr):
        return self.lua.eval(expr)

    def event(self, name, *args):
        self.g.FRAMES[1]._scripts.OnEvent(None, name, *args)

    def evaluate(self, message):
        ok, why = self.eval("function(m) return ServiceInviter_Test.Evaluate(ServiceInviter_Test.Norm(m)) end")(message)
        return bool(ok), why

    def sent(self):
        s = self.g.SENT
        return [(s[i].ch, s[i].to, s[i].m) for i in range(1, len(s) + 1)]

    def printed(self):
        p = self.g.PRINTED
        return [p[i] for i in range(1, len(p) + 1)]

    def status(self, name):
        return self.eval(f'ServiceInviter_Test.Jobs.Get("{name}").status')


@pytest.fixture
def game():
    return Game()


@pytest.fixture
def party():
    return Game(GROUP)
