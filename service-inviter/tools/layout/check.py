"""Layout check: draw every Service Inviter window from the real Lua, in realistic states, and
fail if anything overlaps or any text runs past its box. Writes a picture of each to OUT.

    python tools/layout/check.py [OUT]       (needs node and Playwright with Chromium)

Why: in game, 12 Nov 2026, the ad button covered the "Customers" title. The owner: "you need
to pay more attention to format there is no reason for buttons to cover words". The tests
cannot see layout; this does. Run it before building an installer.
"""
import json, subprocess, sys, tempfile
from pathlib import Path
from lupa import lua51

HERE = Path(__file__).parent
ADDON = HERE.parent.parent / "ServiceInviter"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="si-layout-"))

GROUP = '''
UNITS = { player = {"Me","SHAMAN",60,"Orgrimmar"}, party1 = {"Grimtotem","WARLOCK",60,"Thunder Bluff"}, party2 = {"Velenne","MAGE",47,"Orgrimmar"} }
function UnitExists(u) return UNITS[u] ~= nil end
function UnitName(u) local x = UNITS[u] return x and x[1] end
function UnitClass(u) local x = UNITS[u] if not x then return nil end return x[2], x[2] end
function UnitLevel(u) local x = UNITS[u] return x and x[3] end
function GetRealZoneText() return UNITS.player[4] end
C_Map = { GetBestMapForUnit = function(u) return UNITS[u] and u end, GetMapInfo = function(u) local x = UNITS[u] return x and { name = x[4] } end }
function UnitFactionGroup() return "Horde" end
GROUP = { Grimtotem = true, Velenne = true }
'''
CHANNELS = 'function GetChannelList() return 2, "Trade - City", false end'


def load(before=""):
    L = lua51.LuaRuntime(unpack_returned_tuples=True)
    L.execute((HERE / "record.lua").read_text())
    L.execute(CHANNELS + "\n" + before)
    L.execute((ADDON / "Services.lua").read_text())
    L.execute((ADDON / "ServiceInviter.lua").read_text())
    L.execute('ServiceInviterDB.stats = { start = time() - 7200, summoned = 81, ev = 1860, paid = 0, silver = 0 }')
    return L


def export(L, win, page=None):
    g = L.globals()
    wid, pid = win._id, page._id if page else None
    items, allv = [], g.ALL
    for j in range(1, len(allv) + 1):
        o = allv[j]
        par = o._parent
        if not par or par._id not in (wid, pid):
            continue
        if page is not None and par._id == wid and o._kind == "Frame":
            continue
        pts = [dict(p=pt.p, rel=0 if pt.rel in (wid, pid) else pt.rel, rp=pt.rp, x=pt.x, y=pt.y) for pt in o._points.values()]
        items.append(dict(id=o._id, kind=o._kind, template=o._template or "", font=o._font or "", points=pts,
                          w=o._w or None, h=o._h or None, text=o._text or "", checked=bool(o._checked),
                          hidden=bool(o._hidden), disabled=bool(o._disabled), nowrap=bool(o._nowrap),
                          color=list(o._color.values()) if o._color else None,
                          justify=o._justify or None, fontsize=o._fontsize or None))
    return {"w": win._w, "h": win._h, "items": items}


scenes = {}
L = load(GROUP)
L.execute('ServiceInviterDB.services = { portals = { on = true, price = 20 }, water = { on = true }, healthstone = { on = true } }')
L.execute("SETUP = ServiceInviter_Test.BuildSetup() SETUP:Show()")
win = L.globals().SETUP
for i, name in enumerate(["General", "Warlock", "Mage", "Rogue", "Buffs", "Advertise"], 1):
    L.execute(f"SETUP.ShowTab({i}) SETUP.Refresh()")
    scenes[f"setup_{name}"] = export(L, win, win.pages[i])

for name, before in [("picker_alone", ""), ("picker_in_a_group", GROUP)]:
    L = load(before)
    L.execute("""S = ServiceInviter_Test.BuildSetup() S:Show() S.ShowTab(2)
        ServiceInviter_Test.ShowPicker(ServiceInviter_Test.SetupBoxes().svc_summons_payee, true, "Who gets paid for summons?", "summons")""")
    scenes[name] = export(L, L.globals().ServiceInviterPicker)

BUSY = '''local J = ServiceInviter_Test.Jobs
  J.New("Aldric","x","t","Trade") J.New("Brenna","x","t","Trade") J.Joined("Brenna")
  J.New("Corvin","x","t","Trade") J.Joined("Corvin") J.Set("Corvin","summoned")
  J.New("Dahlia","x","t","Trade") J.Joined("Dahlia") J.Set("Dahlia","summoned") J.Set("Dahlia","arrived") J.Get("Dahlia").offered = true
  J.New("Edric","x","t","Trade") J.Busy("Edric")
  J.New("Fennamaraqu","x","t","Trade") J.Declined("Fennamaraqu")'''
for name, before, after in [
    ("customers_nothing_to_sell", "", ""),
    ("customers_ready_to_post", GROUP, ""),
    ("customers_waiting_for_next_ad", GROUP, "ServiceInviter_Test.PostAd() CLOCK = CLOCK + 1"),
    ("customers_two_warlocks", GROUP.replace('party2 = {"Velenne","MAGE",47,"Orgrimmar"}', 'party2 = {"Ashfel","WARLOCK",60,"Undercity"}').replace('GROUP = { Grimtotem = true, Velenne = true }', 'GROUP = { Grimtotem = true, Ashfel = true }'),
     '''local function ch(n, t) local f for _, o in ipairs(ALL) do if o._kind == "Frame" and rawget(o._scripts, "OnEvent") then f = o break end end
          f._scripts.OnEvent(nil, "CHAT_MSG_CHANNEL", t, n, "", "2. Trade - City", "", "", "", "", "Trade") end
        ch("Kaldrok", "WTB summon to TB") ch("Mirasha", "WTB summon to UC") ch("Thrandor", "wtb summ uc")
        UNITS.party3 = {"Kaldrok","ROGUE",44,"Orgrimmar"} UNITS.party4 = {"Mirasha","PRIEST",52,"Orgrimmar"}
        ServiceInviter_Test.Jobs.Joined("Kaldrok") ServiceInviter_Test.Jobs.Joined("Mirasha")'''),
    ("customers_priest_with_buffs_waiting", GROUP.replace('"Me","SHAMAN",60,"Orgrimmar"', '"Me","PRIEST",60,"Thunder Bluff"').replace('party2 = {"Velenne","MAGE",47,"Orgrimmar"}', 'party2 = {"Kaldrok","ROGUE",44,"Thunder Bluff"}').replace('GROUP = { Grimtotem = true, Velenne = true }', 'GROUP = { Grimtotem = true, Kaldrok = true }') + '\nServiceInviterDB = { services = { fort = { on = true } } }',
     '''local f for _, o in ipairs(ALL) do if o._kind == "Frame" and rawget(o._scripts, "OnEvent") then f = o break end end
        f._scripts.OnEvent(nil, "CHAT_MSG_PARTY", "fort pls", "Grimtotem", "", "", "", "", "", "", "")
        f._scripts.OnEvent(nil, "CHAT_MSG_PARTY", "can i get stam buff", "Kaldrok", "", "", "", "", "", "", "")'''),
    ("customers_busy_as_the_lock", GROUP.replace('"Me","SHAMAN"', '"Me","WARLOCK"') + '\nServiceInviterDB = { role = "lock" }', BUSY),
]:
    L = load(before)
    L.execute(after)
    L.execute("ServiceInviter_Test.Refresh() ServiceInviterJobs:Show() ServiceInviter_Test.Refresh()")
    scenes[name] = export(L, L.globals().ServiceInviterJobs)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "scenes.json").write_text(json.dumps(scenes))
r = subprocess.run(["node", str(HERE / "shoot.js"), str(HERE / "render.html"), str(OUT)], capture_output=True, text=True)
print(r.stdout, end="")
if r.returncode != 0:
    print(r.stderr, end="")
    sys.exit(r.returncode)
print(f"pictures in {OUT}")
