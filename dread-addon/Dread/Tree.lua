-- Skill-point rules and the maths that turns spent points into damage, mana cost and resistance.
-- Pure Lua, no WoW calls.
--
-- Design choices (ours, not facts about another game):
--   * A character has `level + quest_points` skill points in total.
--   * A point goes into a skill only when the character level meets the skill's `req`, every
--     prerequisite has at least one point, and the skill has fewer than MAX_POINTS.
--   * Synergy and mastery use points actually spent ("hard points"); item bonuses are not modelled yet.
--   * A resist of 100 or more is immunity: a pierce effect only takes a fifth of its value off it.
local _, ns = ...
ns = ns or {}

local Tree = {}
ns.Tree = Tree

local function skills() return ns.Skills end

function Tree.new(opts)
  opts = opts or {}
  return { level = opts.level or 1, quest_points = opts.quest_points or 0, points = {} }
end

function Tree.points_total(st) return st.level + st.quest_points end

function Tree.points_spent(st)
  local n = 0
  for _, v in pairs(st.points) do n = n + v end
  return n
end

function Tree.points_free(st) return Tree.points_total(st) - Tree.points_spent(st) end

function Tree.points_in(st, id) return st.points[id] or 0 end

-- true, or false plus the reason a point cannot go in.
Tree.HEADROOM = 3

function Tree.can_allocate(st, id)
  local sk = skills().byId[id]
  if not sk then return false, "no such skill" end
  if st.level < sk.req then return false, "needs character level " .. sk.req end
  for _, p in ipairs(sk.prereqs) do
    if Tree.points_in(st, p) < 1 then return false, "needs a point in " .. skills().byId[p].name end
  end
  if Tree.points_in(st, id) >= skills().MAX_POINTS then return false, "already at the maximum" end
  local cap = st.level - sk.req + Tree.HEADROOM                -- a skill keeps growing as you do: saving points up cannot pour them all into one new skill
  if Tree.points_in(st, id) >= cap then return false, "can take " .. cap .. " points at character level " .. st.level .. " (more as you level)" end
  if Tree.points_free(st) < 1 then return false, "no points left" end
  return true
end

function Tree.allocate(st, id)
  local ok, why = Tree.can_allocate(st, id)
  if not ok then return false, why end
  st.points[id] = Tree.points_in(st, id) + 1
  return true
end

-- Sum of a value from every learned mastery/passive of the given effect type and element.
function Tree.bonus(st, effect_type, element)
  local total = 0
  for _, sk in ipairs(skills()) do
    local e, pts = sk.effect, Tree.points_in(st, sk.id)
    if e and e.type == effect_type and sk.element == element and pts > 0 then
      total = total + e.base + e.per_level * (pts - 1)
    end
  end
  return total
end

-- 1 + the synergy bonus, as a multiplier.
function Tree.synergy_mult(st, id)
  local sk, pct = skills().byId[id], 0
  for _, s in ipairs(sk.syn or {}) do pct = pct + s.pct * Tree.points_in(st, s.from) end
  return 1 + pct / 100
end

-- Damage range (lo, hi) at the character's current points; nil, nil if the skill has no damage or no points.
function Tree.damage(st, id)
  local sk, n = skills().byId[id], Tree.points_in(st, id)
  if not sk.dmg or n < 1 then return nil, nil end
  local d = sk.dmg
  local mult = Tree.synergy_mult(st, id) * (1 + Tree.bonus(st, "dmg_bonus_pct", sk.element) / 100)
  return (d[1] + d[3] * (n - 1)) * mult, (d[2] + d[4] * (n - 1)) * mult
end

function Tree.mana_cost(st, id)
  local sk, n = skills().byId[id], Tree.points_in(st, id)
  if not sk.mana or n < 1 then return nil end
  local cost = sk.mana[1] + sk.mana[2] * (n - 1)
  cost = cost * (1 - Tree.bonus(st, "mana_discount_pct", sk.element) / 100)
  return math.max(skills().MIN_MANA, cost)
end

-- A monster's resist (percent) after the character's piercing effects. Floor is -100.
function Tree.effective_resist(st, element, resist)
  local pierce = Tree.bonus(st, "resist_pierce_pct", element)
  local r
  if resist >= 100 then r = resist - pierce * 0.2 else r = resist - pierce end
  return math.max(-100, r)
end

function Tree.after_resist(amount, resist) return amount * (1 - resist / 100) end

-- Problems with the skill table itself; an empty list means it is well formed.
function Tree.validate()
  local S, problems = skills(), {}
  local gates = { [1]=true, [6]=true, [12]=true, [18]=true, [24]=true, [30]=true }
  local per_tree, seen = {}, {}
  for _, sk in ipairs(S) do
    if seen[sk.id] then problems[#problems + 1] = "duplicate id " .. sk.id end
    seen[sk.id] = true
    per_tree[sk.tree] = (per_tree[sk.tree] or 0) + 1
    if not gates[sk.req] then problems[#problems + 1] = sk.id .. ": odd level gate " .. tostring(sk.req) end
    for _, p in ipairs(sk.prereqs) do
      local pre = S.byId[p]
      if not pre then problems[#problems + 1] = sk.id .. ": unknown prerequisite " .. p
      elseif pre.req >= sk.req then problems[#problems + 1] = sk.id .. ": prerequisite " .. p .. " is not an earlier tier" end
    end
    for _, s in ipairs(sk.syn or {}) do
      if not S.byId[s.from] then problems[#problems + 1] = sk.id .. ": synergy from unknown skill " .. s.from end
      if s.from == sk.id then problems[#problems + 1] = sk.id .. ": synergy from itself" end
    end
  end
  for _, t in ipairs(S.trees) do
    if per_tree[t] ~= 10 then problems[#problems + 1] = t .. " tree has " .. tostring(per_tree[t]) .. " skills, expected 10" end
  end
  return problems
end

return Tree
