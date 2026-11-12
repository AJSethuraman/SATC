# Service Inviter: services, providers and tabs (design for 2.0)

Written 12 Nov 2026 from the owner's asks the same day. Nothing here is built yet.

## What the owner asked for

- "a mage page": setup split so Lockpicking, mage food & water and portals live on their own page.
- "a mage port is a re-service we can charge for it and other like it": every service can be charged.
- "we should have options for anything - paid or free. if no price but we offer, assume free"
- "if we are in TB summoning in TB it implies we only invite [for] TB"
- "i have a friend in my party and he is screwing around somewhere else, i can help our group by
  capturing his potential customers ... and also it would know not to invite people he can't service"
- "we can turn them wholesale off/on by simply not offering mage services"
- Facts about the game are ours to find and get right, not questions for the owner.

## The model

**A service** is something the group sells: summons, portals, food & water, lockpicking,
healthstones, soulstones, buffs. Each one has:

| Setting | Meaning |
|---|---|
| Offer it | Off = it doesn't exist. This is the wholesale off switch. |
| Price | Gold and silver. Blank = free. |
| Invite buyers | Invite people who ask for it in chat. Off = only offered on arrival. |
| Buyers say | The words that mark a request for it (editable, with tested defaults). |

**A provider** is someone in the group who can do a service: you, or a party/raid member. The
addon reads each member's class, level, faction and zone from the game, so it knows who can do
what without being told. A service only invites while someone in the group can provide it: if the
mage leaves, portal invites stop.

**Where** comes from the provider, not a checkbox:

- **Summons** bring the customer to where the warlock is standing. The destination is the
  warlock's current zone. A summon also answers port requests to that place (1.6.0 rule, kept).
- **Portals** send the customer from where the mage is to a city the mage has a portal for. The
  customer has to come to the mage. Port requests only, never summon requests.
- **Food & water, lockpicking, stones, buffs** need the customer to come to the provider.

**Who gets paid** defaults to whoever does the service ({payee} in messages). "I collect the
payment" overrides that and sends everything to you.

## Facts the design relies on, and where they come from

WoW: Forever is a third version of the game (launched 4 Nov 2026), levels 1-60, Classic-era
content reworked, Mainline addon restrictions. Facts below are from Forever-specific spell
databases and guides, searched 12 Nov 2026. They're confirmed in game by the addon itself where
possible (see "Checked in game").

| Fact | Value | Sources |
|---|---|---|
| Horde mage portals | Orgrimmar and Undercity at 40, Thunder Bluff at 50, reagent Rune of Portals | db.icy-veins.com/wow-forever/spells/11418, metabot.gg (Portal: Orgrimmar), zockify.com/forever/mage, wow4ever.quest |
| Alliance mage portals | Stormwind and Ironforge at 40, Darnassus at 50 (guides; same pattern as Horde) | conquestcapped.com mage overview, mobalytics mage guide |
| No group portal to Dalaran | Teleport: Dalaran at 50 is self-only | conquestcapped.com, foreverchanges.pro (search summaries) |
| Mages portal only to capitals | So the old Port column for Booty Bay, Gadgetzan, Everlook, Ratchet and Crossroads offered things no mage can do | same |
| Ritual of Summoning | Unchanged from Classic, learned at 20, spell 698 | foreverchanges.pro/class/warlock, metabot.gg |
| Portal of Summoning | New at 60: a portal two members use to summon another. Counts as a summon. | allthings.how warlock abilities, conquestcapped.com warlock abilities |
| Lockpicking | Rogue skill, up to 300 at 60, learned around 16 | warcrafttavern.com/forever/guides/lockpicking, leprestore.com lockpicking guide |

### Checked in game, not trusted from a list

- **Your own spells**: the addon reads your spellbook (Portal: X, Ritual of Summoning, Portal of
  Summoning, Pick Lock, Conjure Food/Water) and offers only what you know.
- **A friend's spells** can't be read. Their portals are inferred from faction and level per the
  table above, shown to you, and can be unticked if they haven't trained one.
- **Summon casts** are recognized by exact spell name (Ritual of Summoning, Portal of Summoning),
  never by "contains ritual" (which caught Ritual of Doom in 1.4.0).

## Tabs

By class, because a provider is a person of a class: **Inviting** (channels, matching, what's
being sold right now), **Warlock**, **Mage**, **Rogue**, **Buffs** (free extras by default),
**Payment** (who collects, the messages). Each class tab lists who in the group can do it.

## Build order

Each slice ships on its own and keeps every earlier test passing.

1. Services: the per-service settings (offer, price/free, invite, buyers say), the tabbed window,
   Payment with {payee}. Summons behave as in 1.6.0.
2. Mage, rogue and warlock services: portals (spellbook for you, faction and level for a friend),
   food & water, lockpicking, stones; matching tested against real request lines.
3. Providers: services follow who is in the group; summons go to the warlock's zone.
