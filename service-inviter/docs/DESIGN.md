# Service Inviter: services, providers and tabs (design for 2.0)

Written 12 Nov 2026 from the owner's asks the same day. **Built as 2.0.0 the same day** (the owner: "i like the idea"); not yet run in the game.

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

**Who gets paid** is set at two levels. The owner, 12 Nov 2026: "otherwise pay could be anyone,
not just the warlock ... what happens when they are summoned somewhere without me/the guy, it is
possible that individual tabs need an override to who the payee is, but payment can be the
overall facilitator of defaults ... or it is zone dependent".

- **Default** (General tab), one of:
  - *Whoever is where the customer ends up* (the default): you if you're in the zone the customer
    arrives in, otherwise the person doing the service. Someone is always there to collect: the
    warlock at a summon, the mage at a portal, the rogue at a lockbox.
  - *Always me*.
  - *Always* a named person: any group member, or a typed name.
- **Per service**: "Default", or any of the above for that service only.
- {payee} in every message is filled from this, so customers are told who to pay.
- Trade opens by itself only when the payee is you and the customer is in range.

## Summons: one per warlock, never a guessed place

The owner, 12 Nov 2026, on the Warlock tab's fallback list of places ("if the game can't tell
where the warlock is, summon to:"): "what's the point in this, like we might as well just not try
to identify their location for this if we check it for safety anyway. also what if we had multiple
warlocks". So:

- Each warlock in the group sells summons to wherever **that warlock** is standing. Two warlocks
  in TB and UC: the ad says `summons to TB/UC`, both are invited for, and each customer's welcome
  and payee name the warlock in the place they asked for.
- If the game can't say where a warlock is, nobody is invited for that warlock's summons. The
  fallback list is gone. The Warlock tab and `/si status` show each warlock and where they are.

## The buff button

The owner, 12 Nov 2026: "can it be like... queued to a single button somehow that always goes to the
last person or someone who asks for it" and "it would not need to be in combat used ever really -
this is really just for buffs". The game only casts from a key press, so it is one press per buff;
the addon aims a secure button (`/si bind buff F8`, and a button on the customer list) at the next
person in a queue. Queued: customers who land where you can see them, and anyone in the group who
asks in party, raid or a whisper, for each buff you offer and your class casts. A successful cast
moves to the next; "too low level" steps down a rank for the next press; leaving the group drops
them. Not re-aimed in combat (the game forbids it). A paladin picks the blessing on the Buffs tab.

Paladins (the owner: "can they say wisdom or something and it knows to queue that"): the word picks
the blessing (wisdom, might, kings, salvation, light, sanctuary); plain "blessing" or "buff" gets
the one set on the Buffs tab. Asking again switches that person's blessing rather than adding one
(a paladin's blessing replaces their last on a target). A blessing you don't have (Kings is a
talent) is not queued; you're told. Only short messages count as asks, so "I might be afk for a bit"
doesn't queue Might.

## Who gets paid is picked from the group

The owner: "can 'who gets paid' be a suggestion/drop down from the raid/party?". Every payee box has
a pick list: Default, Me, and each party or raid member with where they are. A typed name still works.

## When a customer joins

The owner, 12 Nov 2026: "when they join basically it knows why i invited them and tells them who
and what". The invite remembers the request that caused it, so the welcome on joining says what
they're getting, who does it, where to go, the price (or free), and who to pay, by the payee rules
above. When you are the one doing it, it speaks in the first person.

Prototype output, 12 Nov 2026 (you in Orgrimmar, the warlock in Thunder Bluff):
`Hi Kaldrok! Grimtotem will summon you to TB. 25s. Pay Grimtotem when you land.` With you in TB as
well, the last sentence becomes `Pay me when you land.` A free service: `Hi Kaldrok! I do
lockpicking, come to me in TB. Free, tips welcome.`

## When a customer arrives

The owner, 12 Nov 2026: "when people land after we summon them to me i would also want to say what
else we offer in the area".

On arrival the group says what else is on offer **in the zone where the customer landed**, leaving
out what they came for. Only providers standing in that zone count, so a mage in Orgrimmar is not
offered to someone who just landed in Thunder Bluff. Paid services show their price; free ones say
free. Nothing else on offer there means no message. (1.6.0 already posts ticked extras on arrival,
but whether or not anyone who does them is there.)

Prototype output, 12 Nov 2026, summoned to Thunder Bluff with a rogue and a priest there and the
mage in Orgrimmar: `Welcome to TB, Kaldrok! Also here: free lockpicking, free healthstones, free
Fortitude. Just ask!`

## Advertising

The game lets an addon or a macro post in Trade, General, Say or Yell only from a key press, so an
ad always needs one press. The addon writes the ad from who is in the group and what is offered
(`{wts}{services} | whisper inv`), lights a keybound button when the per-channel wait is over, turns
it off when nothing can be sold, and invites a whispered "inv" as an answer to the ad. A mage never
advertises a portal to the city he is standing in (caught by the prototype).

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

By class, because a provider is a person of a class: **General**, **Warlock**, **Mage**, **Rogue**,
**Buffs** (free unless priced). Each class tab lists who in the group can do it and where they are.

General holds inviting *and* payment together. The owner: "payment and inviting can be in one tab
because there are downstream impacts from both": what someone asked for sets the {service},
{price} and {payee} in the welcome they get on joining.

## Build order

Each slice ships on its own and keeps every earlier test passing.

1. Services: the per-service settings (offer, price/free, invite, buyers say), the tabbed window,
   the payee rules (default plus per-service override) and {payee}. Summons behave as in 1.6.0.
2. Mage, rogue and warlock services: portals (spellbook for you, faction and level for a friend),
   food & water, lockpicking, stones; matching tested against real request lines.
3. Providers: services follow who is in the group; summons go to the warlock's zone; the arrival
   message lists what is on offer where they landed.
4. Advertising: the ad built from the group, the keybound button, per-channel wait, answers to the ad.
