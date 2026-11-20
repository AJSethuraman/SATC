-- The numbers of the game: weapons, enemies, pickups. Pure data. Every number is a tuning knob.
local _, ns = ...
ns = ns or {}
local Rules = {}
ns.Rules = Rules

-- Weapons. ammo: which pool it spends; pellets: shots per trigger pull; spread: how wide they scatter (radians); rate: seconds between shots.
-- A rocket flies (speed, units a second) and bursts (radius, damage at the centre falling to nothing at the edge).
Rules.WEAPONS = {
  { id = "pistol",   name = "Flintlock Pistol",  ammo = "bullets", use = 1, dmg = 11, pellets = 1, spread = 0.015, rate = 0.38, icon = "INV_Weapon_Rifle_01", sound = 1 },
  { id = "scatter",  name = "Blunderbuss",       ammo = "shells",  use = 1, dmg = 7,  pellets = 7, spread = 0.11,  rate = 0.95, icon = "INV_Weapon_Rifle_06", sound = 2 },
  { id = "repeater", name = "Dwarven Repeater",  ammo = "bullets", use = 1, dmg = 8,  pellets = 1, spread = 0.035, rate = 0.12, icon = "INV_Weapon_Rifle_04", sound = 3 },
  { id = "rocket",   name = "Goblin Rocket Launcher", ammo = "rockets", use = 1, dmg = 90, pellets = 1, spread = 0, rate = 1.0, icon = "INV_Misc_Bomb_02", sound = 2,
    speed = 9, radius = 2.2 },
}
Rules.AMMO_MAX = { bullets = 200, shells = 50, rockets = 30 }
Rules.START = { hp = 100, armor = 0, bullets = 50, shells = 0, rockets = 0, weapons = { true, false, false, false } }
Rules.MAX_HP, Rules.MAX_ARMOR = 100, 100
Rules.ARMOR_ABSORB = 0.5                          -- armour takes this share of each hit while it lasts

-- Enemies. kind: melee (bites when close), shoot (a bullet that may miss), fire (a slow fireball you can step out of).
-- speed in units a second; range is how far it attacks from; windup is the warning before a ranged attack.
Rules.ENEMIES = {
  wolf    = { name = "Moor Wolf",       cid = 299,  hp = 18, speed = 3.4, kind = "melee", dmg = { 4, 8 },   cool = 0.6, reach = 0.85, r = 0.3, wake = 11 },
  kobold  = { name = "Kobold Miner",    cid = 6,    hp = 22, speed = 1.6, kind = "shoot", dmg = { 4, 10 },  cool = 1.1, range = 12, windup = 0.35, chance = 0.55, r = 0.3, wake = 13 },
  murloc  = { name = "Murloc Forager",  cid = 46,   hp = 40, speed = 2.2, kind = "melee", dmg = { 8, 14 },  cool = 0.9, reach = 0.9, r = 0.32, wake = 11 },
  imp     = { name = "Gloom Imp",       cid = 3101, hp = 35, speed = 1.8, kind = "fire",  dmg = { 10, 18 }, cool = 1.8, range = 14, windup = 0.5, shot = 6, r = 0.3, wake = 14 },
  boar    = { name = "Tusker",          cid = 3098, hp = 90, speed = 3.0, kind = "melee", dmg = { 14, 24 }, cool = 1.0, reach = 1.0, r = 0.4, wake = 12 },
  boss    = { name = "Gorefang the Unwelcome", cid = 3098, hp = 700, speed = 2.5, kind = "fire", dmg = { 18, 30 }, cool = 1.6, range = 16, windup = 0.7, shot = 7,
              melee = { dmg = { 24, 36 }, reach = 1.4, cool = 1.1 }, r = 0.7, wake = 20, scale = 1.8, boss = true },
}
Rules.HP_PER_LEVEL = 0.12                         -- every level on, enemies have this much more life

-- Pickups. give: what it adds. A weapon pickup also gives the weapon (by index) and some ammo for it.
Rules.ITEMS = {
  health  = { name = "Healing Potion",    icon = "INV_Potion_54", give = { hp = 25 } },
  bigheal = { name = "Greater Potion",    icon = "INV_Potion_51", give = { hp = 50 } },
  armor   = { name = "Plate Armor",       icon = "INV_Chest_Plate06", give = { armor = 40 } },
  bullets = { name = "Powder and Shot",   icon = "INV_Misc_Ammo_Bullet_01", give = { bullets = 25 } },
  shells  = { name = "Blunderbuss Shot",  icon = "INV_Misc_Ammo_Gunpowder_01", give = { shells = 10 } },
  rockets = { name = "Goblin Rockets",    icon = "INV_Misc_Bomb_05", give = { rockets = 5 } },
  scatter = { name = "Blunderbuss",       icon = "INV_Weapon_Rifle_06", give = { weapon = 2, shells = 10 } },
  repeater = { name = "Dwarven Repeater", icon = "INV_Weapon_Rifle_04", give = { weapon = 3, bullets = 40 } },
  rocket  = { name = "Goblin Rocket Launcher", icon = "INV_Misc_Bomb_02", give = { weapon = 4, rockets = 6 } },
  key     = { name = "Iron Key",          icon = "INV_Misc_Key_03", give = { key = 1 } },
}

-- Walls: kind -> texture file id and a plain colour to fall back on. 1-4 are the room walls, 5 a door, 6 a locked door.
Rules.WALLS = {
  [1] = { file = 129765, color = { 0.55, 0.52, 0.5 } },
  [2] = { file = 2316172, color = { 0.6, 0.35, 0.3 } },
  [3] = { file = 126995, color = { 0.4, 0.5, 0.55 } },
  [4] = { file = 2930451, color = { 0.45, 0.25, 0.3 } },
  [5] = { file = 418811, color = { 0.5, 0.35, 0.2 } },
  [6] = { file = 428572, color = { 0.7, 0.15, 0.15 } },
}
Rules.DOOR, Rules.LOCKED = 5, 6

-- Sounds, by file id (community listfile): gunfire, a bullet's impact, a rocket's burst, a door, a pickup, a creature waking, hurt, dying.
Rules.SOUNDS = { shot = { 567721, 567718, 567722 }, impact = 1315092, explode = 568461, fire = 569062, door = 566647, pickup = 567428,
                 wake = 545128, hurt = 545127, die = 545132, bite = 545129, win = 567413 }

-- The campaign: five levels, the last with the boss.
Rules.LEVELS = 5
Rules.LEVEL_NAMES = { "The Gloam Crypt", "Bonewind Keep", "The Rotted Armory", "The Sunken Barracks", "Gorefang's Lair" }
-- Which enemies appear from which level.
Rules.ROSTER = { { "wolf", "kobold" }, { "wolf", "kobold", "murloc" }, { "kobold", "murloc", "imp" }, { "murloc", "imp", "boar", "wolf" }, { "imp", "boar", "murloc", "kobold" } }

return Rules
