# Bloodrune redesign — v1 build slices

Vertical slices from `prd-bloodrune-redesign.md`, dependency-ordered. Each is a
tracer bullet testable at the deterministic engine seam
(`bloodrune/tests/*.test.js` via `node --test`). Built autonomously toward a
playable v1 (Sorceress + Act 1).

- [ ] **S1 — Synergy engine + Sorceress trees (M1, headline).** Rewrite
  `skillEffect`: `base(level=hard+gear) × synergyMult(hard-only same-tree siblings)
  × masteryMult(hard-only)`. Delete the global `masteryBonus`. Restructure the 3
  trees × 6 with synergy maps + one-point utilities. Tooltips show live synergy.
  **AC:** fed capstone ≈3× unsupported; gear +skills changes base but 0 synergy;
  cross-tree = 0; committed ≥2.5× a spread. *Blocked by: none.*
- [ ] **S2 — Elements + resistances + mastery-% + penetration + immunities (M2).**
  Damage carries an element; enemies carry per-element resist + Hell immunity;
  Mastery = ×% element; penetration from gear/utility (not Mastery); tiered
  scaling. **AC:** 50% resist halves; immune ≈0; −res restores on resistant;
  Mastery multiplies but never breaks immunity. *Blocked by: S1.*
- [ ] **S3 — Loot rarity + itemTier gating + build-fit affixes (M3a).** 4 rarities;
  `itemTier` caps affix brackets so Normal<NM<Hell; affix pools incl
  element/+skill/FCR/FHR/+stat/resist/life/mana with build-fit tags; ~10–15%
  upgrade target. **AC:** upgrade fraction in band across seeds; tier cap holds;
  deterministic. *Blocked by: S2 (element/resist affixes).*
- [ ] **S5 — Attributes + equip requirements (M4).** Str/Dex/Vit/Energy; ~5
  pts/level; Vit→life, Energy→mana, Str/Dex→equip gates. **AC:** equip refused
  under Str/Dex/level req; Vit/Energy change max life/mana. *Blocked by: S1.*
- [ ] **S6 — Town loop + stash + starting loadout + respec + at-risk banking (M5).**
  `phase: town|field`; `runInventory` (at-risk) vs persistent `stash`; quest
  turn-in; bank only at town; death forfeits unbanked, keeps stash; per-act
  respec; starting-loadout picker. **AC:** banking only at town; simulated field
  death discards runInventory, preserves stash; respec once/act. *Blocked by: S3, S5.*
- [ ] **S4 — Kill auto-equip + town equip/compare/salvage (M3b).** No auto-equip;
  equip/compare/salvage in town; one-key salvage → craft/reroll currency. **AC:**
  nothing auto-equips; equip is an explicit action; salvage yields currency.
  *Blocked by: S3, S6.*
- [ ] **S7 — Sockets/runes/runewords + enabler uniques (M6).** Bases roll sockets;
  runes drop tier-gated; rune sequence in a base → fixed runeword; 2–3 enabler
  uniques per build path. **AC:** runeword resolves deterministically; unique
  enabler makes a build spike (bot). *Blocked by: S3.*
- [ ] **S8 — Moment-to-moment + balance tuning + artifact smoke (M7).**
  standing-still-lethal; per-skill movement geometry audit (no 360° passive
  nuke); nuke/filler rotation; balance-bot tuning to the §8 metrics; artifact
  smoke 0 errors; host. **AC:** stationary hero dies vs moving survives; metrics
  in band; smoke clean. *Blocked by: all above.*
- [ ] **S9 — Update DESIGN.md + PLAN.md** with the redesign + roadmap (Acts 2–5,
  other classes). *Blocked by: none.*
