-- The Mage skill table. Data only: every number here is a tuning knob, not a fact about any other game.
-- Shape (3 trees x 10 skills, character-level gates 1/6/12/18/24/30, prerequisites, synergies, one
-- mastery per tree) follows the Diablo II design the owner asked for. Names are WoW's or our own,
-- never Diablo II's. Nothing here is copied text.
--
-- Fields
--   id, name, tree, element ("fire" | "cold" | "lightning")
--   req        character level needed before a point can go in
--   prereqs    skill ids that need at least one point first (always a lower req, so no cycles)
--   kind       how the engine treats it: bolt, cone, trail, aoe, zone, summon, buff, utility, passive, mastery
--   mana       { base, per_level }   cost at skill level n = base + per_level * (n - 1)
--   dmg        { lo, hi, lo_step, hi_step }   damage at level n = lo + lo_step * (n - 1), same for hi
--   syn        { {from = id, pct = n}, ... }   +n% damage per point spent in `from`
--   effect     { type, base, per_level }   for passives, masteries and buffs: value at level n = base + per_level * (n - 1)
local _, ns = ...
ns = ns or {}

local S = {}
ns.Skills = S

local function skill(t) S[#S + 1] = t; return t end

------------------------------------------------------------------ FIRE
skill{ id="scorch", name="Scorch", tree="fire", element="fire", req=1, prereqs={}, kind="bolt",
  mana={3,0.2}, dmg={6,10,3,4},
  syn={ {from="fireball",pct=14}, {from="meteor",pct=8}, {from="flame_spirit",pct=6} } }
skill{ id="evocation", name="Evocation", tree="fire", element="fire", req=6, prereqs={}, kind="passive",
  effect={type="mana_regen_pct", base=30, per_level=15} }
skill{ id="dragons_breath", name="Dragon's Breath", tree="fire", element="fire", req=6, prereqs={"scorch"}, kind="cone",
  mana={2,0.3}, dmg={4,8,2,3},
  syn={ {from="flamestrike",pct=9}, {from="flame_spirit",pct=6}, {from="scorch",pct=6} } }
skill{ id="blazing_speed", name="Blazing Speed", tree="fire", element="fire", req=12, prereqs={"evocation","dragons_breath"}, kind="trail",
  mana={10,0.3}, dmg={5,9,2,3}, effect={type="move_speed_pct", base=20, per_level=2},
  syn={ {from="dragons_breath",pct=8} } }
skill{ id="fireball", name="Fireball", tree="fire", element="fire", req=18, prereqs={"scorch"}, kind="aoe",
  mana={5,0.3}, dmg={30,45,9,12},
  syn={ {from="scorch",pct=14}, {from="meteor",pct=9}, {from="flame_spirit",pct=7} } }
skill{ id="flamestrike", name="Flamestrike", tree="fire", element="fire", req=24, prereqs={"blazing_speed","dragons_breath"}, kind="zone",
  mana={14,0.6}, dmg={10,18,4,6},
  syn={ {from="fireball",pct=8}, {from="dragons_breath",pct=8} } }
skill{ id="combustion", name="Combustion", tree="fire", element="fire", req=30, prereqs={"flamestrike"}, kind="buff",
  mana={25,0.5}, effect={type="fire_dmg_buff_pct", base=20, per_level=6} }
skill{ id="meteor", name="Meteor", tree="fire", element="fire", req=30, prereqs={"fireball","flamestrike"}, kind="aoe",
  mana={22,1.0}, dmg={60,90,20,28},
  syn={ {from="fireball",pct=12}, {from="flamestrike",pct=6} } }
skill{ id="master_of_flame", name="Master of Flame", tree="fire", element="fire", req=30, prereqs={"evocation"}, kind="mastery",
  effect={type="dmg_bonus_pct", base=30, per_level=7} }
skill{ id="flame_spirit", name="Flame Spirit", tree="fire", element="fire", req=30, prereqs={"flamestrike","fireball"}, kind="summon",
  mana={30,0.8}, dmg={10,16,5,7},
  syn={ {from="flamestrike",pct=8}, {from="fireball",pct=7} } }

------------------------------------------------------------------ COLD
skill{ id="frostbolt", name="Frostbolt", tree="cold", element="cold", req=1, prereqs={}, kind="bolt",
  mana={3,0.2}, dmg={5,8,2,3}, effect={type="chill_pct", base=25, per_level=1},
  syn={ {from="ice_lance",pct=12}, {from="glacial_spike",pct=9}, {from="frozen_orb",pct=6} } }
skill{ id="ice_barrier", name="Ice Barrier", tree="cold", element="cold", req=1, prereqs={}, kind="buff",
  mana={10,0.5}, effect={type="absorb", base=40, per_level=15} }
skill{ id="frost_nova", name="Frost Nova", tree="cold", element="cold", req=6, prereqs={"frostbolt"}, kind="aoe",
  mana={9,0.4}, dmg={4,9,2,3},
  syn={ {from="blizzard",pct=6}, {from="frozen_orb",pct=5} } }
skill{ id="ice_lance", name="Ice Lance", tree="cold", element="cold", req=6, prereqs={"frostbolt"}, kind="bolt",
  mana={6,0.3}, dmg={12,18,4,6}, effect={type="freeze_chance_pct", base=10, per_level=1},
  syn={ {from="frostbolt",pct=11}, {from="glacial_spike",pct=8} } }
skill{ id="frost_armor", name="Frost Armor", tree="cold", element="cold", req=6, prereqs={"ice_barrier"}, kind="buff",
  mana={12,0.4}, effect={type="defense_pct", base=15, per_level=5} }
skill{ id="glacial_spike", name="Glacial Spike", tree="cold", element="cold", req=18, prereqs={"ice_lance"}, kind="aoe",
  mana={7,0.4}, dmg={20,30,7,10},
  syn={ {from="frostbolt",pct=9}, {from="ice_lance",pct=11} } }
skill{ id="blizzard", name="Blizzard", tree="cold", element="cold", req=24, prereqs={"glacial_spike","frost_nova"}, kind="zone",
  mana={23,1.0}, dmg={25,40,10,14},
  syn={ {from="glacial_spike",pct=9}, {from="ice_lance",pct=6}, {from="frost_nova",pct=8} } }
skill{ id="icicle_cloak", name="Icicle Cloak", tree="cold", element="cold", req=24, prereqs={"frost_armor","frost_nova"}, kind="buff",
  mana={14,0.5}, dmg={10,16,4,6},
  syn={ {from="frostbolt",pct=5} } }
skill{ id="frozen_orb", name="Frozen Orb", tree="cold", element="cold", req=30, prereqs={"blizzard"}, kind="aoe",
  mana={25,1.0}, dmg={40,60,12,17},
  syn={ {from="blizzard",pct=7}, {from="glacial_spike",pct=8} } }
skill{ id="piercing_cold", name="Piercing Cold", tree="cold", element="cold", req=30, prereqs={"frost_nova"}, kind="mastery",
  effect={type="resist_pierce_pct", base=20, per_level=4} }

------------------------------------------------------------------ LIGHTNING
skill{ id="arcing_bolts", name="Arcing Bolts", tree="lightning", element="lightning", req=1, prereqs={}, kind="bolt",
  mana={2,0.2}, dmg={3,8,1,3},
  syn={ {from="chain_lightning",pct=6}, {from="lightning_bolt",pct=8}, {from="storm_cloud",pct=6} } }
skill{ id="static_shock", name="Static Shock", tree="lightning", element="lightning", req=6, prereqs={"arcing_bolts"}, kind="aoe",
  mana={9,0.4}, effect={type="life_cut_pct", base=25, per_level=1} }
skill{ id="force_pull", name="Force Pull", tree="lightning", element="lightning", req=6, prereqs={"arcing_bolts"}, kind="utility",
  mana={4,0.1} }
skill{ id="thunder_nova", name="Thunder Nova", tree="lightning", element="lightning", req=12, prereqs={"static_shock"}, kind="aoe",
  mana={15,0.5}, dmg={6,12,3,5},
  syn={ {from="lightning_bolt",pct=7}, {from="chain_lightning",pct=5} } }
skill{ id="lightning_bolt", name="Lightning Bolt", tree="lightning", element="lightning", req=18, prereqs={"thunder_nova"}, kind="bolt",
  mana={8,0.3}, dmg={15,70,5,22},
  syn={ {from="arcing_bolts",pct=8}, {from="thunder_nova",pct=6} } }
skill{ id="chain_lightning", name="Chain Lightning", tree="lightning", element="lightning", req=18, prereqs={"arcing_bolts","thunder_nova"}, kind="bolt",
  mana={9,0.3}, dmg={8,40,3,12},
  syn={ {from="arcing_bolts",pct=8}, {from="thunder_nova",pct=5} } }
skill{ id="blink", name="Blink", tree="lightning", element="lightning", req=18, prereqs={"force_pull"}, kind="utility",
  mana={24,-0.5} }
skill{ id="storm_cloud", name="Storm Cloud", tree="lightning", element="lightning", req=24, prereqs={"chain_lightning"}, kind="zone",
  mana={19,0.7}, dmg={10,40,4,14},
  syn={ {from="lightning_bolt",pct=7}, {from="chain_lightning",pct=7} } }
skill{ id="mana_shield", name="Mana Shield", tree="lightning", element="lightning", req=24, prereqs={"blink"}, kind="buff",
  mana={0,0}, effect={type="mana_shield_pct", base=30, per_level=2} }
skill{ id="conductor", name="Conductor", tree="lightning", element="lightning", req=30, prereqs={"blink"}, kind="mastery",
  effect={type="mana_discount_pct", base=10, per_level=2.5} }

------------------------------------------------------------------ lookup
S.byId = {}
for _, sk in ipairs(S) do S.byId[sk.id] = sk end
S.trees = { "fire", "cold", "lightning" }
S.MAX_POINTS = 20       -- points that can be spent in one skill
S.MIN_MANA = 1          -- a skill never costs less than this

return S
