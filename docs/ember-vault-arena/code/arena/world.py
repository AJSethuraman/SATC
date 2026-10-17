from __future__ import annotations

"""The Ember Vault, hand-authored (PRD §5.2, built 18 Sep 2026).

One registry the engine reads for rooms, adjacency, grids, props, features,
caches, floor items, monsters, wild-swing reactions, the contraction schedule
and the board layout. ``rules``, ``grid``, ``combat`` and the board page take
their tables from here, so a room drawn here is a room everywhere and no
effect can apply undisclosed. The map never varies by seed.

Sixteen locations, the session's drawing, every name reversible by the firm:

    July's five, unchanged in shape and kept first so the record reads on:
      threshold (start) -- ironwood_gate / ossuary_gate (seals, guardians,
      caches) -- vault (the Warden, the Crown) -- egress
    the outer ring, off the Threshold, act I ground:
      bell_tower (cache), drowned_cellar (a lurker over a cache),
      lantern_walk joining them below the stair
    the deep west, off the Ironwood Gate:
      root_hollow (cache), sap_works (cache, hazards), and down to
    the_gallery, the one long hall joining west to east, with
      the_undercroft hanging off its middle (cache)
    the deep east, off the Ossuary Gate:
      reliquary (a relic on the floor), charnel_stair (a hound), bone_well
      (cache, a dead end)
    beyond the Egress: parapet (open sky, a dead end)

Contraction (act IV only) seals the ring and the deeps from the outside in,
two rooms on the last two rounds, so round 48 is played in the Vault, the
Egress and the Parapet alone; every room still open at the end is reachable
from the Vault (``validate`` proves it). The bigger world's cooperative
objective sites (PRD §5.3) are marked as features here (the Gallery's two
braziers) and wired in a later slice.
"""

from typing import Any

from . import items

WORLD_VERSION = "ember-vault-world-1.0"

START_ROOM = "threshold"
VAULT_ROOM = "vault"
EGRESS_ROOM = "egress"
CONTRACTION_REFUGE = "vault"  # force-move destination, a constant not an adjacency

# Rooms that never seal: the last round's ground.
NEVER_SEALS: tuple[str, ...] = ("vault", "egress", "parapet")

# Contraction: ordered, absolute round numbers, every one inside act IV and
# before the last round (rules.py proves the act; ``validate`` proves the rest).
# Outside in: the ring first, then the deeps, then the gates last.
CONTRACTION_SCHEDULE: tuple[tuple[int, str], ...] = (
    (37, "lantern_walk"),
    (38, "bell_tower"),
    (39, "bone_well"),
    (40, "the_undercroft"),
    (41, "sap_works"),
    (42, "charnel_stair"),
    (43, "drowned_cellar"),
    (44, "the_gallery"),
    (45, "threshold"),
    (46, "root_hollow"),
    (46, "reliquary"),
    (47, "ironwood_gate"),
    (47, "ossuary_gate"),
)

# What each cache holds. Fixed for now; seeded placement within declared
# sites (PRD §5.2) is a later slice.
CACHES: dict[str, str] = {
    "ironwood_gate": "veteran_blade",
    "ossuary_gate": "healing_tonic",
    "bell_tower": "healing_tonic",
    "drowned_cellar": "veteran_blade",
    "root_hollow": "ironwood_splinter",
    "sap_works": "ironwood_splinter",
    "the_undercroft": "healing_tonic",
    "bone_well": "veteran_blade",
}

# Items lying on the floor when the match opens.
FLOOR_ITEMS: dict[str, list[str]] = {
    "reliquary": ["marrow_reliquary"],
}

# Cooperative objective sites (PRD §5.3): a site wakes only when every one of
# its hands is lent by a different character in the same round; each of them
# scores its points; a round with too few hands lapses in public. The hands
# are features of the room, so the board draws them. Points are the
# session's, tuned later on the simulator (item 5).
SITES: dict[str, dict[str, Any]] = {
    "gallery_braziers": {
        "name": "the Gallery's braziers", "room": "the_gallery",
        "hands": ["brazier_west", "brazier_east"], "points": 4,
        "done_text": "Both braziers catch at once and the Long Gallery blazes end to end.",
    },
    "well_winch": {
        "name": "the Bone Well's winch", "room": "bone_well",
        "hands": ["winch_crank", "winch_brake"], "points": 3,
        "done_text": "Crank and brake move together and the well's bucket comes up out of the dark.",
    },
    "tower_bell": {
        "name": "the Bell Tower's bell", "room": "bell_tower",
        "hands": ["bell_rope_north", "bell_rope_east", "bell_rope_south"], "points": 5,
        "done_text": "Three ropes pull as one and the cracked bell speaks over the whole vault.",
    },
}

# Each monster's canned lines (PRD §5.6, §5.27), spoken when it strikes,
# keyed by the round so a replay says the same thing at the same moment.
MONSTERS: dict[str, dict[str, Any]] = {
    "ironwood_guardian": {"name": "Ironwood Guardian", "kind": "guardian", "room": "ironwood_gate", "tile": [2, 1],
                          "reach": 1, "max_hp": 12, "power": 3, "armor": 1,
                          "lines": ["The gate does not open for the living.", "Sap for sap.", "Roots remember every footstep.",
                                    "You brought steel to a tree.", "Grow still."]},
    "ossuary_guardian": {"name": "Ossuary Guardian", "kind": "guardian", "room": "ossuary_gate", "tile": [2, 1],
                         "reach": 1, "max_hp": 12, "power": 3, "armor": 0,
                         "lines": ["Bone to the bone-rack.", "You will fit. They all fit.", "The arch counts its teeth.",
                                   "Breathe quieter.", "Another rib for the wall."]},
    "crown_warden": {"name": "Crown Warden", "kind": "warden", "room": "vault", "tile": [3, 2],
                     "reach": 2, "max_hp": 20, "power": 4, "armor": 2,
                     "lines": ["The Crown is not yours to wear.", "It burns whoever holds it. Ask me.", "Kneel, and it is quicker.",
                               "Ash is what the vault keeps.", "Come closer to the fire."]},
    "cellar_drowner": {"name": "Cellar Drowner", "kind": "guardian", "room": "drowned_cellar", "tile": [1, 1],
                       "reach": 1, "max_hp": 9, "power": 2, "armor": 0,
                       "lines": ["Down. Down.", "The water keeps what it takes.", "Nobody searches here.", "Cold, is it?",
                                 "Under. Stay under."]},
    "charnel_hound": {"name": "Charnel Hound", "kind": "guardian", "room": "charnel_stair", "tile": [1, 1],
                      "reach": 1, "max_hp": 10, "power": 3, "armor": 0,
                      "lines": ["*a low growl over the bones*", "*teeth, then the landing rail*", "*it circles the stair*",
                                "*the heap shifts under it*", "*it does not bark; it waits*"]},
}


def _p(kind: str, pid: str, name: str) -> dict[str, str]:
    return {"kind": kind, "id": pid, "name": name}


# Each room: the slim record the state carries (name, description, neighbors,
# kind, seal, cache, guardian), its grid (w, h, doors, features, spawn), its
# props, its wild-swing reaction and where the board draws it (tiles).
ROOMS: dict[str, dict[str, Any]] = {
    # ---- July's five -------------------------------------------------------
    "threshold": {
        "name": "The Threshold",
        "description": "Rain hammers the outer stair; two gates wait inland, a bell tower east and a drowned cellar west.",
        "neighbors": ["bell_tower", "drowned_cellar", "ironwood_gate", "ossuary_gate"],
        "kind": "start", "seal_id": None, "cache_id": None, "guardian_id": None,
        "grid": {"w": 5, "h": 3,
                 "doors": {"ironwood_gate": (0, 1), "ossuary_gate": (4, 1), "drowned_cellar": (0, 2), "bell_tower": (4, 2)},
                 "features": {},
                 "spawn": [(2, 2), (1, 2), (3, 2), (2, 1), (1, 1), (3, 1), (0, 2), (4, 2)]},
        "props": {"1,0": _p("blocking", "broken_statue", "Broken Statue"), "3,0": _p("blocking", "broken_statue_2", "Toppled Statue"),
                  "0,0": _p("cover", "stair_wall", "Stair Wall"), "4,0": _p("cover", "rain_barrel", "Rain Barrel")},
        "reaction": {"reaction_id": "threshold_sluice", "flavor": "Rain sluices off the threshold stone and shoves {target} off its brace.", "effect_kind": "strip_guard"},
        "layout": (12.0, 14.5),
    },
    "ironwood_gate": {
        "name": "The Ironwood Gate",
        "description": "Living timber grown through the arch, wet with sap; a hollow of roots opens west.",
        "neighbors": ["root_hollow", "threshold", "vault"],
        "kind": "gate", "seal_id": "ironwood_seal", "cache_id": "ironwood_cache", "guardian_id": "ironwood_guardian",
        "grid": {"w": 5, "h": 4,
                 "doors": {"threshold": (2, 3), "vault": (2, 0), "root_hollow": (0, 1)},
                 "features": {"seal": (4, 0), "cache": (0, 0)},
                 "spawn": [(2, 3), (1, 3), (3, 3), (2, 2), (1, 2), (3, 2), (0, 3), (4, 3)]},
        "props": {"1,1": _p("blocking", "ironwood_trunk", "Ironwood Trunk"), "3,1": _p("blocking", "ironwood_trunk_2", "Split Trunk"),
                  "0,2": _p("cover", "root_tangle", "Root Tangle"), "4,2": _p("cover", "bark_shield", "Bark Shelf"),
                  "1,2": _p("hazard", "sap_pool", "Boiling Sap"), "3,2": _p("hazard", "sap_pool_2", "Sap Seep")},
        "reaction": {"reaction_id": "ironwood_splinter_shear", "flavor": "The swing shears a blade of ironwood off the gate; it clatters to the floor.",
                     "effect_kind": "reveal_item", "item_id": "ironwood_splinter", "max_uses": 1},
        "layout": (6.5, 9.0),
    },
    "ossuary_gate": {
        "name": "The Ossuary Gate",
        "description": "A stacked-bone arch that clicks when anyone breathes; a reliquary lies east.",
        "neighbors": ["reliquary", "threshold", "vault"],
        "kind": "gate", "seal_id": "ossuary_seal", "cache_id": "ossuary_cache", "guardian_id": "ossuary_guardian",
        "grid": {"w": 5, "h": 4,
                 "doors": {"threshold": (2, 3), "vault": (2, 0), "reliquary": (4, 1)},
                 "features": {"seal": (0, 0), "cache": (4, 0)},
                 "spawn": [(2, 3), (1, 3), (3, 3), (2, 2), (1, 2), (3, 2), (0, 3), (4, 3)]},
        "props": {"1,1": _p("blocking", "bone_stack", "Bone Stack"), "3,1": _p("blocking", "bone_stack_2", "Femur Pile"),
                  "0,2": _p("cover", "skull_wall", "Skull Wall"), "4,2": _p("cover", "rib_arch", "Rib Arch"),
                  "2,1": _p("hazard", "marrow_pit", "Marrow Pit")},
        "reaction": {"reaction_id": "ossuary_ribfall", "flavor": "The bone-rack sloughs; a rib of ash-bone lodges in {attacker}'s guard arm.",
                     "effect_kind": "attacker_damage", "amount": 1},
        "layout": (17.5, 9.0),
    },
    "vault": {
        "name": "The Ember Vault",
        "description": "The Crown burns inside its Warden.",
        "neighbors": ["egress", "ironwood_gate", "ossuary_gate"],
        "kind": "vault", "seal_id": None, "cache_id": None, "guardian_id": "crown_warden",
        "grid": {"w": 7, "h": 5,
                 "doors": {"ironwood_gate": (0, 4), "ossuary_gate": (6, 4), "egress": (3, 0)},
                 "features": {"pedestal": (3, 2)},
                 "spawn": [(3, 4), (2, 4), (4, 4), (1, 4), (5, 4), (0, 4), (6, 4), (3, 3)]},
        "props": {"1,1": _p("blocking", "vault_pillar", "Ember Pillar"), "5,1": _p("blocking", "vault_pillar_2", "Ember Pillar"),
                  "2,3": _p("cover", "fallen_pillar", "Fallen Pillar"), "4,3": _p("cover", "shield_wall", "Warden's Shieldwall"),
                  "0,2": _p("hazard", "brazier", "Open Brazier"), "6,2": _p("hazard", "brazier_2", "Open Brazier"),
                  "3,1": _p("hazard", "ember_vent", "Ember Vent")},
        "reaction": {"reaction_id": "ember_glass_flare", "flavor": "The ember-glass flares and the heat lashes everything near the plinth.",
                     "effect_kind": "burst_damage", "amount": 1},
        "layout": (11.0, 3.0),
    },
    "egress": {
        "name": "The Moonlit Egress",
        "description": "Open sky and the way out, and no way to end it early: the Crown is won by whoever holds it when the last round ends. A parapet runs on.",
        "neighbors": ["parapet", "vault"],
        "kind": "egress", "seal_id": None, "cache_id": None, "guardian_id": None,
        "grid": {"w": 3, "h": 2,
                 "doors": {"vault": (1, 1), "parapet": (2, 0)},
                 "features": {},
                 "spawn": [(1, 1), (0, 1), (2, 1), (1, 0), (2, 0), (1, 1), (0, 1), (2, 1)]},
        "props": {"0,0": _p("blocking", "egress_rubble", "Rubble"), "2,1": _p("cover", "arch_stone", "Arch Stone")},
        "reaction": {"reaction_id": "egress_windfall", "flavor": "Wind off the egress arch takes the blow and gives nothing back.", "effect_kind": "none"},
        "layout": (13.0, 0.0),
    },
    # ---- the outer ring ----------------------------------------------------
    "bell_tower": {
        "name": "The Bell Tower",
        "description": "A cracked bell on a rotten frame; the rope runs down to a walk of lanterns.",
        "neighbors": ["lantern_walk", "threshold"],
        "kind": "chamber", "seal_id": None, "cache_id": "bell_cache", "guardian_id": None,
        "grid": {"w": 3, "h": 3,
                 "doors": {"threshold": (0, 1), "lantern_walk": (1, 2)},
                 "features": {"cache": (2, 0), "bell_rope_north": (1, 0), "bell_rope_east": (2, 1), "bell_rope_south": (1, 2)},
                 "spawn": [(0, 1), (1, 2), (0, 2), (1, 0), (0, 0), (2, 1), (2, 2), (2, 0)]},
        "props": {"1,1": _p("blocking", "bell_frame", "Bell Frame"), "2,2": _p("cover", "stair_rail", "Stair Rail")},
        "reaction": {"reaction_id": "bell_rope_snap", "flavor": "The bell rope snaps taut and {target} loses their footing.", "effect_kind": "strip_guard"},
        "layout": (18.5, 14.5),
    },
    "drowned_cellar": {
        "name": "The Drowned Cellar",
        "description": "Black water to the shin, casks afloat, and something under the surface that keeps the cache.",
        "neighbors": ["lantern_walk", "sap_works", "threshold"],
        "kind": "chamber", "seal_id": None, "cache_id": "cellar_cache", "guardian_id": "cellar_drowner",
        "grid": {"w": 4, "h": 3,
                 "doors": {"threshold": (3, 1), "lantern_walk": (2, 2), "sap_works": (0, 1)},
                 "features": {"cache": (1, 0)},
                 "spawn": [(3, 1), (2, 2), (3, 2), (3, 0), (0, 1), (0, 2), (1, 0), (2, 1)]},
        "props": {"2,0": _p("blocking", "cask_stack", "Cask Stack"), "0,0": _p("cover", "cistern_lip", "Cistern Lip"),
                  "1,2": _p("hazard", "black_water", "Black Water")},
        "reaction": {"reaction_id": "cellar_undertow", "flavor": "The black water heaves and drags at {attacker}'s legs.", "effect_kind": "attacker_damage", "amount": 1},
        "layout": (6.5, 14.5),
    },
    "lantern_walk": {
        "name": "The Lantern Walk",
        "description": "A long gallery of guttering lamps under the stair, joining the tower to the cellar.",
        "neighbors": ["bell_tower", "drowned_cellar"],
        "kind": "hall", "seal_id": None, "cache_id": None, "guardian_id": None,
        "grid": {"w": 8, "h": 2,
                 "doors": {"drowned_cellar": (0, 0), "bell_tower": (7, 0)},
                 "features": {},
                 "spawn": [(0, 0), (7, 0), (1, 1), (6, 1), (3, 0), (4, 1), (2, 0), (5, 0)]},
        "props": {"2,1": _p("cover", "lantern_post", "Lantern Post"), "5,1": _p("cover", "lantern_post_2", "Lantern Post"),
                  "4,0": _p("hazard", "guttering_lamp", "Guttering Lamp")},
        "reaction": {"reaction_id": "lantern_gutter", "flavor": "A lamp gutters out; the walk takes the blow in the dark.", "effect_kind": "none"},
        "layout": (10.0, 18.5),
    },
    # ---- the deep west -----------------------------------------------------
    "root_hollow": {
        "name": "The Root Hollow",
        "description": "Under the ironwood, a hollow of knotted roots with a cache wedged in the wall.",
        "neighbors": ["ironwood_gate", "sap_works"],
        "kind": "chamber", "seal_id": None, "cache_id": "hollow_cache", "guardian_id": None,
        "grid": {"w": 4, "h": 3,
                 "doors": {"ironwood_gate": (3, 1), "sap_works": (1, 2)},
                 "features": {"cache": (0, 0)},
                 "spawn": [(3, 1), (1, 2), (3, 0), (3, 2), (0, 1), (0, 2), (1, 0), (2, 2)]},
        "props": {"2,1": _p("blocking", "root_knot", "Root Knot"), "1,0": _p("cover", "hollow_wall", "Hollow Wall")},
        "reaction": {"reaction_id": "root_splinter", "flavor": "The swing bites a root and a splinter comes away with it.",
                     "effect_kind": "reveal_item", "item_id": "ironwood_splinter", "max_uses": 1},
        "layout": (1.0, 9.5),
    },
    "sap_works": {
        "name": "The Sap Works",
        "description": "Vats of boiling sap and a press frame; the floor is not to be trusted.",
        "neighbors": ["drowned_cellar", "root_hollow", "the_gallery"],
        "kind": "chamber", "seal_id": None, "cache_id": "works_cache", "guardian_id": None,
        "grid": {"w": 4, "h": 3,
                 "doors": {"root_hollow": (1, 0), "drowned_cellar": (3, 1), "the_gallery": (2, 2)},
                 "features": {"cache": (0, 0)},
                 "spawn": [(1, 0), (3, 1), (2, 2), (1, 1), (0, 2), (3, 2), (2, 0), (1, 2)]},
        "props": {"3,0": _p("cover", "press_frame", "Press Frame"), "0,1": _p("hazard", "sap_vat", "Sap Vat"),
                  "2,1": _p("hazard", "sap_vat_2", "Sap Vat")},
        "reaction": {"reaction_id": "sap_scald", "flavor": "A vat slops and the sap scalds {attacker}'s arm.", "effect_kind": "attacker_damage", "amount": 1},
        "layout": (1.0, 14.0),
    },
    "the_gallery": {
        "name": "The Long Gallery",
        "description": "One hall joins the deep west to the deep east, pillared, with two cold braziers at its heart and a hatch to the undercroft.",
        "neighbors": ["charnel_stair", "sap_works", "the_undercroft"],
        "kind": "hall", "seal_id": None, "cache_id": None, "guardian_id": None,
        "grid": {"w": 18, "h": 2,
                 "doors": {"sap_works": (0, 0), "charnel_stair": (17, 0), "the_undercroft": (9, 1)},
                 "features": {"brazier_west": (6, 1), "brazier_east": (11, 1)},
                 "spawn": [(0, 0), (17, 0), (1, 1), (16, 1), (8, 0), (9, 0), (2, 0), (15, 0)]},
        "props": {"3,0": _p("blocking", "gallery_pillar", "Pillar"), "7,0": _p("blocking", "gallery_pillar_2", "Pillar"),
                  "10,0": _p("blocking", "gallery_pillar_3", "Pillar"), "14,0": _p("blocking", "gallery_pillar_4", "Pillar"),
                  "4,1": _p("cover", "fallen_lintel", "Fallen Lintel"), "13,1": _p("cover", "fallen_lintel_2", "Fallen Lintel")},
        "reaction": {"reaction_id": "gallery_echo", "flavor": "The blow rings the length of the gallery and dies.", "effect_kind": "none"},
        "layout": (5.0, 21.5),
    },
    "the_undercroft": {
        "name": "The Undercroft",
        "description": "A low crypt under the gallery's hatch, dripping, with a cache among the coffins.",
        "neighbors": ["the_gallery"],
        "kind": "chamber", "seal_id": None, "cache_id": "undercroft_cache", "guardian_id": None,
        "grid": {"w": 4, "h": 2,
                 "doors": {"the_gallery": (2, 0)},
                 "features": {"cache": (0, 1)},
                 "spawn": [(2, 0), (1, 0), (3, 0), (2, 1), (1, 1), (0, 0), (3, 1), (0, 1)]},
        "props": {"3,1": _p("cover", "coffin_lid", "Coffin Lid")},
        "reaction": {"reaction_id": "undercroft_drip", "flavor": "A coffin lid shifts and {target} stumbles off their guard.", "effect_kind": "strip_guard"},
        "layout": (12.0, 24.0),
    },
    # ---- the deep east -----------------------------------------------------
    "reliquary": {
        "name": "The Reliquary",
        "description": "A screened altar past the bone arch; the Marrow Reliquary rests on it, unguarded and worth a great deal.",
        "neighbors": ["charnel_stair", "ossuary_gate"],
        "kind": "chamber", "seal_id": None, "cache_id": None, "guardian_id": None,
        "grid": {"w": 4, "h": 3,
                 "doors": {"ossuary_gate": (0, 1), "charnel_stair": (2, 2)},
                 "features": {"altar": (3, 0)},
                 "spawn": [(0, 1), (2, 2), (0, 0), (0, 2), (1, 2), (2, 0), (3, 1), (1, 0)]},
        "props": {"1,1": _p("blocking", "altar_screen", "Altar Screen"), "3,2": _p("cover", "prayer_bench", "Prayer Bench")},
        "reaction": {"reaction_id": "reliquary_hush", "flavor": "The screen rattles and the altar keeps its silence.", "effect_kind": "none"},
        "layout": (24.0, 9.5),
    },
    "charnel_stair": {
        "name": "The Charnel Stair",
        "description": "A broken stair down through the bone heaps; a hound keeps the landing.",
        "neighbors": ["bone_well", "reliquary", "the_gallery"],
        "kind": "chamber", "seal_id": None, "cache_id": None, "guardian_id": "charnel_hound",
        "grid": {"w": 4, "h": 3,
                 "doors": {"reliquary": (2, 0), "bone_well": (3, 1), "the_gallery": (2, 2)},
                 "features": {},
                 "spawn": [(2, 0), (3, 1), (2, 2), (3, 0), (3, 2), (1, 0), (0, 0), (2, 1)]},
        "props": {"0,1": _p("blocking", "collapsed_step", "Collapsed Step"), "1,2": _p("cover", "landing_rail", "Landing Rail"),
                  "0,2": _p("hazard", "loose_bones", "Loose Bones")},
        "reaction": {"reaction_id": "charnel_slide", "flavor": "The heap slides and a jaw of bone rakes {attacker}'s shin.", "effect_kind": "attacker_damage", "amount": 1},
        "layout": (24.0, 14.0),
    },
    "bone_well": {
        "name": "The Bone Well",
        "description": "A dry well mouth ringed with skulls, a winch, and a cache at the bottom step. A dead end.",
        "neighbors": ["charnel_stair"],
        "kind": "chamber", "seal_id": None, "cache_id": "well_cache", "guardian_id": None,
        "grid": {"w": 3, "h": 3,
                 "doors": {"charnel_stair": (0, 1)},
                 "features": {"cache": (2, 2), "winch_crank": (2, 0), "winch_brake": (2, 1)},
                 "spawn": [(0, 1), (0, 0), (1, 1), (1, 2), (2, 1), (0, 2), (2, 2), (2, 0)]},
        "props": {"1,0": _p("blocking", "well_mouth", "Well Mouth"), "2,0": _p("cover", "winch_post", "Winch Post"),
                  "0,2": _p("hazard", "bone_dust", "Bone Dust")},
        "reaction": {"reaction_id": "well_winch", "flavor": "The winch chain whips loose and knocks {target} off their brace.", "effect_kind": "strip_guard"},
        "layout": (29.0, 14.0),
    },
    # ---- beyond the egress -------------------------------------------------
    "parapet": {
        "name": "The Parapet",
        "description": "A walk along the outer wall under open sky; it goes nowhere else.",
        "neighbors": ["egress"],
        "kind": "chamber", "seal_id": None, "cache_id": None, "guardian_id": None,
        "grid": {"w": 3, "h": 2,
                 "doors": {"egress": (0, 1)},
                 "features": {},
                 "spawn": [(0, 1), (1, 1), (0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (0, 0)]},
        "props": {"2,1": _p("blocking", "fallen_merlon", "Fallen Merlon"), "2,0": _p("cover", "crenel", "Crenel")},
        "reaction": {"reaction_id": "parapet_gust", "flavor": "A gust off the wall takes the blow and gives nothing back.", "effect_kind": "none"},
        "layout": (17.0, 0.0),
    },
}

ROOM_ORDER: tuple[str, ...] = tuple(ROOMS)
SEAL_ROOMS: tuple[str, ...] = tuple(rid for rid, r in ROOMS.items() if r["seal_id"])
LAYOUT: dict[str, tuple[float, float]] = {rid: r["layout"] for rid, r in ROOMS.items()}


# ---------------------------------------------------------------------------
# views the engine modules take
# ---------------------------------------------------------------------------


def room_records() -> dict[str, dict[str, Any]]:
    """The slim room record the match state carries (static forever, P1)."""
    keys = ("name", "description", "neighbors", "kind", "seal_id", "cache_id", "guardian_id")
    return {rid: {k: (list(r[k]) if isinstance(r[k], list) else r[k]) for k in keys} for rid, r in ROOMS.items()}


def grids() -> dict[str, dict[str, Any]]:
    return {rid: {"w": r["grid"]["w"], "h": r["grid"]["h"],
                  "doors": dict(r["grid"]["doors"]), "features": dict(r["grid"]["features"]),
                  "spawn": list(r["grid"]["spawn"])} for rid, r in ROOMS.items()}


def props() -> dict[str, dict[str, dict[str, Any]]]:
    return {rid: {k: dict(v) for k, v in r["props"].items()} for rid, r in ROOMS.items()}


def reactions() -> dict[str, dict[str, Any]]:
    return {rid: dict(r["reaction"]) for rid, r in ROOMS.items()}


def monster_templates() -> dict[str, dict[str, Any]]:
    out = {}
    for mid, m in MONSTERS.items():
        out[mid] = {"id": mid, "name": m["name"], "kind": m["kind"], "room": m["room"], "tile": list(m["tile"]),
                    "reach": m["reach"], "max_hp": m["max_hp"], "hp": m["max_hp"], "power": m["power"],
                    "armor": m["armor"], "guard": 0, "death_cause": None, "defeated_by": None, "collateral_taken": 0}
    return out


def monster_line(monster_id: str, round_no: int) -> str:
    """The monster's line for this round: the table keyed by the round."""
    lines = MONSTERS[monster_id]["lines"]
    return lines[(max(1, int(round_no)) - 1) % len(lines)]


def monster_reach() -> dict[str, int]:
    return {mid: int(m["reach"]) for mid, m in MONSTERS.items()}


def sites_in(room_id: str) -> list[str]:
    return [sid for sid, site in SITES.items() if site["room"] == room_id]


def site_of_hand(hand: str) -> str | None:
    for sid, site in SITES.items():
        if hand in site["hands"]:
            return sid
    return None


def sealing_rounds() -> dict[str, int]:
    return {room: round_no for round_no, room in CONTRACTION_SCHEDULE}


# ---------------------------------------------------------------------------
# validation, at import
# ---------------------------------------------------------------------------

PROP_KINDS = ("blocking", "cover", "hazard")
REACTION_KINDS = ("strip_guard", "reveal_item", "attacker_damage", "burst_damage", "none")


def validate() -> None:
    """Every claim the docstring makes, checked: adjacency symmetric, a door
    both ways on a floor tile for every neighbour, features and spawns on the
    floor, one guardian per room and in it, caches and floor items known,
    reactions well formed, the schedule inside the map with the never-seal
    rooms never in it, every room still open at the end reachable from the
    Vault, and no two rooms overlapping on the board."""
    ids = set(ROOMS)
    for rid, r in ROOMS.items():
        g = r["grid"]
        w, h = g["w"], g["h"]
        blocked = {tuple(int(v) for v in k.split(",")) for k, p in r["props"].items() if p["kind"] == "blocking"}
        for k, p in r["props"].items():
            x, y = (int(v) for v in k.split(","))
            if not (0 <= x < w and 0 <= y < h) or p["kind"] not in PROP_KINDS:
                raise ValueError(f"{rid}: bad prop {k} {p}")
        if r["neighbors"] != sorted(r["neighbors"]) or len(set(r["neighbors"])) != len(r["neighbors"]):
            raise ValueError(f"{rid}: neighbors must be sorted and distinct")
        for n in r["neighbors"]:
            if n not in ids or rid not in ROOMS[n]["neighbors"]:
                raise ValueError(f"{rid}: adjacency to {n} is not symmetric")
            if n not in g["doors"] or rid not in ROOMS[n]["grid"]["doors"]:
                raise ValueError(f"{rid}: no door both ways with {n}")
        for n, t in g["doors"].items():
            if n not in r["neighbors"]:
                raise ValueError(f"{rid}: door to {n} which is not a neighbour")
            if not (0 <= t[0] < w and 0 <= t[1] < h) or tuple(t) in blocked:
                raise ValueError(f"{rid}: door to {n} at {t} is off the floor")
        for f, t in g["features"].items():
            if not (0 <= t[0] < w and 0 <= t[1] < h) or tuple(t) in blocked:
                raise ValueError(f"{rid}: feature {f} at {t} is off the floor")
        if len(g["spawn"]) < 8:
            raise ValueError(f"{rid}: eight spawn tiles are needed")
        for t in g["spawn"]:
            if not (0 <= t[0] < w and 0 <= t[1] < h) or tuple(t) in blocked:
                raise ValueError(f"{rid}: spawn {t} is off the floor")
        if r["cache_id"] and rid not in CACHES:
            raise ValueError(f"{rid}: cache_id without contents")
        if rid in CACHES and (not r["cache_id"] or "cache" not in g["features"]):
            raise ValueError(f"{rid}: cache contents without a cache feature")
        if r["seal_id"] and "seal" not in g["features"]:
            raise ValueError(f"{rid}: seal without a seal feature")
        if r["guardian_id"] and MONSTERS.get(r["guardian_id"], {}).get("room") != rid:
            raise ValueError(f"{rid}: guardian {r['guardian_id']} is not in it")
        re = r["reaction"]
        if re["effect_kind"] not in REACTION_KINDS:
            raise ValueError(f"{rid}: reaction kind {re['effect_kind']}")
        if re["effect_kind"] == "reveal_item" and not items.is_known_item(re.get("item_id")):
            raise ValueError(f"{rid}: reaction reveals an unknown item")
    hands_seen: set[str] = set()
    for sid, site in SITES.items():
        if site["room"] not in ids:
            raise ValueError(f"site {sid} in no room")
        if len(site["hands"]) < 2 or len(set(site["hands"])) != len(site["hands"]):
            raise ValueError(f"site {sid} needs at least two distinct hands")
        for hand in site["hands"]:
            if hand not in ROOMS[site["room"]]["grid"]["features"]:
                raise ValueError(f"site {sid}: hand {hand} is not a feature of {site['room']}")
            if hand in hands_seen:
                raise ValueError(f"hand {hand} belongs to two sites")
            hands_seen.add(hand)
        if int(site["points"]) <= 0:
            raise ValueError(f"site {sid} must be worth something")
    for mid, m in MONSTERS.items():
        if m["room"] not in ids:
            raise ValueError(f"monster {mid} in no room")
        if not m.get("lines") or not all(isinstance(x, str) and x.strip() for x in m["lines"]):
            raise ValueError(f"monster {mid} has no lines")
        if ROOMS[m["room"]]["guardian_id"] != mid:
            raise ValueError(f"monster {mid} is not its room's guardian")
        g = ROOMS[m["room"]]["grid"]
        if not (0 <= m["tile"][0] < g["w"] and 0 <= m["tile"][1] < g["h"]):
            raise ValueError(f"monster {mid} off the floor")
    for room, item_id in CACHES.items():
        if not items.is_known_item(item_id):
            raise ValueError(f"cache in {room} holds unknown item {item_id}")
    for room, floor in FLOOR_ITEMS.items():
        if room not in ids or not all(items.is_known_item(i) for i in floor):
            raise ValueError(f"floor items in {room} are unknown")
    rounds = [n for n, _ in CONTRACTION_SCHEDULE]
    if rounds != sorted(rounds):
        raise ValueError("contraction schedule out of order")
    sealed = [room for _, room in CONTRACTION_SCHEDULE]
    if len(set(sealed)) != len(sealed):
        raise ValueError("a room seals twice")
    for room in sealed:
        if room not in ids or room in NEVER_SEALS:
            raise ValueError(f"schedule seals {room}")
    if CONTRACTION_REFUGE in sealed or START_ROOM not in ids or VAULT_ROOM not in ids or EGRESS_ROOM not in ids:
        raise ValueError("the refuge, the start, the vault or the egress is wrong")
    # every room still open at the end is reachable from the Vault
    open_rooms = ids - set(sealed)
    seen, stack = {VAULT_ROOM}, [VAULT_ROOM]
    while stack:
        here = stack.pop()
        for n in ROOMS[here]["neighbors"]:
            if n in open_rooms and n not in seen:
                seen.add(n)
                stack.append(n)
    if seen != open_rooms:
        raise ValueError(f"rooms open at the end but cut off from the Vault: {sorted(open_rooms - seen)}")
    # the board: no two rooms overlap
    boxes = {rid: (r["layout"][0], r["layout"][1], r["layout"][0] + r["grid"]["w"], r["layout"][1] + r["grid"]["h"])
             for rid, r in ROOMS.items()}
    for a, (ax0, ay0, ax1, ay1) in boxes.items():
        if ax0 < 0 or ay0 < 0:
            raise ValueError(f"{a} is drawn off the board")
        for b, (bx0, by0, bx1, by1) in boxes.items():
            if a < b and ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                raise ValueError(f"{a} and {b} overlap on the board")


validate()
