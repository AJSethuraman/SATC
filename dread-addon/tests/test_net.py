"""Net.lua (the multiplayer probe) against a stand-in client: a simulated clock, a send budget that runs out, friends who reply
after a delay, and the game echoing your own messages back to you under your own name (which has a surname, like on Forever)."""
from pathlib import Path
import re
import pytest

lupa = pytest.importorskip("lupa")
DREAD = Path(__file__).resolve().parents[1] / "Dread"

MOCK = r'''
PRINTED, TIMERS, SENT, NOW = {}, {}, {}, 0
IN_GROUP, RAID = true, false
FRIENDS = { "Friend-Realm" }        -- who else has Dread
FRIEND_DELAY = 0.2                  -- seconds for a reply to come back
FRIEND_DROPS = 0                    -- the first friend loses every Nth burst message
FRIEND_REPLIES = true
ECHO = false                        -- the game hands your own messages back to you
ME = "Jesus Macy"                   -- the sender name an echo carries: a name AND a surname
BUCKET_CAP, BUCKET_REFILL = 1e9, 0  -- the client's send budget: tokens, and tokens regained per second
FIXED_RESULT = nil                  -- or force every send to return this
local tokens, last = nil, 0
local f_count, f_seen = {}, {}
function print(...) local t = {} for i = 1, select("#", ...) do t[#t + 1] = tostring((select(i, ...))) end PRINTED[#PRINTED + 1] = table.concat(t, " ") end
function GetTime() return NOW end
function IsInGroup() return IN_GROUP end
function IsInRaid() return RAID end
function UnitName() return "Jesus" end                       -- the first name only: the trap the old probe fell into
C_Timer = { After = function(sec, fn) TIMERS[#TIMERS + 1] = { NOW + sec, fn, #TIMERS } end }
function run_timers()
  while #TIMERS > 0 do
    table.sort(TIMERS, function(a, b) if a[1] ~= b[1] then return a[1] < b[1] end return a[3] < b[3] end)
    local e = table.remove(TIMERS, 1)
    NOW = e[1]
    e[2]()
  end
end
local frame
function CreateFrame() frame = { scripts = {}, RegisterEvent = function() end, SetScript = function(self, n, f) self.scripts[n] = f end } return frame end
local function deliver(text, channel, name) frame.scripts.OnEvent(frame, "CHAT_MSG_ADDON", "DREADNET", text, channel, name) end
local function fields(text) local t = {} for p in (text .. "|"):gmatch("([^|]*)|") do t[#t + 1] = p end return t end
local function take_token()
  if tokens == nil then tokens = BUCKET_CAP end
  tokens = math.min(BUCKET_CAP, tokens + (NOW - last) * BUCKET_REFILL)
  last = NOW
  if tokens >= 1 then tokens = tokens - 1 return true end
  return false
end
C_ChatInfo = {
  RegisterAddonMessagePrefix = function() return true end,
  SendAddonMessage = function(prefix, text, channel)
    if FIXED_RESULT ~= nil then return FIXED_RESULT end
    if not take_token() then return 3 end                    -- AddonMessageThrottle
    SENT[#SENT + 1] = text
    local f = fields(text)
    local kind = f[1]
    if ECHO then C_Timer.After(0.1, function() deliver(text, channel, ME) end) end
    if not FRIEND_REPLIES then return 0 end
    for i, name in ipairs(FRIENDS) do
      f_count[name], f_seen[name] = f_count[name] or 0, f_seen[name] or 0
      if kind == "PING" then
        C_Timer.After(FRIEND_DELAY, function() deliver("PONG|FRIEND" .. i .. "|" .. f[3] .. "|" .. f[4], channel, name) end)
      elseif kind == "BURST" then
        f_seen[name] = f_seen[name] + 1
        -- the first friend gets everything (less FRIEND_DROPS); every later friend gets only half of it
        local keep = (i == 1) and not (FRIEND_DROPS > 0 and f_seen[name] % FRIEND_DROPS == 0) or (i > 1 and f_seen[name] % 2 == 0)
        if keep then f_count[name] = f_count[name] + 1 end
      elseif kind == "END" then
        C_Timer.After(FRIEND_DELAY, function() deliver("STAT|FRIEND" .. i .. "|" .. f_count[name] .. "|" .. f[3], channel, name) end)
      end
    end
    return 0
  end,
}
'''


def boot(prelude=""):
    lua = lupa.LuaRuntime(unpack_returned_tuples=True)
    lua.execute(MOCK + "\n" + prelude)
    ns = lua.table()
    lua.eval("function(p, ns) return loadfile(p)('Dread', ns) end")(str(DREAD / "Net.lua"), ns)
    return lua, ns


def finish(lua, ns):
    assert ns.Net.start() is True
    lua.eval("run_timers")()
    return " ".join(str(v) for v in lua.eval("PRINTED").values())


def sent(lua):
    return [str(v) for v in lua.eval("SENT").values()]


# ---------------------------------------------------------------- the small pure parts
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


def test_sustained_is_the_fastest_rate_where_everything_was_accepted():
    lua, ns = boot()
    paced = lua.table_from({10: lua.table_from({"sent": 30, "ok": 5}), 5: lua.table_from({"sent": 15, "ok": 15}),
                            2: lua.table_from({"sent": 6, "ok": 6}), 1: lua.table_from({"sent": 3, "ok": 3})})
    assert ns.Net.sustained(paced) == 5
    nothing = lua.table_from({10: lua.table_from({"sent": 30, "ok": 1}), 1: lua.table_from({"sent": 3, "ok": 2})})
    assert ns.Net.sustained(nothing) is None


def test_the_result_codes_are_named():
    lua, ns = boot()
    assert ns.Net.RESULT[3] == "AddonMessageThrottle" and ns.Net.RESULT[0] == "Success"


# ---------------------------------------------------------------- a run
def test_refuses_politely_when_not_in_a_group():
    lua, ns = boot("IN_GROUP = false")
    assert ns.Net.start() is False
    assert any("join a party or raid" in str(l) for l in lua.eval("PRINTED").values()) and sent(lua) == []


def test_a_clean_run_with_a_friend_reports_pings_burst_and_the_paced_rates():
    lua, ns = boot()
    out = finish(lua, ns)
    assert "10 of 10 answered" in out
    assert "round trip 200 / 200 / 200 ms" in out                       # the friend replies after 0.2 s
    assert "sent 40 messages of 200 bytes, 40 accepted by the client, the friend received 40 of 40" in out
    assert "10/s 30 of 30, 5/s 15 of 15, 2/s 6 of 6, 1/s 3 of 3" in out and "took every message at 10 a second" in out
    assert "measured against Friend-Realm" in out and lua.eval("DreadDB.results.net") is not None
    assert all(len(t) <= 255 for t in sent(lua))                        # never over the 255-byte message limit


def test_a_tight_send_budget_is_found_the_way_it_was_in_the_real_game():
    # The real client took 2 of 40 burst messages and said 3 (throttled). Model that: a bucket of 2, refilling 1 a second.
    lua, ns = boot("BUCKET_CAP, BUCKET_REFILL = 2, 1")
    out = finish(lua, ns)
    m = re.search(r"sent 40 messages of 200 bytes, (\d+) accepted", out)
    assert m and int(m.group(1)) <= 3                                   # nearly the whole burst was refused
    assert "the client said: 3 = AddonMessageThrottle" in out           # and the number is named, not left as a bare 3
    assert "10/s" in out and re.search(r"10/s (\d+) of 30", out) and int(re.search(r"10/s (\d+) of 30", out).group(1)) < 10
    assert "took every message at 1 a second" in out                    # the steady rate it can keep up
    assert "1/s 3 of 3" in out


def test_a_client_that_refuses_everything_still_gets_a_report():
    lua, ns = boot("FIXED_RESULT = 'AddonMessageThrottle'")
    out = finish(lua, ns)
    assert "0 accepted by the client" in out and "AddonMessageThrottle" in out
    assert "refused some even at the slowest rate" in out


# ---------------------------------------------------------------- the bug your real run showed
def test_your_own_echo_under_a_name_with_a_surname_is_not_a_friend():
    # Real run: UnitName gave the first name, the echo carried "Jesus Macy", the names did not match, and the old probe
    # counted its own reply to its own message as a friend answering (6 of 10).
    lua, ns = boot("FRIENDS = {}\nECHO = true")
    out = finish(lua, ns)
    assert "0 of 10 answered by anyone else" in out
    assert "measured against" not in out and "no report back" in out


def test_an_echo_does_not_disturb_a_real_friend_either():
    lua, ns = boot("ECHO = true")
    out = finish(lua, ns)
    assert "10 of 10 answered" in out and "measured against Friend-Realm" in out


def test_with_two_friends_only_the_first_to_answer_is_measured():
    lua, ns = boot('FRIENDS = { "Friend-Realm", "Other-Realm" }')
    out = finish(lua, ns)
    assert "10 of 10 answered" in out                                    # not 20 of 10
    assert "the friend received 40 of 40" in out and "measured against Friend-Realm" in out


def test_a_friend_who_loses_messages_shows_up_as_missing():
    lua, ns = boot("FRIEND_DROPS = 4")
    assert "the friend received 30 of 40" in finish(lua, ns)


def test_no_friend_means_no_answers_and_no_crash():
    lua, ns = boot("FRIEND_REPLIES = false")
    out = finish(lua, ns)
    assert "0 of 10 answered by anyone else" in out and "no report back" in out


def test_a_missing_send_call_is_reported_not_fatal():
    lua, ns = boot("C_ChatInfo = nil\nSendAddonMessage = nil")
    assert "no addon-message call exists" in finish(lua, ns)


# ---------------------------------------------------------------- message hygiene
def test_every_burst_message_is_exactly_the_size_the_report_claims():
    lua, ns = boot()
    finish(lua, ns)
    bursts = [t for t in sent(lua) if t.startswith("BURST|")]
    assert len(bursts) == 40 and {len(t) for t in bursts} == {200}


def test_every_message_carries_this_sessions_id():
    lua, ns = boot()
    sid = str(ns.Net.SID)
    assert re.fullmatch(r"\d{8}", sid)
    finish(lua, ns)
    assert all(t.split("|")[1] == sid for t in sent(lua))


def test_it_answers_a_friends_ping_and_ignores_its_own_strangers_and_garbage():
    lua, ns = boot()
    f = ns.Net.frame
    ev = lambda text, who="Friend-Realm", prefix="DREADNET": f.scripts.OnEvent(f, "CHAT_MSG_ADDON", prefix, text, "PARTY", who)
    ev("PING|55555555|7|12.5")
    assert sent(lua) == [f"PONG|{ns.Net.SID}|7|12.5"]
    lua.execute("SENT = {}")
    ev(f"PING|{ns.Net.SID}|8|1", "Whatever Name")                         # our own id, under any name
    ev("PING|55555555|9|1", prefix="OTHERADDON")                           # someone else's addon
    ev(None)                                                               # garbage
    ev("nonsense")
    assert sent(lua) == []


def test_two_bursts_from_a_friend_are_counted_separately():
    lua, ns = boot()
    f = ns.Net.frame
    ev = lambda text: f.scripts.OnEvent(f, "CHAT_MSG_ADDON", "DREADNET", text, "PARTY", "Friend-Realm")
    for i in range(5):
        ev(f"BURST|55555555|{i}|xxxx")
    ev("END|55555555|5|")
    for i in range(3):
        ev(f"BURST|55555555|{i}|xxxx")
    ev("END|55555555|3|")
    stats = [t.split("|", 1)[0] + "|" + "|".join(t.split("|")[2:4]) for t in sent(lua) if t.startswith("STAT")]
    assert stats == ["STAT|5|5", "STAT|3|3"]


def test_a_second_run_cannot_start_on_top_of_the_first_but_can_after():
    lua, ns = boot()
    assert ns.Net.start() is True and ns.Net.start() is False
    lua.eval("run_timers")()
    assert ns.Net.start() is True
