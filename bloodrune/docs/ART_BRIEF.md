# Bloodrune — Sprite Art Brief (for an image-generation agent)

Paste this whole file (or the relevant parts) to an image-generation model/agent.
Generate **one PNG per unit** using the shared **STYLE + TECH block**, appended to
each unit's one-line description. Send the files back named exactly by their `id`
(e.g. `sorceress.png`, `fallen.png`) and we drop them straight into the game.

---

## What the game is

**Bloodrune** is a dark-fantasy action-roguelite — **Diablo 2 condensed into a
Vampire-Survivors run**. You drop into one big gothic arena and the only control is
**moving**; your skills auto-fire. A horde of the damned closes in from every side,
you kite and blast them, grab the loot they drop, and fight your way through the
eight areas of **Act 1** — each ending in a named boss — down to **Andariel,
Maiden of Anguish**. Between areas you return to a torch-lit **town** to gear up.
The tone is **Diablo 2**: grim, medieval, blood and candlelight, monstrous but
readable. Not cute, not cartoony, not neon.

---

## STYLE + TECH block (append this to EVERY unit prompt)

> Dark-fantasy action-RPG game sprite in the style of Diablo 2 / classic gothic
> ARPGs. **Single character, full body, 3/4 top-down view** (camera looking down
> at ~30–45°, as in an isometric ARPG), facing toward the lower-right/viewer.
> Hand-painted, richly shaded, moody. **Lighting comes from the upper-left**
> (warm torchlight), deep shadows on the lower-right. Grim medieval palette: soot
> black, dried-blood crimson (#8e1c1c–#c62828), tarnished gold (#c8a24a), cold
> steel-blue (#6f8a99), bone, leather browns. **Transparent background (alpha),
> no scene, no ground, no shadow baked in, no border, no text, no UI.** The
> character fills the frame, **centered horizontally, feet near the bottom edge**.
> Square image, **512×512**, crisp edges, clean silhouette that reads at small
> size. Consistent scale and lighting across all sprites in the set.

*(If you prefer pixel art instead of painted, swap the first two sentences for:
"Detailed 32-bit pixel-art game sprite, dark-fantasy ARPG, single character full
body, 3/4 top-down view" — but keep everything from "Lighting comes from…"
onward, and keep ALL sprites in the SAME style.)*

---

## Units to generate (`id` → one-line description)

### Hero classes (the player)
- **`sorceress`** — a lithe human sorceress in a deep-blue hooded robe, pale
  face shadowed by the hood, holding a glowing cyan crystal orb; arcane, elegant.
- **`barbarian`** — a hulking bare-chested warrior, fur and leather, a horned iron
  helm, gripping a heavy two-handed battle-axe; brutal, scarred.
- **`amazon`** — an agile warrior-woman in studded leather, ponytail, drawing a
  longbow, javelin on her back; lean and poised.
- **`necromancer`** — a gaunt pale spellcaster in a charcoal-grey hooded robe,
  bone ornaments, a skull-topped staff, sunken glowing eyes; sinister, cold.

### Common monsters (the horde)
- **`fallen`** — a small red-skinned imp/demon, big pointed ears, little horns,
  glowing yellow eyes, a crude spear; scrawny and vicious.
- **`zombie`** — a rotting humanoid corpse, greenish-grey mottled flesh, torn
  clothes, one milky eye, arms reaching; slow and grim.
- **`quill_rat`** — a large hunched vermin-beast bristling with sharp quills along
  its back, a long snout, mangy brown fur; it flings quills.
- **`goatman`** — a muscular goat-headed beastman (Moon Clan), big curved horns,
  shaggy fur, hooves, wielding a crude club or polearm.
- **`archer`** — a "Dark Ranger": a hooded corrupted human archer in tattered
  dark-green leathers, drawing a bow, face lost in shadow.
- **`shaman`** — a Fallen shaman: a robed red imp-priest holding a flaming staff,
  bone fetishes and skulls, casting; the pack's healer/reviver.
- **`guardian`** — a Fallen champion: a bigger, armored red demon with a shield
  and spiked helm, a bodyguard for casters.

### Act 1 bosses / super-uniques (larger, menacing "hero" versions)
- **`corpsefire`** — a bloated undead horror, the leader of the Den; swollen
  grey-green flesh, glowing red wounds, oozing; heals when it hits.
- **`bishibosh`** — a powerful Fallen shaman wreathed in fire, elaborate skull
  headdress, staff blazing; a caster boss.
- **`blood_raven`** — a corrupted undead huntress, a former Sister, in blackened
  armor, firing burning arrows, wisps of raised dead around her.
- **`rakanishu`** — a shrieking Fallen champion crackling with lightning, wild
  eyes, a glowing sword; fast and frenzied.
- **`treehead_woodfist`** — a monstrous goat-brute of the Dark Wood, huge, mossy,
  gnarled, slow and hulking, tree-trunk arms.
- **`the_countess`** — a gothic vampiric noblewoman on ruined ramparts, flowing
  black-and-crimson gown, raining fire, cruel and regal.
- **`the_smith`** — a massive demonic blacksmith of the Barracks, hammer and anvil,
  molten metal, iron plating, glowing forge-eyes.
- **`andariel`** — **the Act 1 final boss**, Maiden of Anguish: a demonic
  spider-queen woman, pale torso above a chitinous many-legged lower body,
  cascading dark hair, dripping venom; terrifying and beautiful.

*(Optional extras if you want more later: tile textures for the ground — cracked
gothic flagstone, blood-soaked moor, catacomb stone — as seamless 512×512 tiles;
and loot/rune icons. Ask and I'll spec these too.)*

---

## How to send them back

- One transparent **PNG per unit**, named exactly by its `id` above
  (`sorceress.png`, `andariel.png`, …). 512×512 is ideal; I downscale in-engine.
- Keep the **whole set in one consistent style, scale, and lighting** — generate
  them in a single session / with the same style block so they read as one game.
- Hand me the files (or a zip). I embed each as a data-URI, swap it in for the
  matching unit, and add idle/hit framing. The game already has a sprite slot for
  every `id`, so it's a drop-in — no code changes needed on your side.
