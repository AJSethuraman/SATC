"""Net.lua (the multiplayer probe) against a stand-in client with a stand-in friend on the other end."""
from pathlib import Path
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
PRINTED, TIMERS, SENT, NOW = {}, {}, {}, 0
IN_GROUP, RAID = true, false
FRIEND_DROPS = 0          -- the friend's client loses every Nth burst message
SEND_RESULT = 0           -- what the send call returns
FRIEND_REPLIES = true
FRIENDS = { "Friend-Realm" }
local friend_count, friend_seen = {}, {}
function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end PRINTED[#PRINTED + 1] = table.concat(t, " ") end
function GetTime() NOW = NOW + 0.05 return NOW end
function IsInGroup() return IN_GROUP end
function IsInRaid() return RAID end
function UnitName() return "Me" end
C_Timer = { After = function(sec, fn) TIMERS[#TIMERS + 1] = { sec, fn } end }
function run_timers() table.sort(TIMERS, function(a, b) return a[1] < b[1] end) local t = TIMERS TIMERS = {} for _, e in ipairs(t) do e[2]() end end
local frame
function CreateFrame() frame = { scripts = {}, RegisterEvent = function() end, SetScript = function(self, n, f) self.scripts[n] = f end } return frame end
local function from_friend(text, channel, name) frame.scripts.OnEvent(frame, "CHAT_MSG_ADDON", "DREADNET", text, channel, name) end
C_ChatInfo = {
  RegisterAddonMessagePrefix = function() return true end,
  SendAddonMessage = function(prefix, text, channel)
    SENT[#SENT + 1] = text
    if not FRIEND_REPLIES then return SEND_RESULT end
    local kind, a, b = text:match("^(%u+)|([^|]*)|?(.*)$")
    for i, name in ipairs(FRIENDS) do
      friend_count[name], friend_seen[name] = friend_count[name] or 0, friend_seen[name] or 0
      if kind == "PING" then from_friend("PONG|" .. a .. "|" .. b, channel, name)
      elseif kind == "BURST" then
        friend_seen[name] = friend_seen[name] + 1
        -- the first friend gets everything (less FRIEND_DROPS); every later friend gets only half of it
        local keep = (i == 1) and not (FRIEND_DROPS > 0 and friend_seen[name] % FRIEND_DROPS == 0) or (i > 1 and friend_seen[name] % 2 == 0)
        if keep then friend_count[name] = friend_count[name] + 1 end
      elseif kind == "END" then from_friend("STAT|" .. friend_count[name] .. "|" .. a, channel, name) end
    end
    return SEND_RESULT
  end,
}
'''


def boot(prelude=""):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK + "\n" + prelude)
    ns = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Net.lua"), ns)
    return lua, ns


def said(lua):
    return [str(v) for v in lua.eval("PRINTED").values()]


def test_summarize_gives_min_average_max_and_nothing_for_no_samples():
    lua, ns = boot()
    s = ns.Net.summarize(lua.table_from([10, 20, 60]))
    assert s.n == 3 and s.min == 10 and s.max == 60 and s.avg == pytest.approx(30)
    assert ns.Net.summarize(lua.table()) is None


def test_the_channel_is_party_raid_or_nothing():
    lua, ns = boot()
    assert ns.Net.channel() == "PARTY"
    lua.execute("RAID = true");  assert ns.Net.channel() == "RAID"
    lua.execute("IN_GROUP = false");  assert ns.Net.channel() is None


def test_refuses_politely_when_not_in_a_group():
    lua, ns = boot("IN_GROUP = false")
    assert ns.Net.start() is False
    assert any("join a party" in l for l in said(lua)) and len(list(lua.eval("SENT").values())) == 0


def test_a_clean_run_reports_every_ping_and_the_whole_burst():
    lua, ns = boot()
    assert ns.Net.start() is True
    lua.eval("run_timers")()
    out = " ".join(said(lua))
    assert "10 of 10 answered" in out and "round trip" in out
    assert "sent 40 messages of 200 bytes, 40 accepted by the client, the friend received 40 of 40" in out
    assert lua.eval("DreadDB.results.net") is not None
    sent = [str(v) for v in lua.eval("SENT").values()]
    assert sum(t.startswith("PING|") for t in sent) == 10 and sum(t.startswith("BURST|") for t in sent) == 40
    assert all(len(t) <= 255 for t in sent)                                  # never over the 255-byte message limit


def test_a_throttled_friend_shows_up_as_missing_messages():
    lua, ns = boot("FRIEND_DROPS = 4")                                      # the friend loses every 4th
    ns.Net.start()
    lua.eval("run_timers")()
    assert "the friend received 30 of 40" in " ".join(said(lua))


def test_a_client_that_refuses_messages_says_what_it_said():
    lua, ns = boot("SEND_RESULT = 'AddonMessageThrottle'")
    ns.Net.start()
    lua.eval("run_timers")()
    out = " ".join(said(lua))
    assert "0 accepted by the client" in out and "AddonMessageThrottle" in out


def test_no_friend_means_no_answers_and_no_crash():
    lua, ns = boot("FRIEND_REPLIES = false")
    ns.Net.start()
    lua.eval("run_timers")()
    out = " ".join(said(lua))
    assert "0 of 10 answered" in out and "no report back" in out


def test_a_missing_send_call_is_reported_not_fatal():
    lua, ns = boot("C_ChatInfo = nil\nSendAddonMessage = nil")
    ns.Net.start()
    lua.eval("run_timers")()
    assert "no addon-message call exists" in " ".join(said(lua))


def test_it_answers_a_friend_who_pings_it_and_ignores_its_own_echo_and_strangers():
    lua, ns = boot()
    frame = ns.Net.frame
    frame.scripts.OnEvent(frame, "CHAT_MSG_ADDON", "DREADNET", "PING|7|12.5", "PARTY", "Friend-Realm")
    assert [str(v) for v in lua.eval("SENT").values()] == ["PONG|7|12.5"]
    lua.execute("SENT = {}")
    frame.scripts.OnEvent(frame, "CHAT_MSG_ADDON", "DREADNET", "PING|8|1", "PARTY", "Me-Realm")        # our own message coming back
    frame.scripts.OnEvent(frame, "CHAT_MSG_ADDON", "OTHERADDON", "PING|9|1", "PARTY", "Friend-Realm")  # someone else's addon
    frame.scripts.OnEvent(frame, "CHAT_MSG_ADDON", "DREADNET", None, "PARTY", "Friend-Realm")           # garbage
    assert len(list(lua.eval("SENT").values())) == 0


def test_a_second_run_cannot_start_on_top_of_the_first():
    lua, ns = boot()
    assert ns.Net.start() is True and ns.Net.start() is False
    lua.eval("run_timers")()
    assert ns.Net.start() is True


def test_the_round_trip_numbers_are_real_measurements():
    import re
    lua, ns = boot()
    ns.Net.start()
    lua.eval("run_timers")()
    m = re.search(r"round trip ([\d.]+) / ([\d.]+) / ([\d.]+) ms", " ".join(said(lua)))
    assert m, "no round-trip line"
    lo, avg, hi = (float(x) for x in m.groups())
    assert 0 < lo <= avg <= hi                                          # not zeros, and in order


def test_two_bursts_from_a_friend_are_counted_separately():
    lua, ns = boot()
    f = ns.Net.frame
    def event(text):
        f.scripts.OnEvent(f, "CHAT_MSG_ADDON", "DREADNET", text, "PARTY", "Friend-Realm")
    for i in range(5):
        event(f"BURST|{i}|xxxx")
    event("END|5")
    for i in range(3):
        event(f"BURST|{i}|xxxx")
    event("END|3")
    stats = [str(t) for t in lua.eval("SENT").values() if str(t).startswith("STAT")]
    assert stats == ["STAT|5|5", "STAT|3|3"]                            # the second report is not 8


def test_with_two_friends_only_the_first_to_answer_is_measured():
    lua, ns = boot('FRIENDS = { "Friend-Realm", "Other-Realm" }')       # both have Dread and both answer everything
    ns.Net.start()
    lua.eval("run_timers")()
    out = " ".join(said(lua))
    assert "10 of 10 answered" in out                                    # not 20 of 10
    assert "the friend received 40 of 40" in out                         # the first friend's count, not overwritten by the second's 20
    assert "Friend-Realm" in out                                         # and the report says whose numbers these are


def test_every_burst_message_is_exactly_the_size_the_report_claims():
    lua, ns = boot()
    ns.Net.start()
    lua.eval("run_timers")()
    bursts = [str(t) for t in lua.eval("SENT").values() if str(t).startswith("BURST|")]
    assert len(bursts) == 40 and {len(t) for t in bursts} == {200}       # not 196 for the first nine and 197 for the rest
