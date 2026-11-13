-- Finder: monsters drawn from a model file alone come out plain white (the skin lives with the creature, not the model). Drawn from a
-- creature id they come out right. This finds the creature ids whose model is the one we want, by asking the client: set a hidden
-- model to creature N, then ask which model file it loaded. Matches are kept in DreadDB.found and the game uses them.
local _, ns = ...
local Finder = {}
ns.Finder = Finder

-- model file id -> what it is. Every monster in Zone.lua names one of these as `model`.
Finder.TARGETS = { [126570] = "zombie", [124160] = "ghoul", [125576] = "rat", [125942] = "skeleton", [125947] = "skeleton mage", [123137] = "carrion bird" }
Finder.PER_BATCH, Finder.DELAY, Finder.KEEP, Finder.LAST = 20, 0.5, 4, 25000

-- The (first, last) of each batch of creature ids.
function Finder.batches(first, last, per)
  local out = {}
  per = per or Finder.PER_BATCH
  local a = first
  while a <= last do
    out[#out + 1] = { a, math.min(last, a + per - 1) }
    a = a + per
  end
  return out
end

-- A creature id that loaded model `fileid`: keep it if that model is one we want (at most KEEP of each). True if kept.
function Finder.consider(found, fileid, npc)
  if not Finder.TARGETS[fileid] then return false end
  local list = found[fileid]
  if not list then list = {}; found[fileid] = list end
  if #list >= Finder.KEEP then return false end
  for _, n in ipairs(list) do if n == npc then return false end end
  list[#list + 1] = npc
  return true
end

-- Is every wanted model covered at least once? Then there is nothing more to look for.
function Finder.complete(found)
  for fileid in pairs(Finder.TARGETS) do
    if not (found and found[fileid] and #found[fileid] > 0) then return false end
  end
  return true
end

-- The creature id to draw this model with, or nil if none has been found (the game then falls back to the bare model).
function Finder.npc_for(found, fileid)
  local list = found and found[fileid]
  return list and list[1] or nil
end

----------------------------------------------------------------- the scan itself (needs the client)
local running, pool, stopped = false, nil, false

function Finder.running() return running end

function Finder.stop() stopped = true end

-- say(msg): where to report progress. Scans creature ids first..last in batches, a moment apart, and stops early once everything is found.
function Finder.start(first, last, say)
  if running then return false end
  DreadDB = DreadDB or {}
  DreadDB.found = DreadDB.found or {}
  local found = DreadDB.found
  say = say or function() end
  first, last = first or 1, last or Finder.LAST
  local list = Finder.batches(first, last, Finder.PER_BATCH)
  running, stopped = true, false
  if not pool then
    pool = {}
    for i = 1, Finder.PER_BATCH do
      local m = CreateFrame("PlayerModel", nil, UIParent)
      m:SetSize(4, 4); m:SetPoint("BOTTOMLEFT", UIParent, "BOTTOMLEFT", 0, 0); m:SetAlpha(0.02); m:Show()
      pool[i] = m
    end
  end
  local i, hits = 0, 0
  local function finish(why)
    running = false
    DreadDB.found_scan = { first = first, last = last, at = i, done = (why == "done" or why == "complete") }
    say("model search " .. why .. ": " .. hits .. " creature id(s) found" .. (Finder.complete(found) and ", every monster covered" or ""))
  end
  local function step()
    if stopped then return finish("stopped") end
    i = i + 1
    local b = list[i]
    if not b then return finish("done") end
    for k = 0, b[2] - b[1] do pcall(pool[k + 1].SetCreature, pool[k + 1], b[1] + k) end
    C_Timer.After(Finder.DELAY, function()
      for k = 0, b[2] - b[1] do
        local ok, fid = pcall(pool[k + 1].GetModelFileID, pool[k + 1])
        if ok and type(fid) == "number" and Finder.consider(found, fid, b[1] + k) then
          hits = hits + 1
          say("found creature " .. (b[1] + k) .. " = " .. Finder.TARGETS[fid])
        end
      end
      if i % 100 == 0 then say("model search: up to creature " .. b[2]) end
      if Finder.complete(found) then return finish("complete") end
      step()
    end)
  end
  step()
  return true
end

return Finder
