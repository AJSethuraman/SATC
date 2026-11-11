"""Discord bot: roster lookups and raid signups."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import tasks

from . import raids as R
from . import craft as C
from .links import item_link
from .config import Config
from .db import Database, utcnow
from .sync import sync_guild, sync_item_catalog, sync_recipe_catalog

log = logging.getLogger("guildbot")

BUTTONS = [
    ("tank", "Tank", discord.ButtonStyle.primary),
    ("healer", "Healer", discord.ButtonStyle.success),
    ("dps", "DPS", discord.ButtonStyle.danger),
    ("tentative", "Tentative", discord.ButtonStyle.secondary),
    ("absent", "Can't make it", discord.ButtonStyle.secondary),
]


def rel(iso: str | None) -> str:
    """Discord relative timestamp ('3 hours ago') for an ISO time, or 'never'."""
    if not iso:
        return "never"
    return f"<t:{int(datetime.fromisoformat(iso).timestamp())}:R>"


def data_as_of(rows, fallback: str | None, key: str = "fetched_at") -> str:
    """Footer for lists built from per-row fetch times: the oldest row shown, so stale data is not
    presented as fresh just because a later sync ran."""
    times = [r[key] for r in rows if r[key]]
    return f"Data as of {min(times) if times else (fallback or 'never')} UTC (oldest shown)"


def who_footer(char, profs, gear) -> str:
    """Date each part of /who separately: they are fetched separately and can be different ages."""
    def oldest(rows):
        times = [x["fetched_at"] for x in rows if x["fetched_at"]]
        return min(times) if times else "never"
    return (f"Profile {char['profile_at'] or 'never'} · professions {oldest(profs)} · "
            f"gear {oldest(gear)} (UTC)")


def chunk_lines(lines: list[str], limit: int) -> list[list[str]]:
    """Split lines into groups whose joined length stays under `limit` (one embed field each)."""
    out, cur, used = [], [], 0
    for line in lines:
        if cur and used + len(line) + 1 > limit:
            out.append(cur)
            cur, used = [], 0
        cur.append(line)
        used += len(line) + 1
    if cur:
        out.append(cur)
    return out


def clip(lines: list[str], limit: int) -> str:
    out, used = [], 0
    for i, line in enumerate(lines):
        if used + len(line) + 1 > limit - 20:
            out.append(f"… and {len(lines) - i} more")
            break
        out.append(line)
        used += len(line) + 1
    return "\n".join(out)


def raid_embed(db: Database, raid) -> discord.Embed:
    g = R.group_signups(db.signups(raid["id"]))
    ts = int(datetime.fromisoformat(raid["starts_at"]).timestamp())
    cancelled = raid["status"] == "cancelled"
    started = raid["status"] == "closed"
    ended = raid["status"] == "ended"
    e = discord.Embed(
        title=f"{'CANCELLED: ' if cancelled else 'STARTED: ' if started else 'COMPLETED: ' if ended else ''}"
              f"{raid['title']}  (#{raid['id']})",
        description=f"<t:{ts}:F> · <t:{ts}:R>\nSlots filled: **{R.filled(g)}/{raid['size']}**",
        color=discord.Color.dark_grey() if cancelled or started or ended else discord.Color.blurple(),
    )
    for role in R.ROLES:
        lines = [R.format_entry(s) + (f" (wants {R.ROLE_SINGULAR[s['wanted']]})" if role == "bench" and s["wanted"] else "")
                 for s in g[role]]
        cap = R.caps_of(raid).get(role)
        e.add_field(name=f"{R.ROLE_LABEL[role]} ({len(lines)}{'/' + str(cap) if cap else ''})",
                    value=clip(lines, 1024) or "—", inline=role in ("tank", "healer", "dps"))
    times = [x["profile_at"] for rows in g.values() for x in rows if x["profile_at"]]
    e.set_footer(text=f"Character data as of {min(times)} UTC (oldest shown)" if times
                 else "No linked characters shown")
    return e


class RaidView(discord.ui.View):
    """Signup buttons. timeout=None + fixed custom_ids keep them working after a restart."""

    def __init__(self, bot: "GuildBot", raid_id: int):
        super().__init__(timeout=None)
        self.bot, self.raid_id = bot, raid_id
        for role, label, style in BUTTONS:
            b = discord.ui.Button(label=label, style=style, custom_id=f"raid:{raid_id}:{role}")
            b.callback = self._make_callback(role)
            self.add_item(b)

    def _make_callback(self, role: str):
        async def callback(interaction: discord.Interaction):
            await self.bot.handle_signup(interaction, self.raid_id, role)
        return callback


CLAIM_PAGE = 25   # Discord allows 25 options in one dropdown


def char_label(r) -> str:
    return f"{R.full_name(r)} · L{r['level'] or '?'} {r['class_name'] or ''}".strip()[:100]


class ClaimPicker(discord.ui.View):
    """Private (ephemeral) dropdown of unclaimed characters, paged 25 at a time."""

    def __init__(self, bot: "GuildBot", page: int = 0, query: str = ""):
        super().__init__(timeout=300)
        self.bot, self.query = bot, query
        rows = bot.db.unclaimed_characters(query)
        pages = max(1, -(-len(rows) // CLAIM_PAGE))
        self.page = min(page, pages - 1)
        self._pages = pages
        chunk = rows[self.page * CLAIM_PAGE:(self.page + 1) * CLAIM_PAGE]
        if chunk:
            sel = discord.ui.Select(
                placeholder=f"Pick your character(s)  ·  page {self.page + 1} of {pages}",
                min_values=1, max_values=min(len(chunk), bot.db.MAX_CLAIMS),
                options=[discord.SelectOption(label=char_label(r), value=r["slug"]) for r in chunk])
            sel.callback = self._picked
            self.add_item(sel)
        if pages > 1:
            nxt = discord.ui.Button(label="Next page", style=discord.ButtonStyle.secondary)
            nxt.callback = self._next
            self.add_item(nxt)
        find = discord.ui.Button(label="Search by name", style=discord.ButtonStyle.primary)
        find.callback = self._search
        self.add_item(find)
        if query:
            allb = discord.ui.Button(label="Show everyone", style=discord.ButtonStyle.secondary)
            allb.callback = self._show_all
            self.add_item(allb)

    async def _next(self, interaction: discord.Interaction) -> None:
        view = ClaimPicker(self.bot, (self.page + 1) % self._pages, self.query)
        await interaction.response.edit_message(content=view.header(), view=view)

    async def _search(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ClaimSearch(self.bot))

    async def _show_all(self, interaction: discord.Interaction) -> None:
        view = ClaimPicker(self.bot)
        await interaction.response.edit_message(content=view.header(), view=view)

    def header(self) -> str:
        n = len(self.bot.db.unclaimed_characters(self.query))
        if self.query:
            return (f"{n} match(es) for \"{self.query}\". Pick yours." if n
                    else f"No unclaimed character matches \"{self.query}\". Try less of the name, or tap Show everyone.")
        return (f"Pick yours from the list ({n} unclaimed)." if n
                else "Every character is already claimed. Ask an officer if one is wrong.")

    async def _picked(self, interaction: discord.Interaction) -> None:
        res = self.bot.db.claim(interaction.user.id, interaction.data["values"])
        names = {r["slug"]: R.full_name(r) for r in self.bot.db.roster()}
        parts = []
        if res["linked"]:
            parts.append("Linked: " + ", ".join(f"**{names[s]}**" for s in res["linked"]) + ". Now tap your role again.")
        if res["taken"]:
            parts.append("Already claimed by someone else: " + ", ".join(names[s] for s in res["taken"])
                         + ". Ask an officer if that is wrong.")
        if res["over_cap"]:
            parts.append(f"You can claim up to {self.bot.db.MAX_CLAIMS} characters; ask an officer for more.")
        log.info("claim by %s: %s", interaction.user.id, res)
        await interaction.response.edit_message(content=" ".join(parts) or "Nothing changed.", view=None)


class ClaimSearch(discord.ui.Modal, title="Find your character"):
    text = discord.ui.TextInput(label="Part of your character's name", min_length=1, max_length=40)

    def __init__(self, bot: "GuildBot"):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        view = ClaimPicker(self.bot, 0, str(self.text.value).strip())
        await interaction.response.edit_message(content=view.header(), view=view)


class ClaimPanel(discord.ui.View):
    """The public 'claim your characters' button. Persistent across restarts."""

    def __init__(self, bot: "GuildBot"):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Claim my characters", style=discord.ButtonStyle.primary, custom_id="claim:open")
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view = ClaimPicker(self.bot)
        await interaction.response.send_message(view.header(), view=view, ephemeral=True)


class RaidDetails(discord.ui.Modal, title="Raid details"):
    name = discord.ui.TextInput(label="Name", default="Raid", min_length=1, max_length=100)
    tanks = discord.ui.TextInput(label="Max tanks (blank = no limit)", required=False, max_length=2)
    healers = discord.ui.TextInput(label="Max healers (blank = no limit)", required=False, max_length=2)
    dps = discord.ui.TextInput(label="Max DPS (blank = no limit)", required=False, max_length=2)

    def __init__(self, bot: "GuildBot", day: str, time: str, size: int, origin=None):
        super().__init__()
        self.bot, self.day, self.time, self.size, self.origin = bot, day, time, size, origin

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            caps = {"tank": R.parse_cap(self.tanks.value), "healer": R.parse_cap(self.healers.value),
                    "dps": R.parse_cap(self.dps.value)}
        except ValueError:
            await interaction.response.send_message("Limits must be whole numbers from 1 to 40 (or blank).", ephemeral=True)
            return
        start = R.parse_start(self.day, self.time, self.bot.cfg.timezone)
        posted = await self.bot.post_raid(interaction, str(self.name.value).strip(), start, self.size, caps)
        if posted and self.origin is not None:
            try:
                await self.origin.delete_original_response()      # the private menu has done its job
            except discord.HTTPException:
                pass


class RaidWizard(discord.ui.View):
    """Step-by-step raid creation: pick the day, the time and the size, then name it.
    The day list shows 14 days at a time; Earlier/Later move it, so any date is reachable."""

    def __init__(self, bot: "GuildBot", page: int = 0, day=None, time=None, size=None, origin=None):
        super().__init__(timeout=900)
        self.bot, self.page, self.day, self.time, self.size = bot, page, day, time, size
        self.origin = origin          # the /raid-create interaction that opened this menu
        days = R.day_options(datetime.now(timezone.utc), bot.cfg.timezone, page=page)
        first, last = days[0][0].split(" - ")[1], days[-1][0].split(" - ")[1]
        self._add_select("day", f"1. Day  ({first} to {last})", days, 0)
        self._add_select("time", "2. Time (" + bot.cfg.timezone.split("/")[-1].replace("_", " ") + ")",
                         R.time_options(), 1)
        self._add_select("size", "3. How many players", [(f"{n} players", str(n)) for n in R.SIZE_CHOICES], 2)
        if page > 0:
            earlier = discord.ui.Button(label="< Earlier days", style=discord.ButtonStyle.secondary, row=3)
            earlier.callback = lambda i: self._turn(i, -1)
            self.add_item(earlier)
        later = discord.ui.Button(label="Later days >", style=discord.ButtonStyle.secondary, row=3)
        later.callback = lambda i: self._turn(i, 1)
        self.add_item(later)
        nxt = discord.ui.Button(label="Next: name and limits", style=discord.ButtonStyle.success, row=3)
        nxt.callback = self._next
        self.add_item(nxt)

    def _add_select(self, attr: str, placeholder: str, options, row: int) -> None:
        current = getattr(self, attr)
        sel = discord.ui.Select(
            placeholder=placeholder, row=row,
            options=[discord.SelectOption(label=l, value=v, default=(str(current) == v)) for l, v in options])

        async def picked(interaction: discord.Interaction, sel=sel, attr=attr) -> None:
            value = sel.values[0]
            setattr(self, attr, int(value) if attr == "size" else value)
            for o in sel.options:
                o.default = o.value == value
            await interaction.response.edit_message(view=self)
        sel.callback = picked
        self.add_item(sel)

    async def _turn(self, interaction: discord.Interaction, step: int) -> None:
        view = RaidWizard(self.bot, max(0, self.page + step), self.day, self.time, self.size, self.origin)
        await interaction.response.edit_message(view=view)

    async def _next(self, interaction: discord.Interaction) -> None:
        if not (self.day and self.time and self.size):
            await interaction.response.send_message("Pick the day, the time and the size first.", ephemeral=True)
            return
        start = R.parse_start(self.day, self.time, self.bot.cfg.timezone)
        if start <= datetime.now(timezone.utc):
            await interaction.response.send_message("That time has already passed. Pick a later time.", ephemeral=True)
            return
        await interaction.response.send_modal(RaidDetails(self.bot, self.day, self.time, self.size, self.origin))


def craftable_result(db: Database, kind, sub, slot, lo, hi, profession, show_all):
    """(embed, None) with the results, or (None, message) when there is nothing to show."""
    if not db.item_facets("item_class", limit=1):
        return None, "I'm still looking up what recipes make (the first run takes a few minutes). Try again shortly."
    rows = db.craftable(kind, sub, slot, lo, hi, profession, only_known=not show_all, limit=400)
    if not rows:
        return None, ("Nobody in the guild can craft anything that matches. Loosen a filter"
                      + (", or turn on 'show items nobody can make yet'." if not show_all else "."))
    lines = []
    for r in rows:
        tags = ", ".join(x for x in (r["item_subclass"], r["inventory_type"]) if x)
        lvl = "any level" if not r["required_level"] else f"L{r['required_level']}"
        lines.append(f"{item_link(r['name'])} ({lvl}, {tags or r['item_class'] or 'item'}): "
                     f"**{r['profession']}** - {r['knowers'] or 'nobody yet'}")
    filt = ", ".join(f"{k}: {v}" for k, v in (("kind", kind), ("type", sub), ("slot", slot), ("from level", lo),
                     ("to level", hi), ("profession", profession)) if v is not None)
    e = discord.Embed(title=f"Craftable by the guild ({len(rows)})" if not show_all else f"All craftable ({len(rows)})",
                      description=(f"*{filt}*\n" if filt else "") + clip(lines, 4000))
    e.set_footer(text="Items from Blizzard's data, not only what is learnable in game yet. "
                      f"Known recipes as of {db.get_meta('last_sync_at') or 'never'} UTC.")
    return e, None


class CraftWizard(discord.ui.View):
    """Guided search: pick the kind, type, slot and level, then show who can make it. Private to the asker."""

    def __init__(self, bot: "GuildBot", kind=None, sub=None, slot=None, band=None, show_all=False):
        super().__init__(timeout=900)
        self.bot, self.kind, self.sub, self.slot, self.band, self.show_all = bot, kind, sub, slot, band, show_all
        db = bot.db
        any_opt = [("Any", C.ANY)]
        kinds = [(r["name"], r["name"]) for r in db.item_facets("item_class")]
        subs = [(r["name"], r["name"]) for r in db.item_facets("item_subclass", item_class=kind)] if kind else []
        slots = [(r["name"], r["name"]) for r in db.item_facets("inventory_type", item_class=kind, item_subclass=sub)]
        self._select("kind", "1. What kind of item?", any_opt + kinds, 0)
        self._select("sub", "2. What type? (Sword, Cloth, Plate...)" if kind else "2. What type? (pick a kind first)",
                     any_opt + subs, 1)
        self._select("slot", "3. Which slot?", any_opt + slots, 2)
        self._select("band", "4. What level?", any_opt + [(l, v) for l, v in C.level_bands()], 3)
        go = discord.ui.Button(label="Show who can make it", style=discord.ButtonStyle.success, row=4)
        go.callback = self._go
        self.add_item(go)
        tog = discord.ui.Button(label=("Showing: everything" if show_all else "Showing: only what the guild can make"),
                                style=discord.ButtonStyle.secondary, row=4)
        tog.callback = self._toggle
        self.add_item(tog)
        reset = discord.ui.Button(label="Start over", style=discord.ButtonStyle.secondary, row=4)
        reset.callback = self._reset
        self.add_item(reset)

    def _select(self, attr: str, placeholder: str, options, row: int) -> None:
        cur = getattr(self, attr)
        opts = [discord.SelectOption(label=l[:100], value=v[:100], default=(v == (cur or C.ANY))) for l, v in options[:25]]
        sel = discord.ui.Select(placeholder=placeholder, options=opts, row=row)

        async def picked(interaction: discord.Interaction, attr=attr, sel=sel) -> None:
            v = sel.values[0]
            state = dict(kind=self.kind, sub=self.sub, slot=self.slot, band=self.band, show_all=self.show_all)
            state[attr] = None if v == C.ANY else v
            if attr == "kind":                       # a new kind makes the old type and slot meaningless
                state["sub"] = state["slot"] = None
            if attr == "sub":
                state["slot"] = None
            await interaction.response.edit_message(view=CraftWizard(self.bot, **state))
        sel.callback = picked
        self.add_item(sel)

    def _state(self) -> dict:
        return dict(kind=self.kind, sub=self.sub, slot=self.slot, band=self.band, show_all=self.show_all)

    async def _toggle(self, interaction: discord.Interaction) -> None:
        state = self._state()
        state["show_all"] = not self.show_all
        await interaction.response.edit_message(view=CraftWizard(self.bot, **state))

    async def _reset(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(content=CRAFT_PROMPT, embed=None, view=CraftWizard(self.bot))

    async def _go(self, interaction: discord.Interaction) -> None:
        lo, hi = C.parse_band(self.band)
        embed, msg = craftable_result(self.bot.db, self.kind, self.sub, self.slot, lo, hi, None, self.show_all)
        await interaction.response.edit_message(content=msg or "Here's what I found. Change anything above and tap the green button again.",
                                                embed=embed, view=CraftWizard(self.bot, **self._state()))


HELP_MEMBER = [
    ("Claim and sign up", [
        ("/link", "claim your character: type a few letters of its name"),
        ("/unlink", "let go of a character"),
        ("/main", "pick which of your characters is your main"),
        ("/raids", "upcoming raids"),
        ("/help", "this list"),
    ]),
    ("Look stuff up", [
        ("/who", "a character, or yours"),
        ("/roster", "everyone in the guild"),
        ("/professions", "who has which profession"),
        ("/whohas", "who's wearing an item"),
        ("/recipes", "what a profession can make, and who can make it"),
        ("/whocan", "who can craft something"),
        ("/craftable", "find gear by kind, type, slot and level, and who can make it"),
        ("/gaps", "what the guild is missing in professions"),
    ]),
]
HELP_OFFICER = ("Officers", [
    ("/raid-create", "make a raid"),
    ("/raid-edit", "change a raid"),
    ("/raid-end", "wrap one up"),
    ("/raid-cancel", "call one off and tell everyone"),
    ("/guild-sync", "refresh from Blizzard now"),
    ("/claim-panel", "post the claim button"),
    ("/claims", "who has claimed what"),
    ("/unlink-member", "clear everything someone claimed"),
    ("/release", "free one character"),
    ("/wanted", "what people searched for that nobody can make"),
])


def help_embed(is_officer: bool) -> discord.Embed:
    e = discord.Embed(title="Commands")
    for title, rows in HELP_MEMBER + ([HELP_OFFICER] if is_officer else []):
        e.add_field(name=title, value="\n".join(f"`{c}` {d}" for c, d in rows), inline=False)
    return e


def gaps_overview(db: Database) -> discord.Embed:
    rows = db.profession_coverage()
    lines, none = [], []
    for r in rows:
        if not r["members"]:
            none.append(r["name"])
            continue
        lines.append(f"**{r['name']}**: {r['members']} guildie(s), best {r['best']}; "
                     f"guild knows {r['known']} of {r['total']} recipes")
    text = "\n".join(lines)
    if none:
        text += "\n\n**Nobody has:** " + ", ".join(none)
    e = discord.Embed(title="Profession gaps", description=clip(text.split("\n"), 4000))
    e.set_footer(text="Totals include everything in Blizzard's data, not only what is learnable in game yet. "
                      f"Known recipes as of {db.get_meta('last_sync_at') or 'never'} UTC.")
    return e


def gaps_for(db: Database, profession: str) -> discord.Embed:
    miss = db.missing_recipes(profession)
    best = db.best_in_profession(profession)
    who = ", ".join(f"{R.full_name(b)} {b['skill']}/{b['max_skill']}" for b in best) or "nobody in the guild has this profession"
    lines = []
    for r in miss:
        lvl = "" if not r["required_level"] else f" (L{r['required_level']})"
        kind = ", ".join(x for x in (r["item_subclass"], r["inventory_type"]) if x and x != "Non-equippable")
        lines.append(f"{item_link(r['name'])}{lvl}" + (f" - {kind}" if kind else ""))
    head = f"**Best in the guild:** {who}\n**Nobody knows these {len(miss)}** (lowest level first). " \
           "Click a name to see on Wowhead where it is learned.\n"
    e = discord.Embed(title=f"{profession}: recipes the guild doesn't have", description=head + clip(lines, 3700 - len(head)))
    e.set_footer(text="Blizzard's data doesn't say where a recipe is learned, so that part is on Wowhead. "
                      f"Known recipes as of {db.get_meta('last_sync_at') or 'never'} UTC.")
    return e


class GapsView(discord.ui.View):
    """Overview of every profession, with a dropdown to see what is missing in one."""

    def __init__(self, bot: "GuildBot", chosen=None):
        super().__init__(timeout=900)
        self.bot = bot
        names = [r["name"] for r in bot.db.profession_coverage()][:25]
        sel = discord.ui.Select(placeholder="See what's missing in a profession",
                                options=[discord.SelectOption(label=n, value=n, default=(n == chosen)) for n in names])
        sel.callback = self._picked
        self.add_item(sel)
        if chosen:
            back = discord.ui.Button(label="Back to overview", style=discord.ButtonStyle.secondary)
            back.callback = self._back
            self.add_item(back)

    async def _picked(self, interaction: discord.Interaction) -> None:
        pick = interaction.data["values"][0]
        await interaction.response.edit_message(embed=gaps_for(self.bot.db, pick), view=GapsView(self.bot, pick))

    async def _back(self, interaction: discord.Interaction) -> None:
        await interaction.response.edit_message(embed=gaps_overview(self.bot.db), view=GapsView(self.bot))


def gap_card(db: Database, name: str, discord_id: int):
    """A 'nobody in the guild has this yet' card for a recipe that exists, or None if there is no such recipe.
    Records the miss so officers can see what people keep looking for."""
    entries = db.catalog_recipe(name)
    if not entries:
        return None
    lines = []
    for en in entries:
        best = db.best_in_profession(en["profession"], 2)
        who = ", ".join(f"{R.full_name(b)} {b['skill']}/{b['max_skill']}" for b in best) \
            or "nobody in the guild has this profession"
        extra = ", ".join(x for x in (en["item_subclass"], en["inventory_type"]) if x and x != "Non-equippable")
        lvl = f", L{en['required_level']}" if en["required_level"] else ""
        lines.append(f"**{en['profession']}**{lvl}{(' - ' + extra) if extra else ''}\nClosest in the guild: {who}")
        db.add_wanted(name, en["profession"], discord_id, utcnow())
    e = discord.Embed(title=f"Gap: nobody in the guild can make {name}",
                      description="\n\n".join(lines))
    e.add_field(name="Where to get it", value=f"{item_link(name)} (Blizzard's data doesn't say where it is learned)",
                inline=False)
    e.set_footer(text="Noted as something people are looking for. Officers can see the list with /wanted.")
    return e


CRAFT_PROMPT = "Find who can craft something. Pick what you want, then tap the green button. Skip anything you don't care about."


class OfferView(discord.ui.View):
    """Take it / Pass buttons on a 'a spot opened up' message. Persistent: custom_ids carry the offer number."""

    def __init__(self, bot: "GuildBot", offer_id: int):
        super().__init__(timeout=None)
        self.bot, self.offer_id = bot, offer_id
        for answer, label, style in (("yes", "Take it", discord.ButtonStyle.success),
                                     ("no", "Pass", discord.ButtonStyle.secondary)):
            b = discord.ui.Button(label=label, style=style, custom_id=f"offer:{offer_id}:{answer}")
            b.callback = self._make(answer == "yes")
            self.add_item(b)

    def _make(self, yes: bool):
        async def callback(interaction: discord.Interaction):
            await self.bot.answer_offer(interaction, self.offer_id, yes)
        return callback


class GuildTree(app_commands.CommandTree):
    """Slash commands only run in the channels named in BOT_CHANNEL_IDS (if any are set)."""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = self.client.cfg.channel_ids
        if not allowed or interaction.channel_id in allowed:
            return True
        where = " or ".join(f"<#{c}>" for c in sorted(allowed))
        await interaction.response.send_message(f"Use me in {where}.", ephemeral=True)
        return False


class GuildBot(discord.Client):
    def __init__(self, cfg: Config, db: Database, blizzard):
        super().__init__(intents=discord.Intents.default())
        self.cfg, self.db, self.blizzard = cfg, db, blizzard
        self.tree = GuildTree(self)
        self._sync_lock = asyncio.Lock()
        self._busy: set[int] = set()      # raids the bot itself is changing right now (ignore our own deletions)
        register_commands(self)

    async def setup_hook(self) -> None:
        self.add_view(ClaimPanel(self))
        for o in self.db.pending_offers():
            self.add_view(OfferView(self, o["id"]))
        for raid in self.db.open_raids():
            self.add_view(RaidView(self, raid["id"]))
        if self.cfg.discord_guild_id:
            guild = discord.Object(id=self.cfg.discord_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()
        self.sync_job = tasks.loop(minutes=self.cfg.sync_minutes)(self._sync_once)
        self.sync_job.start()
        self.reminder_job = tasks.loop(minutes=1)(self._send_reminders)
        self.reminder_job.start()
        self.close_job = tasks.loop(minutes=1)(self._close_started)
        self.close_job.start()
        self.end_job = tasks.loop(minutes=1)(self._end_old_raids)
        self.end_job.start()
        self.offer_job = tasks.loop(minutes=1)(self._expire_offers)
        self.offer_job.start()

    async def post_raid(self, interaction: discord.Interaction, title: str, start: datetime, size: int,
                        caps: dict) -> bool:
        """Create the raid row, post the signup message and make the Discord event. Used by the wizard
        and by /raid-create. Returns True once the raid is posted."""
        db = self.db
        if start <= datetime.now(timezone.utc):
            await interaction.response.send_message("That time is in the past.", ephemeral=True)
            return False
        raid_id = db.create_raid(title, start.isoformat(timespec="seconds"), size, interaction.user.id, caps)
        raid = db.get_raid(raid_id)
        try:
            await interaction.response.send_message(embed=raid_embed(db, raid), view=RaidView(self, raid_id))
            msg = await interaction.original_response()
        except Exception:
            # Not recorded: take the post down if it went out, and remove the row, so a retry starts clean.
            try:
                await interaction.delete_original_response()
            except discord.HTTPException:
                pass
            db.delete_raid(raid_id)
            raise
        event_id, note = None, ""
        try:
            ev = await interaction.guild.create_scheduled_event(
                name=title, start_time=start, end_time=start + timedelta(hours=3),
                entity_type=discord.EntityType.external, location="In game (WoW Forever)",
                privacy_level=discord.PrivacyLevel.guild_only)
            event_id = ev.id
        except discord.HTTPException:
            note = "Raid posted, but I couldn't create the Discord event (check my Manage Events permission)."
        db.set_raid_posted(raid_id, msg.channel.id, msg.id, event_id)
        try:
            await msg.pin()                          # live raids stay pinned until they end
        except discord.HTTPException:
            log.warning("could not pin raid %s (check my Manage Messages permission)", raid_id)
        if note:
            await interaction.followup.send(note, ephemeral=True)
        return True

    # ---- background jobs ---------------------------------------------
    async def run_sync(self):
        async with self._sync_lock:
            return await sync_guild(self.db, self.blizzard, self.cfg.guild_slug)

    async def _sync_once(self) -> None:
        try:
            res = await self.run_sync()
            log.info("sync ok: %d members, %d failures", res.members, len(res.failures))
        except Exception:
            log.exception("roster sync failed")
        try:
            n = await sync_recipe_catalog(self.db, self.blizzard)
            if n:
                log.info("recipe catalogue refreshed: %d recipes", n)
        except Exception:
            log.exception("recipe catalogue refresh failed")
        try:
            r, i = await sync_item_catalog(self.db, self.blizzard)
            if r or i:
                log.info("item catalogue: looked up %d recipes and %d items", r, i)
        except Exception:
            log.exception("item catalogue refresh failed")

    async def _send_reminders(self) -> None:
        """Private reminder to everyone signed up (slots, bench and tentative). Nothing is posted in the channel.
        Anyone whose DMs are closed is reported privately to whoever created the raid."""
        for raid in self.db.due_reminders(datetime.now(timezone.utc), 60):
            try:
                g = R.group_signups(self.db.signups(raid["id"]))
                ids = list(dict.fromkeys(s["discord_id"] for r in (*R.COUNTED, "bench", "tentative") for s in g[r]))
                text = R.reminder_text(raid)
                blocked = []
                for uid in ids:
                    try:
                        user = self.get_user(uid) or await self.fetch_user(uid)
                        if not user.bot:
                            await user.send(text)
                    except discord.HTTPException:
                        blocked.append(uid)
                self.db.mark_reminded(raid["id"])
                if blocked and raid["created_by"]:
                    try:
                        owner = self.get_user(raid["created_by"]) or await self.fetch_user(raid["created_by"])
                        await owner.send(f"Couldn't remind these players about **{raid['title']}** (their DMs are "
                                         "closed): " + " ".join(f"<@{u}>" for u in blocked))
                    except discord.HTTPException:
                        log.warning("could not tell the raid creator about blocked reminders")
            except Exception:
                log.exception("reminder failed for raid %s", raid["id"])

    async def _close_started(self) -> None:
        """Take the buttons off raids that have started. A raid is only marked closed once its
        message is updated (or is gone), so a Discord hiccup is retried on the next pass."""
        for raid in self.db.started_open(datetime.now(timezone.utc)):
            try:
                if raid["channel_id"] and raid["message_id"]:
                    chan = self.get_channel(raid["channel_id"]) or await self.fetch_channel(raid["channel_id"])
                    msg = await chan.fetch_message(raid["message_id"])
                    closed = dict(raid) | {"status": "closed"}
                    await msg.edit(embed=raid_embed(self.db, closed), view=None)
                self.db.mark_closed(raid["id"])
                await self.dm_user(raid["created_by"], R.roster_summary(raid, self.db.signups(raid["id"])))
            except discord.NotFound:
                self.db.mark_closed(raid["id"])      # message or channel deleted: nothing left to tidy
            except Exception:
                log.exception("could not remove buttons from started raid %s; will retry", raid["id"])

    # ---- bench queue ----------------------------------------------------
    async def refresh_raid_post(self, raid_id: int) -> None:
        raid = self.db.get_raid(raid_id)
        if not raid or not raid["channel_id"] or not raid["message_id"]:
            return
        try:
            chan = self.get_channel(raid["channel_id"]) or await self.fetch_channel(raid["channel_id"])
            msg = await chan.fetch_message(raid["message_id"])
            await msg.edit(embed=raid_embed(self.db, raid))
        except discord.HTTPException:
            log.exception("could not refresh the post for raid %s", raid_id)

    async def fill_open_slots(self, raid_id: int) -> None:
        """If a slot is free and people are waiting on the bench, ask the next one in line (by DM)."""
        for _ in range(6):                                  # someone with DMs closed is skipped, then the next is asked
            raid = self.db.get_raid(raid_id)
            if not raid or raid["status"] != "open" or \
                    datetime.fromisoformat(raid["starts_at"]) <= datetime.now(timezone.utc):
                return
            picks = R.next_offers(raid, self.db.signups(raid_id), self.db.offers_for_raid(raid_id))
            if not picks:
                return
            now = datetime.now(timezone.utc)
            ping_at, expires_at = R.offer_window(now, datetime.fromisoformat(raid["starts_at"]))
            for uid, role in picks:
                offer_id = self.db.create_offer(raid_id, uid, role, now.isoformat(timespec="seconds"),
                                                ping_at.isoformat(timespec="seconds"),
                                                expires_at.isoformat(timespec="seconds"))
                sent = False
                try:
                    user = self.get_user(uid) or await self.fetch_user(uid)
                    if user.bot:
                        self.db.set_offer_state(offer_id, "expired")
                        continue
                    msg = await user.send(R.offer_text(raid, role, expires_at), view=OfferView(self, offer_id))
                    self.db.set_offer_messages(offer_id, dm=msg.id)
                    sent = True
                except discord.HTTPException:
                    pass
                if not sent and not await self.ping_offer(offer_id):    # DMs closed: ask in the channel instead
                    self.db.set_offer_state(offer_id, "expired")

    async def ping_offer(self, offer_id: int) -> bool:
        """Ask in the raid channel with an @ and the same buttons. Deleted again once it is answered."""
        offer = self.db.get_offer(offer_id)
        raid = self.db.get_raid(offer["raid_id"]) if offer else None
        if not raid or not raid["channel_id"]:
            return False
        try:
            chan = self.get_channel(raid["channel_id"]) or await self.fetch_channel(raid["channel_id"])
            last = offer["dm_msg_id"] is not None                      # they got a DM already: this is the last call
            expires = datetime.fromisoformat(offer["expires_at"])
            msg = await chan.send(R.ping_text(raid, offer["role"], offer["discord_id"], expires, last), view=OfferView(self, offer_id),
                                  allowed_mentions=discord.AllowedMentions(users=[discord.Object(id=offer["discord_id"])]))
            self.db.set_offer_messages(offer_id, chan=msg.id)
            return True
        except discord.HTTPException:
            log.exception("could not ping offer %s in the raid channel", offer_id)
            return False

    async def sweep_offer_messages(self) -> None:
        """Delete finished pings from the channel and close the buttons on finished DMs."""
        for o in self.db.offers_to_clean():
            try:
                raid = self.db.get_raid(o["raid_id"])
                if o["chan_msg_id"] and raid and raid["channel_id"]:
                    chan = self.get_channel(raid["channel_id"]) or await self.fetch_channel(raid["channel_id"])
                    try:
                        await chan.get_partial_message(o["chan_msg_id"]).delete()
                    except discord.NotFound:
                        pass
                if o["dm_msg_id"]:
                    try:
                        user = self.get_user(o["discord_id"]) or await self.fetch_user(o["discord_id"])
                        dm = user.dm_channel or await user.create_dm()
                        text = {"accepted": "You took it.", "declined": "You passed."}.get(o["state"], "This offer is closed.")
                        await dm.get_partial_message(o["dm_msg_id"]).edit(content=text, view=None)
                    except discord.NotFound:
                        pass
                self.db.mark_offer_cleaned(o["id"])
            except discord.HTTPException:
                log.exception("could not tidy offer %s; will retry", o["id"])

    async def _reply_to_offer(self, interaction: discord.Interaction, offer, text: str) -> None:
        """Answer where they clicked: edit the DM, or whisper (ephemeral) if they clicked the channel ping."""
        msg = getattr(interaction, "message", None)
        if offer and offer["chan_msg_id"] and msg is not None and msg.id == offer["chan_msg_id"]:
            await interaction.response.send_message(text, ephemeral=True)
        else:
            await interaction.response.edit_message(content=text, view=None)

    async def answer_offer(self, interaction: discord.Interaction, offer_id: int, yes: bool) -> None:
        db = self.db
        offer = db.get_offer(offer_id)
        if offer and interaction.user.id != offer["discord_id"]:
            await interaction.response.send_message("That spot was offered to someone else.", ephemeral=True)
            return
        if not offer or offer["state"] != "pending":
            await self._reply_to_offer(interaction, offer, "That offer has expired.")
            await self.sweep_offer_messages()
            return
        raid = db.get_raid(offer["raid_id"])
        started = raid and datetime.fromisoformat(raid["starts_at"]) <= datetime.now(timezone.utc)
        if not raid or raid["status"] != "open" or started:
            db.set_offer_state(offer_id, "expired")
            await self._reply_to_offer(interaction, offer, "That raid has already started or was cancelled.")
            await self.sweep_offer_messages()
            return
        if not yes:
            db.set_offer_state(offer_id, "declined")
            await self._reply_to_offer(interaction, offer, "No problem, you're still on the bench.")
            await self.sweep_offer_messages()
            await self.fill_open_slots(raid["id"])
            return
        uid, role = offer["discord_id"], offer["role"]
        mine = next((s for s in db.signups(raid["id"]) if s["discord_id"] == uid), None)
        groups = R.group_signups(db.signups(raid["id"]))
        if mine is None or R.resolve_role(role, groups, raid["size"], uid, R.caps_of(raid)) != role:
            db.set_offer_state(offer_id, "expired")
            await self._reply_to_offer(interaction, offer, "Sorry, that spot just got taken.")
            await self.sweep_offer_messages()
            await self.fill_open_slots(raid["id"])
            return
        db.upsert_signup(raid["id"], uid, mine["slug"], role, utcnow(), None)
        db.set_offer_state(offer_id, "accepted")
        await self._reply_to_offer(interaction, offer, f"You're in as {R.ROLE_SINGULAR[role]} for **{raid['title']}**.")
        await self.sweep_offer_messages()
        await self.refresh_raid_post(raid["id"])

    async def _expire_offers(self) -> None:
        """An offer nobody answered in time goes to the next person in line; quiet ones get a last-call ping."""
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for o in self.db.expire_old_offers(now_iso):
            try:
                await self.fill_open_slots(o["raid_id"])
            except Exception:
                log.exception("could not pass on an expired offer for raid %s", o["raid_id"])
        for o in self.db.offers_to_ping(now_iso):              # no answer to the DM yet: last call in the channel
            await self.ping_offer(o["id"])
        await self.sweep_offer_messages()

    # ---- end of a raid --------------------------------------------------
    def busy(self, raid_id: int):
        """`with bot.busy(id):` while the bot itself removes a raid's post or event, so the listeners below
        do not mistake our own deletions for someone doing it by hand."""
        bot = self

        class _Guard:
            def __enter__(self_inner):
                bot._busy.add(raid_id)

            def __exit__(self_inner, *exc):
                bot._busy.discard(raid_id)
        return _Guard()

    async def dm_user(self, user_id: int, text: str) -> bool:
        try:
            user = self.get_user(user_id) or await self.fetch_user(user_id)
            if user.bot:
                return False
            await user.send(text)
            return True
        except discord.HTTPException:
            return False

    async def finish_raid(self, raid_id: int, *, remove_event: bool, dm_ids=(), note: str = "") -> bool:
        """End a raid: the post stays as the record (marked COMPLETED, buttons off, unpinned), the event is
        ended (or removed if it never started), and the roster goes to dm_ids. Safe to repeat."""
        db = self.db
        raid = db.get_raid(raid_id)
        if not raid or raid["status"] not in ("open", "closed"):
            return False
        with self.busy(raid_id):
            roster = R.roster_summary(raid, db.signups(raid_id))
            if remove_event and raid["discord_event_id"]:
                try:
                    guild = self.get_guild(self.cfg.discord_guild_id) if self.cfg.discord_guild_id else None
                    if guild:
                        ev = await guild.fetch_scheduled_event(raid["discord_event_id"])
                        if ev.status == discord.EventStatus.active:
                            await ev.end()
                        elif ev.status == discord.EventStatus.scheduled:
                            await ev.delete()
                except discord.NotFound:
                    pass
                except discord.HTTPException:
                    log.exception("could not close the event for raid %s", raid_id)
            db.mark_ended(raid_id)
            if raid["channel_id"] and raid["message_id"]:
                try:
                    chan = self.get_channel(raid["channel_id"]) or await self.fetch_channel(raid["channel_id"])
                    msg = await chan.fetch_message(raid["message_id"])
                    await msg.edit(embed=raid_embed(db, db.get_raid(raid_id)), view=None)
                    if getattr(msg, "pinned", True):
                        await msg.unpin()
                except discord.NotFound:
                    pass
                except discord.HTTPException:
                    log.exception("could not update the post for raid %s", raid_id)
        for uid in dict.fromkeys(dm_ids):
            await self.dm_user(uid, (note + "\n" if note else "") + roster)
        return True

    async def _end_old_raids(self) -> None:
        """Three hours after a raid started, mark its post COMPLETED and unpin it. The post stays as the record."""
        for raid in self.db.closed_ended_before(datetime.now(timezone.utc), R.END_AFTER_HOURS):
            try:
                await self.finish_raid(raid["id"], remove_event=False)
            except Exception:
                log.exception("could not clean up raid %s", raid["id"])

    async def _handled_by_hand(self, raid, what: str) -> None:
        """Someone removed a raid's post or event in Discord itself: close the raid and tell its organizer."""
        if not raid or raid["id"] in self._busy or raid["status"] not in ("open", "closed"):
            return
        note = f"I noticed the {what} for **{raid['title']}** was removed by hand, so I closed the raid."
        if raid["status"] == "open" and datetime.fromisoformat(raid["starts_at"]) > datetime.now(timezone.utc):
            note += " Players weren't told; use /raid-cancel next time to message them."
        await self.finish_raid(raid["id"], remove_event=True, dm_ids=[raid["created_by"]], note=note)

    async def on_message(self, message: discord.Message) -> None:
        """Discord adds a 'the bot pinned a message' line to the channel each time we pin a raid; remove it."""
        if message.type == discord.MessageType.pins_add and self.user and message.author.id == self.user.id:
            try:
                await message.delete()
            except discord.HTTPException:
                pass

    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent) -> None:
        await self._handled_by_hand(self.db.raid_by_message(payload.message_id), "signup post")

    async def on_scheduled_event_delete(self, event: discord.ScheduledEvent) -> None:
        await self._handled_by_hand(self.db.raid_by_event(event.id), "Discord event")

    async def on_scheduled_event_update(self, before: discord.ScheduledEvent, after: discord.ScheduledEvent) -> None:
        if after.status in (discord.EventStatus.completed, discord.EventStatus.cancelled):
            raid = self.db.raid_by_event(after.id)
            if raid:       # ended by hand, or Discord ended it at the 3-hour mark: either way the raid is over
                await self._handled_by_hand(raid, "Discord event")

    # ---- raid signup --------------------------------------------------
    async def handle_signup(self, interaction: discord.Interaction, raid_id: int, role: str) -> None:
        raid = self.db.get_raid(raid_id)
        if not raid or raid["status"] != "open" or \
                datetime.fromisoformat(raid["starts_at"]) <= datetime.now(timezone.utc):
            await interaction.response.send_message("This raid is closed.", ephemeral=True)
            return
        # A signup is a Discord account, a role and a character: the bot has to know who you are in the guild.
        # With several linked characters it asks which one on every tap (their last choice is pre-selected).
        chars = self.db.characters_for(interaction.user.id)
        if not chars:
            picker = ClaimPicker(self)
            await interaction.response.send_message(
                "To sign up I need to know who you are in the guild. Claim your character first, then tap your role "
                "again.\n" + picker.header(), view=picker, ephemeral=True)
            return
        prior = next((s for s in self.db.signups(raid_id) if s["discord_id"] == interaction.user.id), None)
        if len(chars) > 1 and role != "absent":
            await interaction.response.send_modal(
                SignupModal(self, raid_id, role, chars, current=prior["slug"] if prior else None))
            return
        slugs = {c["slug"] for c in chars}
        main = self.db.main_for(interaction.user.id)
        slug = prior["slug"] if prior and prior["slug"] in slugs else (main["slug"] if main else None)
        landed = self.apply_signup(raid, interaction.user.id, role, slug)
        await interaction.response.edit_message(embed=raid_embed(self.db, raid))
        if landed != role:
            where = "the bench" if landed == "bench" else f"{R.ROLE_LABEL[landed].lower()}"
            await interaction.followup.send(
                f"{R.ROLE_LABEL.get(role, role)} (or the raid) is full, so you're on {where}. "
                "If a spot opens up I'll message you.", ephemeral=True)
        await self.fill_open_slots(raid["id"])         # they may have just left a slot someone is waiting for

    def apply_signup(self, raid, discord_id: int, role: str, slug) -> str:
        """Record the signup; returns the role they actually landed in (bench when full)."""
        landed = R.resolve_role(role, R.group_signups(self.db.signups(raid["id"])), raid["size"],
                                discord_id, R.caps_of(raid))
        wanted = role if landed == "bench" and role in R.COUNTED else None     # bounced to the bench: remember why
        self.db.upsert_signup(raid["id"], discord_id, slug, landed, utcnow(), wanted)
        return landed


class SignupModal(discord.ui.Modal):
    """Pop-up in the middle of the screen: which of your characters are you signing up as?"""

    def __init__(self, bot: GuildBot, raid_id: int, role: str, chars, current=None):
        super().__init__(title=f"Sign up as {R.ROLE_LABEL[role]}"[:45], timeout=300)
        self.bot, self.raid_id, self.role = bot, raid_id, role
        pre = current or next((c["slug"] for c in chars if c["is_main"]), chars[0]["slug"])
        self.choice = discord.ui.Select(
            placeholder="Pick a character",
            options=[discord.SelectOption(label=char_label(c), value=c["slug"], default=(c["slug"] == pre))
                     for c in chars[:25]])
        self.add_item(discord.ui.Label(text="Which character?", component=self.choice))

    async def on_submit(self, interaction: discord.Interaction) -> None:
        db = self.bot.db
        raid = db.get_raid(self.raid_id)
        if not raid or raid["status"] != "open" or \
                datetime.fromisoformat(raid["starts_at"]) <= datetime.now(timezone.utc):
            await interaction.response.send_message("This raid is closed.", ephemeral=True)
            return
        slug = self.choice.values[0]
        if slug not in {c["slug"] for c in db.characters_for(interaction.user.id)}:
            await interaction.response.send_message("That character isn't linked to you.", ephemeral=True)
            return
        landed = self.bot.apply_signup(raid, interaction.user.id, self.role, slug)
        await interaction.response.edit_message(embed=raid_embed(db, raid))    # updates the raid post itself
        if landed != self.role:
            where = "the bench" if landed == "bench" else R.ROLE_LABEL[landed].lower()
            await interaction.followup.send(
                f"{R.ROLE_LABEL.get(self.role, self.role)} (or the raid) is full, so you're on {where}. "
                "If a spot opens up I'll message you.", ephemeral=True)
        await self.bot.fill_open_slots(raid["id"])


def register_commands(bot: GuildBot) -> None:
    tree, db = bot.tree, bot.db
    officer = app_commands.checks.has_permissions(manage_events=True)

    async def char_ac(interaction: discord.Interaction, current: str):
        return [app_commands.Choice(
                    name=f"{R.full_name(r)} (L{r['level'] or '?'} {r['class_name'] or ''})".strip()[:100],
                    value=r["slug"])
                for r in db.search_characters(current)]

    async def unclaimed_ac(interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=char_label(r), value=r["slug"])
                for r in db.unclaimed_characters(current)[:25]]

    @tree.error
    async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            msg = "You need the Manage Events permission for that."
        else:
            log.exception("command error", exc_info=error)
            msg = "Something went wrong. It's been logged."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)

    # ---- who is who ---------------------------------------------------
    @tree.command(name="link", description="Claim your character: type a few letters of its name")
    @app_commands.autocomplete(character=unclaimed_ac)
    @app_commands.guild_only()
    async def link(interaction: discord.Interaction, character: str):
        row = db.find_character(character)
        if not row:
            await interaction.response.send_message(
                f"No guild member found for `{character}`. Roster last synced {rel(db.get_meta('last_sync_at'))}.",
                ephemeral=True)
            return
        owner = db.owner_of(row["slug"])
        if not interaction.permissions.manage_events:       # members: first come, capped, never steal
            res = db.claim(interaction.user.id, [row["slug"]])
            log.info("link by %s: %s", interaction.user.id, res)
            if res["linked"]:
                msg = f"Linked **{R.full_name(row)}**."
            elif res["taken"]:
                msg = f"**{R.full_name(row)}** is already claimed. Ask a Moderator if that is wrong."
            elif res["over_cap"]:
                msg = f"You can claim up to {db.MAX_CLAIMS} characters; ask a Moderator for more."
            else:
                msg = f"**{R.full_name(row)}** is already yours."
            await interaction.response.send_message(msg, ephemeral=True)
            return
        if owner and owner != interaction.user.id:
            db.release(row["slug"])                          # officers may take over a claimed character
        became_main = db.link(interaction.user.id, row["slug"])
        await interaction.response.send_message(
            f"Linked **{R.full_name(row)}**" + (" as your main." if became_main else ". Use `/main` to make it your main."),
            ephemeral=True)

    @tree.command(name="unlink", description="Remove a character link from your Discord account")
    @app_commands.autocomplete(character=char_ac)
    async def unlink(interaction: discord.Interaction, character: str):
        row = db.find_character(character)
        if row:
            db.unlink(interaction.user.id, row["slug"])
        await interaction.response.send_message("Done.", ephemeral=True)

    @tree.command(name="main", description="Choose which of your linked characters signs up for raids")
    @app_commands.autocomplete(character=char_ac)
    async def main_cmd(interaction: discord.Interaction, character: str):
        row = db.find_character(character)
        ok = bool(row) and db.set_main(interaction.user.id, row["slug"])
        await interaction.response.send_message(
            f"**{R.full_name(row)}** is now your main." if ok else "Link that character first with `/link`.",
            ephemeral=True)

    @tree.command(name="who", description="Show a character, a member's characters, or your own")
    @app_commands.autocomplete(character=char_ac)
    async def who(interaction: discord.Interaction, character: str | None = None,
                  member: discord.Member | None = None):
        if character:
            row = db.find_character(character)
            rows = [row] if row else []
        else:
            rows = db.characters_for((member or interaction.user).id)
        if not rows:
            await interaction.response.send_message(
                "Nothing found. Link a character with `/link`, or give a character name.", ephemeral=True)
            return
        embeds = []
        for r in rows[:5]:
            e = discord.Embed(title=R.full_name(r),
                              description=f"L{r['level'] or '?'} {r['race_name'] or ''} {r['class_name'] or ''}".strip())
            profs = db.professions_for(r["slug"])
            e.add_field(name="Professions",
                        value="\n".join(f"{p['profession']} {p['skill']}/{p['max_skill']}" for p in profs) or "—")
            gear = db.equipment_for(r["slug"])
            gear_lines = [f"{g['slot']}: {item_link(g['item_name'])}" for g in gear]
            for n, chunk in enumerate(chunk_lines(gear_lines, 1000) or [["—"]]):
                e.add_field(name="Gear" if n == 0 else "Gear (cont.)", value="\n".join(chunk), inline=False)
            e.set_footer(text=who_footer(r, profs, gear))
            embeds.append(e)
        await interaction.response.send_message(embeds=embeds)

    @tree.command(name="roster", description="List guild characters")
    async def roster(interaction: discord.Interaction, class_name: str | None = None,
                     min_level: int | None = None):
        rows = db.roster(class_name, min_level)
        lines = [f"**{R.full_name(r)}**: L{r['level'] or '?'} {r['class_name'] or ''}" for r in rows]
        e = discord.Embed(title=f"Roster ({len(rows)})", description=clip(lines, 4000) or "Nobody found.")
        e.set_footer(text=data_as_of(rows, db.get_meta('last_sync_at'), key="profile_at"))
        await interaction.response.send_message(embed=e)

    async def item_ac(interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=f"{r['name']} ({r['n']})"[:100], value=r["name"][:100])
                for r in db.item_names(current)]

    async def profession_ac(interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=f"{r['name']} ({r['n']})", value=r["name"])
                for r in db.profession_names(current)]

    @tree.command(name="professions", description="Who has which profession (leave blank for all)")
    @app_commands.autocomplete(profession=profession_ac)
    async def professions(interaction: discord.Interaction, profession: str = ""):
        rows = db.who_has_profession(profession)
        by: dict[str, list[str]] = {}
        for r in rows:
            by.setdefault(r["profession"], []).append(f"{R.full_name(r)} {r['skill']}/{r['max_skill']}")
        lines = [f"**{p}** ({len(v)}): {', '.join(v)}" for p, v in sorted(by.items())]
        e = discord.Embed(title="Professions", description=clip(lines, 4000) or "Nobody found.")
        e.set_footer(text=data_as_of(rows, db.get_meta('last_sync_at')))
        await interaction.response.send_message(embed=e)

    async def catalog_profession_ac(interaction: discord.Interaction, current: str):
        return [app_commands.Choice(name=f"{r['name']} ({r['n']} recipes)", value=r["name"])
                for r in db.catalog_professions(current)]

    async def recipe_ac(interaction: discord.Interaction, current: str):
        return [app_commands.Choice(
                    name=(f"{r['name']} - {r['profession']} ({r['n']})" if r["n"]
                          else f"{r['name']} - {r['profession']} (nobody yet)")[:100],
                    value=r["name"][:100])
                for r in db.recipe_names_all(current)]

    @tree.command(name="recipes", description="What a profession can make, and which guildies can make it")
    @app_commands.describe(profession="Pick a profession", match="Part of a recipe name (blank = overview)")
    @app_commands.autocomplete(profession=catalog_profession_ac)
    async def recipes(interaction: discord.Interaction, profession: str, match: str = ""):
        rows = db.recipes_for(profession, match)
        if not rows:
            await interaction.response.send_message(
                "No recipes found. Pick a profession from the list" + (" or try a different search word." if match else "."),
                ephemeral=True)
            return
        title = f"{profession}: {len(rows)} recipe(s)" + (f" matching '{match}'" if match else "")
        if not match:
            by: dict[str, list] = {}
            for r in rows:
                by.setdefault(r["category"] or "Other", []).append(r)
            known = [r for r in rows if r["knowers"]]
            lines = [f"**{cat}** - {len(rs)} recipes" for cat, rs in by.items()]
            head = "\n".join(lines)
            head += (f"\n\n**Known in the guild ({len(known)}):**\n" +
                     "\n".join(f"{item_link(r['name'])}: {r['knowers']}" for r in known)) if known else \
                "\n\nNobody in the guild has learned any of these yet."
            head += "\n\nAdd a search word to list the recipes themselves."
        else:
            head = "\n".join(f"{item_link(r['name'])}" + (f": {r['knowers']}" if r["knowers"] else "") for r in rows)
        e = discord.Embed(title=title[:256], description=clip(head.split("\n"), 4000))
        e.set_footer(text="Recipe list is everything in Blizzard's data, not only what is learnable in game yet. "
                          f"Known recipes as of {db.get_meta('last_sync_at') or 'never'} UTC.")
        await interaction.response.send_message(embed=e)

    async def facet_ac(column: str, interaction: discord.Interaction, current: str):
        chosen = getattr(interaction.namespace, "kind", None) if column == "item_subclass" else None
        return [app_commands.Choice(name=f"{r['name']} ({r['n']})", value=r["name"])
                for r in db.item_facets(column, current, chosen)]

    async def kind_ac(interaction: discord.Interaction, current: str):
        return await facet_ac("item_class", interaction, current)

    async def type_ac(interaction: discord.Interaction, current: str):
        return await facet_ac("item_subclass", interaction, current)

    async def slot_ac(interaction: discord.Interaction, current: str):
        return await facet_ac("inventory_type", interaction, current)

    @tree.command(name="craftable", description="Find who can craft gear (guided; or fill in the options to skip it)")
    @app_commands.describe(kind="Weapon, Armor, ...", type="Sword, Plate, Cloth, ...", slot="Head, Chest, One-Hand, ...",
                           min_level="Lowest level needed to use it", max_level="Highest level needed to use it",
                           profession="Only this profession", show_all="Also show items nobody in the guild can make")
    @app_commands.autocomplete(kind=kind_ac, type=type_ac, slot=slot_ac, profession=catalog_profession_ac)
    async def craftable(interaction: discord.Interaction, kind: str | None = None, type: str | None = None,
                        slot: str | None = None, min_level: int | None = None, max_level: int | None = None,
                        profession: str | None = None, show_all: bool = False):
        if not any(v is not None for v in (kind, type, slot, min_level, max_level, profession)) and not show_all:
            if not db.item_facets("item_class", limit=1):
                await interaction.response.send_message(
                    "I'm still looking up what recipes make (the first run takes a few minutes). Try again shortly.",
                    ephemeral=True)
                return
            await interaction.response.send_message(CRAFT_PROMPT, view=CraftWizard(bot), ephemeral=True)
            return
        embed, msg = craftable_result(db, kind, type, slot, min_level, max_level, profession, show_all)
        if msg:
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @tree.command(name="gaps", description="What the guild is missing in professions, and where to look it up")
    @app_commands.describe(profession="Leave blank for an overview of every profession")
    @app_commands.autocomplete(profession=catalog_profession_ac)
    async def gaps(interaction: discord.Interaction, profession: str | None = None):
        if not db.catalog_professions():
            await interaction.response.send_message(
                "I'm still loading the recipe list (the first run takes a few minutes). Try again shortly.", ephemeral=True)
            return
        if profession:
            if not db.catalog_professions(profession):
                await interaction.response.send_message("Pick a profession from the list.", ephemeral=True)
                return
            await interaction.response.send_message(embed=gaps_for(db, profession), ephemeral=True)
            return
        await interaction.response.send_message(embed=gaps_overview(db), view=GapsView(bot), ephemeral=True)

    @tree.command(name="wanted", description="What people searched for that nobody in the guild can make (officers)")
    @app_commands.guild_only()
    @officer
    async def wanted(interaction: discord.Interaction):
        rows = db.wanted_top()
        if not rows:
            await interaction.response.send_message("Nothing yet. Searches that find nobody show up here.", ephemeral=True)
            return
        lines = [f"{item_link(r['name'])} ({r['profession']}): searched {r['n']}x by {r['people']} "
                 f"person{'s' if r['people'] != 1 else ''}, last <t:{int(datetime.fromisoformat(r['last_at']).timestamp())}:R>"
                 for r in rows]
        e = discord.Embed(title="Most wanted, and nobody has it", description=clip(lines, 4000))
        await interaction.response.send_message(embed=e, ephemeral=True)

    @tree.command(name="help", description="Every command, in a message only you can see")
    async def help_cmd(interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=help_embed(bool(interaction.permissions.manage_events)), ephemeral=True)

    @tree.command(name="whocan", description="Who in the guild can craft something (type a few letters)")
    @app_commands.autocomplete(recipe=recipe_ac)
    async def whocan(interaction: discord.Interaction, recipe: str):
        rows = db.who_can_craft(recipe)
        if not rows:
            card = gap_card(db, recipe, interaction.user.id)
            if card:
                await interaction.response.send_message(embed=card, ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"I don't know a recipe called \"{recipe}\". Look it up: {item_link(recipe)}", ephemeral=True)
            return
        lines = [f"**{R.full_name(r)}**: {r['profession']} {r['skill']}/{r['max_skill']}" for r in rows]
        e = discord.Embed(title=f"Who can make {recipe}", description=clip(lines, 4000))
        e.add_field(name="Look it up", value=item_link(recipe), inline=False)
        e.set_footer(text=data_as_of(rows, db.get_meta('last_sync_at')))
        await interaction.response.send_message(embed=e)

    @tree.command(name="whohas", description="Who has an item equipped (type a few letters of its name)")
    @app_commands.autocomplete(item=item_ac)
    async def whohas(interaction: discord.Interaction, item: str):
        rows = db.search_items(item)
        lines = [f"**{R.full_name(r)}**: {item_link(r['item_name'])} ({r['slot']})" for r in rows]
        e = discord.Embed(title=f"Equipped: {item}", description=clip(lines, 4000) or "Nobody has it equipped.")
        e.set_footer(text=data_as_of(rows, db.get_meta('last_sync_at')))
        await interaction.response.send_message(embed=e)

    # ---- raids ----------------------------------------------------------
    @tree.command(name="raid-create", description="Create a raid (step by step, or fill in everything at once)")
    @app_commands.describe(title="Leave everything blank to be walked through it", date="YYYY-MM-DD",
                           time="HH:MM, 24-hour, in the guild timezone", size="Raid size",
                           tanks="Max tanks (leave blank for no limit)", healers="Max healers (blank = no limit)",
                           dps="Max DPS (blank = no limit)")
    @app_commands.guild_only()
    @officer
    async def raid_create(interaction: discord.Interaction, title: app_commands.Range[str, 1, 100] | None = None,
                          date: str | None = None, time: str | None = None,
                          size: app_commands.Range[int, 1, 40] | None = None,
                          tanks: app_commands.Range[int, 1, 40] | None = None,
                          healers: app_commands.Range[int, 1, 40] | None = None,
                          dps: app_commands.Range[int, 1, 40] | None = None):
        if not (title and date and time and size):
            await interaction.response.send_message(
                "Let's set up a raid. Pick the day, time and size, then tap **Next**.",
                view=RaidWizard(bot, origin=interaction), ephemeral=True)
            return
        try:
            start = R.parse_start(date, time, bot.cfg.timezone)
        except ValueError:
            await interaction.response.send_message(
                "Couldn't read that date/time. Use `2026-11-15` and `20:00`.", ephemeral=True)
            return
        await bot.post_raid(interaction, title, start, size, {"tank": tanks, "healer": healers, "dps": dps})

    @tree.command(name="raid-edit", description="Change a raid's title, time or size")
    @app_commands.describe(date="YYYY-MM-DD (give date and time together)", time="HH:MM, guild timezone",
                           tanks="Max tanks (0 removes the limit)", healers="Max healers (0 removes the limit)",
                           dps="Max DPS (0 removes the limit)")
    @app_commands.guild_only()
    @officer
    async def raid_edit(interaction: discord.Interaction, raid_id: int, title: app_commands.Range[str, 1, 100] | None = None,
                        date: str | None = None, time: str | None = None,
                        size: app_commands.Range[int, 1, 40] | None = None,
                        tanks: app_commands.Range[int, 0, 40] | None = None,
                        healers: app_commands.Range[int, 0, 40] | None = None,
                        dps: app_commands.Range[int, 0, 40] | None = None):
        raid = db.get_raid(raid_id)
        if not raid or raid["status"] != "open":
            await interaction.response.send_message("No open raid with that number.", ephemeral=True)
            return
        if (date is None) != (time is None):
            await interaction.response.send_message("Give the date and the time together.", ephemeral=True)
            return
        start = None
        if date:
            try:
                start = R.parse_start(date, time, bot.cfg.timezone)
            except ValueError:
                await interaction.response.send_message(
                    "Couldn't read that date/time. Use `2026-11-15` and `20:00`.", ephemeral=True)
                return
            if start <= datetime.now(timezone.utc):
                await interaction.response.send_message("That time is in the past.", ephemeral=True)
                return
        caps = {r: n for r, n in (("tank", tanks), ("healer", healers), ("dps", dps)) if n is not None}
        if not (title or start or size or caps):
            await interaction.response.send_message("Nothing to change.", ephemeral=True)
            return
        if size and not caps and R.size_from_limits(raid["cap_tank"], raid["cap_healer"], raid["cap_dps"]):
            await interaction.response.send_message(
                "This raid's size comes from its tank, healer and DPS limits. To add a spot, raise one of them "
                "(for example `dps:4`) and the total updates by itself.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)     # Discord calls below can exceed the 3-second limit
        db.update_raid(raid_id, title, start.isoformat(timespec="seconds") if start else None, size, caps)
        raid = db.get_raid(raid_id)
        note = ""
        try:
            chan = bot.get_channel(raid["channel_id"]) or await bot.fetch_channel(raid["channel_id"])
            msg = await chan.fetch_message(raid["message_id"])
            await msg.edit(embed=raid_embed(db, raid))
            if raid["discord_event_id"]:
                try:
                    ev = await interaction.guild.fetch_scheduled_event(raid["discord_event_id"])
                    new_start = datetime.fromisoformat(raid["starts_at"])
                    await ev.edit(name=raid["title"], start_time=new_start, end_time=new_start + timedelta(hours=3))
                except discord.NotFound:
                    pass                          # event was deleted by hand
        except discord.HTTPException:
            log.exception("could not refresh edited raid %s", raid_id)
            note = " Saved, but I couldn't refresh the post or event."
        if caps:
            note += " Lower limits don't remove anyone already signed up; they only block new signups."
        await interaction.followup.send(f"Raid #{raid_id} updated.{note}", ephemeral=True)
        await bot.fill_open_slots(raid_id)             # more room? ask the bench

    @tree.command(name="raid-cancel", description="Cancel a raid: removes the post and event and tells everyone signed up")
    @app_commands.guild_only()
    @officer
    async def raid_cancel(interaction: discord.Interaction, raid_id: int):
        with bot.busy(raid_id):
            await cancel_raid_flow(interaction, raid_id)

    @tree.command(name="raid-end", description="End a raid now: marks the post completed, unpins it and sends the roster to you")
    @app_commands.guild_only()
    @officer
    async def raid_end(interaction: discord.Interaction, raid_id: int):
        raid = db.get_raid(raid_id)
        if not raid or raid["status"] not in ("open", "closed"):
            await interaction.response.send_message("No running or open raid with that number.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        who = [interaction.user.id, raid["created_by"]]
        await bot.finish_raid(raid_id, remove_event=True, dm_ids=who, note="You ended the raid.")
        await interaction.followup.send(f"Raid #{raid_id} ended. The post stays as the record (unpinned); the roster is in your DMs.",
                                        ephemeral=True)

    async def cancel_raid_flow(interaction: discord.Interaction, raid_id: int):
        raid = db.get_raid(raid_id)
        if not raid or raid["status"] != "open":
            await interaction.response.send_message("No open raid with that number.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)     # Discord calls below can exceed the 3-second limit
        # Tidy Discord first and cancel only once that worked, so a failure can be retried by running
        # /raid-cancel again. The event goes first: if it fails, the post is untouched and still
        # matches the open raid. A message or event that is already gone counts as tidy.
        try:
            if raid["discord_event_id"]:
                ev = await interaction.guild.fetch_scheduled_event(raid["discord_event_id"])
                await ev.delete()
        except discord.NotFound:
            pass                                  # already gone
        except discord.HTTPException:
            log.exception("could not delete the event for raid %s", raid_id)
            await interaction.followup.send(
                f"Couldn't remove the Discord event, so #{raid_id} is not cancelled yet. Try again.",
                ephemeral=True)
            return
        chan = None
        try:
            if raid["channel_id"] and raid["message_id"]:
                chan = bot.get_channel(raid["channel_id"]) or await bot.fetch_channel(raid["channel_id"])
                msg = await chan.fetch_message(raid["message_id"])
                await msg.delete()                      # the signup post goes away entirely
        except discord.NotFound:
            pass
        except discord.HTTPException:
            log.exception("could not delete the post for raid %s", raid_id)
            await interaction.followup.send(
                f"Couldn't remove the raid post, so #{raid_id} is not cancelled yet. Try again.", ephemeral=True)
            return
        who = [s["discord_id"] for s in db.signups(raid_id) if s["role"] != "absent"]   # everyone involved
        db.cancel_raid(raid_id)                         # the row stays, marked cancelled, as a record
        notice = R.cancel_notice(raid, interaction.user.id)
        told, blocked = 0, []
        for uid in dict.fromkeys(who):
            if uid == interaction.user.id:
                continue                                # the officer who cancelled it already knows
            try:
                user = bot.get_user(uid) or await bot.fetch_user(uid)
                if user.bot:
                    continue
                await user.send(notice)
                told += 1
            except discord.HTTPException:               # DMs closed, or the account is gone
                blocked.append(uid)
        msg = f"Raid #{raid_id} cancelled. The post and event are gone; {told} player(s) were messaged privately."
        if blocked:
            msg += " Couldn't message (their DMs are closed): " + " ".join(f"<@{u}>" for u in blocked)
        await interaction.followup.send(msg, ephemeral=True, allowed_mentions=discord.AllowedMentions.none())

    @tree.command(name="raids", description="List upcoming raids")
    @app_commands.guild_only()
    async def raids(interaction: discord.Interaction):
        now = datetime.now(timezone.utc)
        rows = [r for r in db.open_raids() if datetime.fromisoformat(r["starts_at"]) > now]
        lines = []
        for r in rows:
            ts = int(datetime.fromisoformat(r["starts_at"]).timestamp())
            url = f"https://discord.com/channels/{interaction.guild_id}/{r['channel_id']}/{r['message_id']}"
            lines.append(f"#{r['id']} [{r['title']}]({url}) <t:{ts}:F>")
        await interaction.response.send_message("\n".join(lines) or "No upcoming raids.")

    @tree.command(name="guild-sync", description="Refresh guild data from Blizzard now")
    @app_commands.guild_only()
    @officer
    async def sync_cmd(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        res = await bot.run_sync()
        msg = (f"Synced {res.members} members, {res.removed} left the roster, {len(res.failures)} fetch problems."
               f"\n{res.summary()}")
        if res.failures:
            msg += "\n" + "\n".join(f"`{s}` {k}: {e}" for s, k, e in res.failures[:8])
        await interaction.followup.send(msg, ephemeral=True)


    # ---- claiming characters (officers moderate) ----------------------
    @tree.command(name="claim-panel", description="Post the 'claim your characters' button in this channel")
    @app_commands.guild_only()
    @officer
    async def claim_panel(interaction: discord.Interaction):
        await interaction.response.send_message(
            "**Claim your characters.**\nTap the button, pick yours from the list, or type `/link` and a few letters of the name.\nMissing? `/guild-sync` or ask a Moderator.",
            view=ClaimPanel(bot))

    @tree.command(name="claims", description="Who has claimed which characters (officers)")
    @app_commands.guild_only()
    @officer
    async def claims(interaction: discord.Interaction):
        by: dict[int, list[str]] = {}
        for r in db.claims():
            by.setdefault(r["discord_id"], []).append(f"{R.full_name(r)}{'*' if r['is_main'] else ''}")
        lines = [f"<@{d}>: {', '.join(n)}" for d, n in by.items()]
        left = len(db.unclaimed_characters())
        text = clip(lines, 1800) or "No claims yet."
        await interaction.response.send_message(
            f"{text}\n\n{left} character(s) unclaimed. `*` = main.", ephemeral=True,
            allowed_mentions=discord.AllowedMentions.none())

    @tree.command(name="unlink-member", description="Remove every character link a Discord member holds (officers)")
    @app_commands.guild_only()
    @officer
    async def unlink_member(interaction: discord.Interaction, member: discord.Member):
        n = db.unlink_all(member.id)
        await interaction.response.send_message(
            f"Removed {n} link(s) from {member.display_name}. Their characters can be claimed again.",
            ephemeral=True)

    @tree.command(name="release", description="Free a character so its rightful owner can claim it (officers)")
    @app_commands.autocomplete(character=char_ac)
    @app_commands.guild_only()
    @officer
    async def release(interaction: discord.Interaction, character: str):
        row = db.find_character(character)
        if not row:
            await interaction.response.send_message("No such character.", ephemeral=True)
            return
        db.release(row["slug"])
        await interaction.response.send_message(f"**{R.full_name(row)}** is free to claim again.", ephemeral=True)
