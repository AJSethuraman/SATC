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

## Preview on every tab

The owner, 12 Nov 2026: "i should be able to press debug buttons in each panel for things like
seeing what the message should look like and stuff". Each setup tab has **Preview this tab**
(also `/si preview warlock`, etc.). It prints, in your own chat window only, every line that tab's
settings would make for a pretend buyer: the invite line, the welcome, the summon alert and
whisper, the arrival offer, who gets paid, the ad and when it can go. It runs the same code that
sends the real messages, so what it shows is what goes out; it sends nothing, invites nobody and
queues nothing. When nobody in the group can do a service it says so, and shows an example with a
level 60 stand-in of that class standing with you.

## Raid icons stay in chat, not over heads

On 12 Nov 2026 the game put up "ServiceInviter has been blocked from an action only available to
the Blizzard UI". The cause was 2.0.8 putting raid icons over heads from a timer: `SetRaidTarget`
has been protected since patch 12.0 (warcraft.wiki.gg/wiki/API:SetRaidTarget), and Forever runs on
those addon rules. 2.0.11 no longer calls it; `{rt1}` icons in party and raid chat are text and
still work. The addon now listens for the game blocking any of its calls, names the call in your
chat, and never makes it again that session. `InitiateTrade` (auto-trade on arrival) is listed as
callable only by Blizzard's code on the current game (warcraft.wiki.gg/wiki/API_InitiateTrade);
if Forever blocks it, auto-trade stops for the session and the addon says so.

## Rows follow the service; Paid finishes the job (2.0.13)

The design review of 12 Nov 2026 (a separate session that read the code and made mockups)
found the customer rows only knew summons. Reproduced: as the warlock, a rogue friend's
lockpicking buyer put "Summon Kaldrok" on the big button, and a portal or lockpick customer
could never be marked Paid. Now:

- Summon customers: Summon, Summoning, Arrived, as before.
- Everyone else (portals, lockpicking, water, stones, buffs): In group, then **Paid**, or
  **Done** when the service is free. The welcome in party or raid chat already tells the
  provider (the review's G1 was mostly wrong on that).
- The big button only offers what you can do: a summon to where you stand, as the warlock;
  the arrival offer; a trade when you collect. Never someone else's customer.
- Paid shows for every customer once they're served, whoever collects. Pressing it (the owner:
  "Paid should also remove from party and maybe send a thank you") whispers "Thanks {name}!
  Enjoy." (editable, General tab) and removes them from the group if you're the leader (or an
  assistant in a raid); otherwise it says to ask the leader. A trade that pays thanks them too,
  but removal waits for your click (x), since removing someone without a click risks the game's
  block popup.
- Invites keep working when you're not the leader: the game turns them into a suggestion.

Not built, on the owner's agreement: the "Tell Mireth" button (the welcome already is that
message), filter chips and the "nobody can do this" strip. Addon-to-addon messages (so several
people running it share one customer list and say what they really know) wait until a second
person runs it.

## The look (2.1.0)

From the design review of 12 Nov 2026 (mockups for the owner, who liked them): dark and gold,
flat, one filled gold button per window.

- **Customers:** header with Post ad and Setup; "Your next job" with the one gold button, what it
  is and how long they've waited; rows with a class-colour bar, the service, who does it and
  where, a status pill (always with the word) and its age, and the row's action. Someone else's
  job says who is up instead of offering a button. The window is as tall as the customers it
  shows; the footer holds the session and, for classes with buffs, the buff button.
- **Setup:** a side menu instead of tab buttons hanging under the frame, the page name as a
  header, Save as the gold button. Same fixed 1068 x 690 window, shrunk to fit small screens.
- **Banner:** a small label naming the event, CLICK THE PORTAL, then "Summoning Kaldrok to
  Thunder Bluff. Pay Grimtotem." and a bar counting down the 14 seconds. It pulses for two
  seconds, then holds.

Every secure button keeps its macro; nothing is moved or resized in combat. Built on the game's
own fonts at set sizes and plain colour textures.

Lua 5.1 allows 200 local names at the top of a file, and over that the addon does not load at
all. This round hit it; a test now keeps 10 spare.

## 3.x: a small team, summons and blessings only (14 Nov 2026)

The owner: *"i want to give it to 3-4 of us, maybe 5. we are only summoning and sometimes doing
a blessing but not much else. i want to have all of the bells and whistles and analytics but we
share our info and the addons talk"*, and *"i think we should keep most of stuff to whispers aside
from like frequent flyer announcements. but this allows us to do our dynamic pricing"*.

Decided with the owner:

- **Summons and blessings only.** Portals, lockpicking, water, healthstones, soulstones and the
  other classes' buffs are removed, not hidden (3.0.0).
- **First to hear claims it.** Every copy hears a buyer in Trade; the first to claim invites, the
  others stand down, so nobody gets two invites.
- **A team name plus a member list.** Addons can't open a private channel on their own, so the
  copies message each other directly (addon whispers) and over party/raid when grouped. Copies with
  the same team name share whenever they're online, grouped or not.
- **One shared book.** Customers, regulars, Paid/Scam, the didn't-pay list, near misses, other
  sellers' prices and shard counts are the team's. Each record carries who logged it and when, so a
  record synced twice counts once; a copy that logs in catches up from the others.
- **Anyone on the team** can put someone on the didn't-pay list or take them off.
- **Customers hear from us by whisper** (the welcome, the summon notice, the price), so each
  customer sees their own price; only the regulars line ("frequent flyer") and the didn't-pay
  call-out go to party/raid chat. A silenced character can't whisper strangers, so the whisper
  goes from whoever claimed the customer.

Stages: 3.0 focus · 3.1 team link + claims · 3.2 shared records + catch-up · 3.3 whispers to
customers · 3.4 shared prices and shards.

### 3.1 as built (14 Nov 2026)

- **Point of contact.** `/si team poc NAME, BACKUP` (or the Team tab). Every other copy hands a
  matched buyer and their quote to the first one online (`BUY` over the group's addon channel, or
  an addon whisper to a teammate online but not grouped). The point of contact invites, and is the
  only copy that sends customer or group messages. Nobody online on the list = each copy solo.
  Two teammates handing the same buyer = one invite.
- **Presence.** Copies say `HI` (version, warlock or not, zone) on login, roster and zone changes,
  and every minute. A teammate's own zone wins over the game's guess. A copy that isn't on the team
  gets one chat line ("/si team add NAME"); nothing it sends is acted on.
- **Each channel is its own market.** A seller counts in the exact channel they posted in ("Trade -
  English 50" never sees "Trade - English 4"), for the city they named, for 5 minutes, cheapest
  first. The service price is the max; the min (floor) is never crossed; Undercut by N, Match, or
  Ignore. A buyer is quoted their channel's price at that moment, and keeps it; the ad in each
  channel carries that channel's price.
- **Where each message goes.** Whisper / party-raid / off per message (welcome, summon notice,
  arrival, thanks, regulars line, call-out). Team default: whispers, except the regulars line and
  the call-out; solo default: as before. Only choices that differ from the default are stored.
- **Test mode across copies.** A copy in test mode hands its buyers to the point of contact marked
  as a test; the point of contact's copy invites nobody and whispers the exact customer messages to
  the test target (or to the teammate who found the buyer).

## 3.3: the guild is the team, and the books are shared (14 Nov 2026)

The owner: *"i want as much to work through guild as possible - like the idea of this being a
'community' addon. so auto detect and stuff should work from guild and understand if guild is in
party it is not a customer"*.

- **"My guild is the team"** (Team tab, on by default). Anyone in your guild is never a customer,
  addon or not (read from the guild roster). Guildmates running the addon are on the team on any
  character, with nothing typed; the team box is now only for people outside the guild.
- **Team messages go over the guild's hidden addon line** as well as the raid's, so a teammate in
  another city gets hand-offs too. The same message arriving twice is heard once.
- **Each copy owns its own book** (customers, didn't pay, stats) and only the owner changes it.
  Every change counts up `bookrev`. Each hello carries that number; a teammate holding less sends
  `WANT`, and the owner answers with what changed since, a line every 0.25s (the game drops faster
  bursts), then `END`. The receiver only marks itself caught up at `END`, so a cut-off answer is
  simply asked for again. Teammates' books are kept in `teambooks`, so their customers count while
  they are offline.
- **Lists and stats add the books up** (`Jobs.Book`, `Jobs.Analytics`). To keep one summon from
  being counted twice, only the point of contact records a visit when one is online; with none, a
  "joined your group" row isn't recorded when a teammate is in the group.
- **Didn't pay is shared both ways.** "Paid after all" no longer deletes: it marks the entry
  cleared, and a name is on the list when its latest "didn't pay", in anyone's book, is newer than
  its latest clear. So any copy can clear anyone's entry.
- Not tested in game: the guild addon line and the roster on Forever.

## 3.4: the owner's flow (14 Nov 2026)

*"1 and 2 monitor trade, general, summons. 2 is POC, he whispers them including their price and
the service so they know upfront what it is and they will be summoned soon. they come in party,
they are welcomed if a regular. we start to summon and they are told a summon is on the way. upon
arrival they are whispered to pay the price again to payee and that they can request a blessing.
either of us can mark someone as a scammer - like the queue knows."* `tests/test_flow.py` walks it.

- When the welcome goes by whisper, it goes **with the invite**, not on joining. On joining, only
  a regular hears the regulars line. In party/raid chat the welcome still waits for them to join.
- **Arrival** names who to pay and how much (`MSG.PAY`, `paymsg`), then what else is on offer
  there. Nothing is said about paying once they've paid or when it's free.
- **Didn't pay** reaches the team at once (the mark says hello, teammates ask for the change), and
  a teammate's copy flips that customer's row to Didn't pay.

## 3.5: the 2026 redesign (14 Nov 2026)

From a designer's handoff, reviewed against the code first (the review is kept with the handoff;
its verdicts are what was built). Dark, flat, one gold accent; the game's fonts and spell icons,
nothing shipped.

- **Customer window:** fixed 600 x 614, never resized, so nothing moves in a fight. A cast strip
  with the next step as a verb (INVITE / SUMMON / OFFER / TRADE + who; a helper sees NEXT UP, not
  a button) and, for a paladin, the blessing button. Six fixed rows (no scrolling: each row's
  buttons are secure macros that can't be rebound in combat), each with a status bar and pill for
  all twelve statuses, one meta line (» city · who), the regular's count, two action slots and x.
  "+N more not shown" when there are more.
- **Setup:** 960 x 780, a rail, two columns of rows. Toggles for on/off, segments for a pick-one
  (Paid: Doer / Me / Name; on a service Default / Doer / Me or a typed name; I summon / Friend
  summons; Ignore / Match / Undercut; the team's Whisper / Party / Off matrix), chips that insert a
  {token}, placeholders that say what blank means. Count shards stays one setting. Running,
  Selling and Test mode on Tools run their /si commands. The arrival pay reminder has a box.
- **Pop-ups:** the banner reads SUMMONING / CLICK PORTAL / who » where · pay whom, with a TEST chip;
  the blessing pop-up is a 224 x 68 card; Lists opens one copy window with the eight lists as tabs.

## 3.5.1: one price list for the team (14 Nov 2026)

The owner: *"they will have the min/max price and then the individual workers would price
dynamically price based on their chats right"*. The point of contact's max, min, and how to meet a
cheaper rival (ignore / match / undercut by N) go out with each hello (`PRICE`). While they're
online, every copy prices with those rules (`Core.PriceOverride` in `C.Setting`), from the rivals
it sees in its own channels, and hands the buyer over with that quote. When the point of contact
goes offline, each copy's own prices come back. Only the point of contact's `PRICE` is heard.

## 3.6: no fixed text (14 Nov 2026)

The owner: *"i dont want to communicate fixed text - not okay"*. Every message a customer or the
group gets comes from a box in setup, and each box shows the text it sends (no "Auto"):

- **Welcome** `Hi {name}! {who} will summon you to {dest}. {price}. Pay {payee} when you land.`
  ({who} is the warlock, or "I"; {dest} the short city name). Used when we know what they came for.
- **Not sure what they want** `Hi {name}! We have {services}. What can we do for you?` Invited by
  hand, by someone else, or said nothing we could read.
- **Arrival** `Also here: {offers}. Just ask!`, after the **Pay reminder**.
- **Regular** `Welcome back {name}, {visits} time with us!` The addon no longer puts "Hi X!" in
  front of it: a line with {name} replaces the welcome's hello; one without goes after the hello.

`tests/test_no_fixed_text.py` sets every box to a marker, runs a customer through every step, and
fails on anything sent that didn't come from a box.

## 3.7: a Messages tab (14 Nov 2026)

The owner: *"getting too cramped - it's annoying to have short text boxes"*, *"make a tab that can
be used for the chats only so it's all in one spot and it's obvious like Send on invite, Send on
entry, Send on arrival etc"*, *"build the team part to be... teams"*.

- **Messages** (second tab): every message in the order a customer meets them (Send on invite,
  on entry, when summoning, on arrival, when done), each a full-width box with Whisper / Party /
  Off beside it. Off is the message's on/off (it also sets the old welcome / thanks / raid-line
  flags). An empty Pay reminder or "What else is here" says nothing.
- **Team** is only the team: the guild, ours outside it, the point of contact, who's online.
- **General** keeps inviting, paying and where the addon's own lines go ("Who I invited, and why").
- Dropped: "WTB only" (LF / need / looking always count) and "Merge split messages" (always on).

## 3.8: Send my setup; the regulars line as a raid warning (14 Nov 2026)

- **Send my setup** (Team tab): messages and where each goes, channels, the ad, re-invite wait,
  auto-invite words, prices, blessing words and spell, who gets paid, the team list and the point
  of contact, as `SET path n/N value` lines through the outbox, then `SETEND count`. The receiver
  asks "X sent their setup. Use it?" (or uses it without asking, if set); a setup that arrives
  with a piece missing is not used. Not sent: warlock or not, test mode, selling, running, keys,
  debug, the helper you whisper. The sender joins the receiver's team.
- The owner: *"a regular and a scammer should be raid warned or whatever by POC"*. The regulars
  line, when it goes to the group, goes as a raid warning when the point of contact is leader or
  assist, like the didn't-pay call-out.

## 3.9: the ad goes everywhere you listen (15 Nov 2026)

The owner: *"this needs to post to anything we watch, or have the option to. like maybe not
general sometimes"*. The ad's channels are every channel you're in that you listen to (Trade,
General, your other channels), each on its own: Trade - English 50 and Trade - English 4 are two
(before, only the first Trade channel ever got it). The Advertise tab shows a switch per channel;
a switched-off channel is remembered by name (`adskip`). Each press posts in the next channel
whose wait is over. An old "General off" from before 3.9 still holds.

## 3.9.5: less traffic, and nothing lost (15 Nov 2026)

The owner: *"it still doesnt seem to be transmitting the list very well"*, *"the trade spam is
straight up not working, it says we are rate limited"*, and *"it is not actually inviting them but
the addon says it is in the queue"*.

- **Customers go several to a line** (`CB`), so a 310-customer book is about 95 lines, sent one a
  second, and posting an ad pauses them for a few seconds. The game limits how much a character
  sends in all; the book was crowding out the ads.
- **Numbered lines.** END says how many; a receiver with a gap asks again from the gap (WANT since
  the change before it) and keeps what arrived. A re-ask covered by the send already going out is
  dropped, so a book never goes out twice over.
- **A hand invite from a teammate is invited by the point of contact too**: a muted character's
  invite to a stranger doesn't go through, and the addon only sees that it was asked for.

## 3.9.8: muted, and not making the throttle worse (15 Nov 2026)

The owner: *"if i type on my own, it says i am muted, if i use the addon to try and post it blanks
twice, third time it just says rate limited after which i type immediately and it is still saying
rate limited not muted"*.

- **Muted turns ads off** until you log in again, said once; the button reads "Muted". The game's
  "rate limited" is its throttle on repeated tries, and it hides the "muted" line while it lasts.
- **Slowed down by the game: no ad for a minute**, since each press only extends it.
- **A gap in a teammate's book is asked for at their next hello**, not straight away, and after
  three broken sends not again this session. Asking at once added traffic exactly when the game was
  already dropping lines.
- **Background lines stay under 40 a minute**, and `/si stop` drops what was queued. `/si teamlog`
  says how many team messages your copy sent in the last minute.

## 3.9.9: the ad is a macro (15 Nov 2026)

The owner: *"the trade thing is still happening - what gets me is a regular macro can do this"*.
The ad buttons (main window, Setup, the bound key) are now macro buttons: a press runs
`/<channel> <ad>`, the same thing a macro typed by hand does, instead of the addon's own
`SendChatMessage`, which the game kept dropping. Just before the press goes through, the addon
fills in the next channel that's ready. In combat the macro can't change, so it posts what was
ready when the fight started. `/si ad` typed in chat still uses the old call.

## 3.9.10: the macro press, and a suspended chat (15 Nov 2026)

The owner's screenshot: *"We have temporarily suspended your chat and mail privileges"*, and *"if it
works like a macro does why do i not get something saying i'm muted like this"*. No line meant the
macro never ran: the ad buttons listened to only the down half of a press, and the game runs a
macro on down or up by the "cast on key down" setting. They now listen to both and act on the half
the game uses, so one press is one ad. That suspension line also turns ads off.

## 3.9.11: try the ad in guild (15 Nov 2026)

The owner: *"ok prove this works by letting me post it in guild"*. Advertise has "Post to guild
instead, to try it": every press runs `/g <ad>` through the same macro button, with no wait and no
ad counted, and when the line comes back in guild chat the addon says so in green.

## 3.9.12: the SI Ad macro (15 Nov 2026)

The owner, of the macro button: *"yeah nothing it is not working"* (no line at all, not even the
suspension notice, so the button never sent anything). Earlier: *"a regular macro can do this"*.
"Make SI Ad macro" (Advertise, or `/si macro`) makes a real per-character macro called SI Ad and,
out of combat, keeps it filled with `/<channel> <ad>` for the next channel that's ready. It counts
when your line shows up in the channel, and then moves on to the next. With debug on, the ad
buttons now print each half of a press and what they handed the game, to find out why they don't.

## 3.9.13: where a quote came from (15 Nov 2026)

The owner: *"we had dynamic pricing put us at 35 but it still seemed to say 45 to people but it's
hard to tell where they are coming from - could be like trade 2 or 40"*. Prices are per channel, so
the same city can be 35 in one Trade and 45 in another. Every invite, hand-off and near miss now
names the full channel ("Trade - English 40", not "Trade") and says why the price is what it is:
the rival, how long ago, the rule, or that it's your max and why (no seller seen there, no min, rule
off), or held at your min. A buyer handed over by a teammate says it was priced by their copy.
`/si why NAME` repeats the quote.

## 3.9.14: whoever left goes to the bottom (15 Nov 2026)

The owner: *"when people leave put them at the bottom of the queue so the top is a working
queue"*. The main window lists everyone in progress first (oldest first), then the finished ones,
then whoever left (still there while they owe, so Scam stays a click away). With more than six,
the ones that don't fit come off the bottom, so a leaver is hidden before anyone waiting.

## 3.9.15: colors in the SI lines (15 Nov 2026)

The owner: *"can you color code the SI log tab ... much easier to tell if i know which chat it came
from quickly"*. Every channel name is a colored tag, `[Trade - English 40]`, its color handed out in
the order channels are first seen, so the first eight are all different. The price is colored by
what set it: green moved for a rival, white your max, orange held at your min, red channel unknown.
Teammates' names are light blue. No channel gets red or green, which mean wrong and working.

## 3.9.16: invite words are for whispers only (15 Nov 2026)

The owner, of "invited Necrotic Paladin keyword 'inv' [Trade (Services) - English 50]": *"ok no
auto invite is meant to be via whispers only"*. The word list (General, now "Whisper words")
invites only from a whisper; in a public channel "inv" never does, whatever the old Auto-invite
switch said. That switch is gone. A buyer's message in a channel ("wtb summon tb") still invites as
before.

## 3.9.17: the macro follows the price (15 Nov 2026)

The owner: *"the macro does not seem to be updating with the dynamic pricing though the whispers
are"*. The rewrite called `EditMacro(index, nil, nil, body)`; a client that wants the name and icon
back refuses that, and the refusal was remembered as done, so the macro kept its first price. It
now passes the macro's own name and icon, reads the macro back to check, and tries again the next
second if it didn't take (saying so once, in red). Debug prints each new macro text.

## 3.9.18: nothing switches the ad off by itself (15 Nov 2026)

The owner: *"stop killing it after 2 attempts - impossible to troubleshoot"*, and *"actually the
macro just doesnt seem to work at all though it did before"*.

- An ad that doesn't show up is reported every time, with how many in a row and what the game
  said; the channel stays in the queue. The queue line shows "last N didn't show up".
- Muted, suspended or slowed down is said (at most every 10 seconds) and never turns ads off or
  holds them.
- The macro "worked before" because its updates were failing (3.9.17), so it kept its first ad
  and every press posted it, wait or no wait. Now it empties between posts, so between posts it
  runs `/run ServiceInviter_AdWhy()`, which says which channel is next and in how long.
- Wait on the Advertise tab takes minutes under one (0.5 = 30 seconds); 0 means every press posts.

## 3.9.19: the quote holds everywhere; ads that did post are seen (15 Nov 2026)

The owner: *"the intention was for someone to be told their quoted price at all points"*, and a
screenshot of "Your ad didn't show up in [Guild] ... The game said: Trukt Hunt has joined the raid
group." with the ad in guild chat.

- **GOT carries the quote** (service, city, price): every teammate's copy holds the customer to the
  price the inviter told them, so the warlock's trade check and window match the whisper. Someone
  who joined with no quote keeps the first price worked out for them.
- **Your own line is matched without the "|"**: the game sends the ad's "|" back as "||", so the
  exact match failed and real posts were reported as missing, in guild and in Trade.
- **Only chat-related game lines count as the reason** an ad failed, not raid joins.

## 3.9.20: the ad buttons run the SI Ad macro (15 Nov 2026)

The owner: *"but it didnt show in guild chat at all?"*. The buttons' own macro text never runs on
their client; the SI Ad macro does. With an SI Ad macro made, every ad button (main window, Setup,
the bound key) runs that macro (secure attribute `macro`, not `macrotext`), refreshed just before
the press; its line showing up does the counting, as when you press the macro yourself. Without
one, the buttons work as before.
