"""Discord bot: roster lookups and raid signups."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import tasks

from . import raids as R
from .links import item_link
from .config import Config
from .db import Database, utcnow
from .sync import sync_guild

log = logging.getLogger("guildbot")

BUTTONS = [
    ("tank", "Tank", discord.ButtonStyle.primary),
    ("healer", "Healer", discord.ButtonStyle.success),
    ("dps", "DPS", discord.ButtonStyle.danger),
    ("bench", "Bench", discord.ButtonStyle.secondary),
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
    e = discord.Embed(
        title=f"{'CANCELLED: ' if cancelled else 'STARTED: ' if started else ''}{raid['title']}  (#{raid['id']})",
        description=f"<t:{ts}:F> · <t:{ts}:R>\nSlots filled: **{R.filled(g)}/{raid['size']}**",
        color=discord.Color.dark_grey() if cancelled or started else discord.Color.blurple(),
    )
    for role in R.ROLES:
        lines = [R.format_entry(s) for s in g[role]]
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
            parts.append("Linked: " + ", ".join(f"**{names[s]}**" for s in res["linked"]) + ".")
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
        register_commands(self)

    async def setup_hook(self) -> None:
        self.add_view(ClaimPanel(self))
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

    async def _send_reminders(self) -> None:
        """Private reminder to everyone signed up (slots and bench). Nothing is posted in the channel.
        Anyone whose DMs are closed is reported privately to whoever created the raid."""
        for raid in self.db.due_reminders(datetime.now(timezone.utc), 60):
            try:
                g = R.group_signups(self.db.signups(raid["id"]))
                ids = list(dict.fromkeys(s["discord_id"] for r in (*R.COUNTED, "bench") for s in g[r]))
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
            except discord.NotFound:
                self.db.mark_closed(raid["id"])      # message or channel deleted: nothing left to tidy
            except Exception:
                log.exception("could not remove buttons from started raid %s; will retry", raid["id"])

    # ---- raid signup --------------------------------------------------
    async def handle_signup(self, interaction: discord.Interaction, raid_id: int, role: str) -> None:
        raid = self.db.get_raid(raid_id)
        if not raid or raid["status"] != "open" or \
                datetime.fromisoformat(raid["starts_at"]) <= datetime.now(timezone.utc):
            await interaction.response.send_message("This raid is closed.", ephemeral=True)
            return
        # A signup is a Discord account, a role and (if they have one) a character. With several linked
        # characters the bot asks which one, the first time and whenever they tap the role they already hold.
        chars = self.db.characters_for(interaction.user.id)
        prior = next((s for s in self.db.signups(raid_id) if s["discord_id"] == interaction.user.id), None)
        if len(chars) > 1 and role != "absent" and (prior is None or prior["role"] == role):
            view = SignupCharacterPicker(self, raid_id, role, chars,
                                         current=prior["slug"] if prior else None)
            await interaction.response.send_message(
                f"Which character are you signing up as ({R.ROLE_LABEL[role]})?", view=view, ephemeral=True)
            return
        slugs = {c["slug"] for c in chars}
        main = self.db.main_for(interaction.user.id)
        slug = prior["slug"] if prior and prior["slug"] in slugs else (main["slug"] if main else None)
        landed = self.apply_signup(raid, interaction.user.id, role, slug)
        await interaction.response.edit_message(embed=raid_embed(self.db, raid))
        if landed != role:
            where = "the bench" if landed == "bench" else f"{R.ROLE_LABEL[landed].lower()}"
            await interaction.followup.send(
                f"{R.ROLE_LABEL.get(role, role)} (or the raid) is full, so you're on {where}.", ephemeral=True)

    def apply_signup(self, raid, discord_id: int, role: str, slug) -> str:
        """Record the signup; returns the role they actually landed in (bench when full)."""
        landed = R.resolve_role(role, R.group_signups(self.db.signups(raid["id"])), raid["size"],
                                discord_id, R.caps_of(raid))
        self.db.upsert_signup(raid["id"], discord_id, slug, landed, utcnow())
        return landed


class SignupCharacterPicker(discord.ui.View):
    """Private 'which of your characters?' list shown when someone with several links signs up."""

    def __init__(self, bot: GuildBot, raid_id: int, role: str, chars, current=None):
        super().__init__(timeout=300)
        self.bot, self.raid_id, self.role = bot, raid_id, role
        pre = current or next((c["slug"] for c in chars if c["is_main"]), chars[0]["slug"])
        sel = discord.ui.Select(
            placeholder="Pick a character",
            options=[discord.SelectOption(label=char_label(c), value=c["slug"], default=(c["slug"] == pre))
                     for c in chars[:25]])
        sel.callback = self._picked
        self.add_item(sel)

    async def _picked(self, interaction: discord.Interaction) -> None:
        bot, db = self.bot, self.bot.db
        raid = db.get_raid(self.raid_id)
        if not raid or raid["status"] != "open" or \
                datetime.fromisoformat(raid["starts_at"]) <= datetime.now(timezone.utc):
            await interaction.response.edit_message(content="This raid is closed.", view=None)
            return
        slug = interaction.data["values"][0]
        if slug not in {c["slug"] for c in db.characters_for(interaction.user.id)}:
            await interaction.response.edit_message(content="That character isn't linked to you.", view=None)
            return
        landed = bot.apply_signup(raid, interaction.user.id, self.role, slug)
        row = db.find_character(slug)
        note = f"Signed up as **{R.full_name(row)}**: {R.ROLE_LABEL[landed]}."
        if landed != self.role:
            note += f" ({R.ROLE_LABEL[self.role]} is full, so you're on the bench.)"
        await interaction.response.edit_message(content=note, view=None)
        try:
            chan = bot.get_channel(raid["channel_id"]) or await bot.fetch_channel(raid["channel_id"])
            msg = await chan.fetch_message(raid["message_id"])
            await msg.edit(embed=raid_embed(db, raid))
        except discord.HTTPException:
            log.exception("could not refresh the post for raid %s", self.raid_id)


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

    @tree.command(name="professions", description="Who has which profession (leave blank for all)")
    async def professions(interaction: discord.Interaction, profession: str = ""):
        rows = db.who_has_profession(profession)
        by: dict[str, list[str]] = {}
        for r in rows:
            by.setdefault(r["profession"], []).append(f"{R.full_name(r)} {r['skill']}/{r['max_skill']}")
        lines = [f"**{p}** ({len(v)}): {', '.join(v)}" for p, v in sorted(by.items())]
        e = discord.Embed(title="Professions", description=clip(lines, 4000) or "Nobody found.")
        e.set_footer(text=data_as_of(rows, db.get_meta('last_sync_at')))
        await interaction.response.send_message(embed=e)

    @tree.command(name="whohas", description="Who has an item equipped")
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

    @tree.command(name="raid-cancel", description="Cancel a raid: removes the post and event and tells everyone signed up")
    @app_commands.guild_only()
    @officer
    async def raid_cancel(interaction: discord.Interaction, raid_id: int):
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
