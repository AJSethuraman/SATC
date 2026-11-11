"""Discord bot: roster lookups and raid signups."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import tasks

from . import raids as R
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
    return f"{r['name']} {r['surname'] or ''} · L{r['level'] or '?'} {r['class_name'] or ''}".replace("  ", " ").strip()[:100]


class ClaimPicker(discord.ui.View):
    """Private (ephemeral) dropdown of unclaimed characters, paged 25 at a time."""

    def __init__(self, bot: "GuildBot", page: int = 0):
        super().__init__(timeout=300)
        self.bot = bot
        rows = bot.db.unclaimed_characters()
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

    async def _next(self, interaction: discord.Interaction) -> None:
        view = ClaimPicker(self.bot, (self.page + 1) % self._pages)
        await interaction.response.edit_message(content=view.header(), view=view)

    def header(self) -> str:
        n = len(self.bot.db.unclaimed_characters())
        return (f"Pick yours from the list ({n} unclaimed)." if n
                else "Every character is already claimed. Ask an officer if one is wrong.")

    async def _picked(self, interaction: discord.Interaction) -> None:
        res = self.bot.db.claim(interaction.user.id, interaction.data["values"])
        names = {r["slug"]: r["name"] for r in self.bot.db.roster()}
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


class ClaimPanel(discord.ui.View):
    """The public 'claim your characters' button. Persistent across restarts."""

    def __init__(self, bot: "GuildBot"):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Claim my characters", style=discord.ButtonStyle.primary, custom_id="claim:open")
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        view = ClaimPicker(self.bot)
        await interaction.response.send_message(view.header(), view=view, ephemeral=True)


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
        for raid in self.db.due_reminders(datetime.now(timezone.utc), 60):
            try:
                chan = self.get_channel(raid["channel_id"]) or await self.fetch_channel(raid["channel_id"])
                g = R.group_signups(self.db.signups(raid["id"]))
                pings = " ".join(f"<@{s['discord_id']}>" for r in R.COUNTED for s in g[r])
                ts = int(datetime.fromisoformat(raid["starts_at"]).timestamp())
                await chan.send(f"Reminder: **{raid['title']}** starts <t:{ts}:R>. {pings}".strip())
                self.db.mark_reminded(raid["id"])
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
        # A signup is a Discord account plus a role. A linked main is shown if there is one; none is needed.
        main = self.db.main_for(interaction.user.id)
        landed = R.resolve_role(role, R.group_signups(self.db.signups(raid_id)), raid["size"],
                               interaction.user.id, R.caps_of(raid))
        self.db.upsert_signup(raid_id, interaction.user.id, main["slug"] if main else None, landed, utcnow())
        await interaction.response.edit_message(embed=raid_embed(self.db, raid))
        if landed != role:
            where = "the bench" if landed == "bench" else f"{R.ROLE_LABEL[landed].lower()}"
            await interaction.followup.send(
                f"{R.ROLE_LABEL.get(role, role)} (or the raid) is full, so you're on {where}.", ephemeral=True)


def register_commands(bot: GuildBot) -> None:
    tree, db = bot.tree, bot.db
    officer = app_commands.checks.has_permissions(manage_events=True)

    async def char_ac(interaction: discord.Interaction, current: str):
        return [app_commands.Choice(
                    name=f"{r['name']} (L{r['level'] or '?'} {r['class_name'] or ''})".strip()[:100],
                    value=r["slug"])
                for r in db.search_characters(current)]

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
    @tree.command(name="link", description="Link one of your in-game characters to your Discord account")
    @app_commands.autocomplete(character=char_ac)
    @app_commands.guild_only()
    async def link(interaction: discord.Interaction, character: str):
        row = db.find_character(character)
        if not row:
            await interaction.response.send_message(
                f"No guild member found for `{character}`. Roster last synced {rel(db.get_meta('last_sync_at'))}.",
                ephemeral=True)
            return
        owner = db.owner_of(row["slug"])
        if owner and owner != interaction.user.id:
            if not interaction.permissions.manage_events:
                await interaction.response.send_message(
                    f"**{row['name']}** is already linked to <@{owner}>. Ask an officer to fix it.",
                    ephemeral=True)
                return
            db.release(row["slug"])
        became_main = db.link(interaction.user.id, row["slug"])
        await interaction.response.send_message(
            f"Linked **{row['name']}**" + (" as your main." if became_main else ". Use `/main` to make it your main."),
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
            f"**{row['name']}** is now your main." if ok else "Link that character first with `/link`.",
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
            e = discord.Embed(title=f"{r['name']}" + (f" {r['surname']}" if r["surname"] else ""),
                              description=f"L{r['level'] or '?'} {r['race_name'] or ''} {r['class_name'] or ''}".strip())
            profs = db.professions_for(r["slug"])
            e.add_field(name="Professions",
                        value="\n".join(f"{p['profession']} {p['skill']}/{p['max_skill']}" for p in profs) or "—")
            gear = db.equipment_for(r["slug"])
            e.add_field(name="Gear", value=clip([f"{g['slot']}: {g['item_name']}" for g in gear], 1024) or "—",
                        inline=False)
            e.set_footer(text=who_footer(r, profs, gear))
            embeds.append(e)
        await interaction.response.send_message(embeds=embeds)

    @tree.command(name="roster", description="List guild characters")
    async def roster(interaction: discord.Interaction, class_name: str | None = None,
                     min_level: int | None = None):
        rows = db.roster(class_name, min_level)
        lines = [f"**{r['name']}**: L{r['level'] or '?'} {r['class_name'] or ''}" for r in rows]
        e = discord.Embed(title=f"Roster ({len(rows)})", description=clip(lines, 4000) or "Nobody found.")
        e.set_footer(text=data_as_of(rows, db.get_meta('last_sync_at'), key="profile_at"))
        await interaction.response.send_message(embed=e)

    @tree.command(name="professions", description="Who has which profession (leave blank for all)")
    async def professions(interaction: discord.Interaction, profession: str = ""):
        rows = db.who_has_profession(profession)
        by: dict[str, list[str]] = {}
        for r in rows:
            by.setdefault(r["profession"], []).append(f"{r['name']} {r['skill']}/{r['max_skill']}")
        lines = [f"**{p}** ({len(v)}): {', '.join(v)}" for p, v in sorted(by.items())]
        e = discord.Embed(title="Professions", description=clip(lines, 4000) or "Nobody found.")
        e.set_footer(text=data_as_of(rows, db.get_meta('last_sync_at')))
        await interaction.response.send_message(embed=e)

    @tree.command(name="whohas", description="Who has an item equipped")
    async def whohas(interaction: discord.Interaction, item: str):
        rows = db.search_items(item)
        lines = [f"**{r['name']}**: {r['item_name']} ({r['slot']})" for r in rows]
        e = discord.Embed(title=f"Equipped: {item}", description=clip(lines, 4000) or "Nobody has it equipped.")
        e.set_footer(text=data_as_of(rows, db.get_meta('last_sync_at')))
        await interaction.response.send_message(embed=e)

    # ---- raids ----------------------------------------------------------
    @tree.command(name="raid-create", description="Create a raid with signup buttons")
    @app_commands.describe(date="YYYY-MM-DD", time="HH:MM, 24-hour, in the guild timezone", size="Raid size",
                           tanks="Max tanks (leave blank for no limit)", healers="Max healers (blank = no limit)",
                           dps="Max DPS (blank = no limit)")
    @app_commands.guild_only()
    @officer
    async def raid_create(interaction: discord.Interaction, title: app_commands.Range[str, 1, 100], date: str, time: str,
                          size: app_commands.Range[int, 1, 40],
                          tanks: app_commands.Range[int, 1, 40] | None = None,
                          healers: app_commands.Range[int, 1, 40] | None = None,
                          dps: app_commands.Range[int, 1, 40] | None = None):
        try:
            start = R.parse_start(date, time, bot.cfg.timezone)
        except ValueError:
            await interaction.response.send_message(
                "Couldn't read that date/time. Use `2026-11-15` and `20:00`.", ephemeral=True)
            return
        if start <= datetime.now(timezone.utc):
            await interaction.response.send_message("That time is in the past.", ephemeral=True)
            return
        raid_id = db.create_raid(title, start.isoformat(timespec="seconds"), size, interaction.user.id,
                                 {"tank": tanks, "healer": healers, "dps": dps})
        raid = db.get_raid(raid_id)
        try:
            await interaction.response.send_message(embed=raid_embed(db, raid), view=RaidView(bot, raid_id))
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

    @tree.command(name="raid-cancel", description="Cancel a raid")
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
        cancelled = dict(raid) | {"status": "cancelled"}
        try:
            if raid["channel_id"] and raid["message_id"]:
                chan = bot.get_channel(raid["channel_id"]) or await bot.fetch_channel(raid["channel_id"])
                msg = await chan.fetch_message(raid["message_id"])
                await msg.edit(embed=raid_embed(db, cancelled), view=None)
        except discord.NotFound:
            pass
        except discord.HTTPException:
            log.exception("could not update the post for raid %s", raid_id)
            await interaction.followup.send(
                f"Couldn't update the raid post, so #{raid_id} is not cancelled yet. Try again.", ephemeral=True)
            return
        db.cancel_raid(raid_id)
        await interaction.followup.send(f"Raid #{raid_id} cancelled.", ephemeral=True)

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
            "**Claim your characters.** Tap the button, pick yours from the list (only you see it).",
            view=ClaimPanel(bot))

    @tree.command(name="claims", description="Who has claimed which characters (officers)")
    @app_commands.guild_only()
    @officer
    async def claims(interaction: discord.Interaction):
        by: dict[int, list[str]] = {}
        for r in db.claims():
            by.setdefault(r["discord_id"], []).append(f"{r['name']}{'*' if r['is_main'] else ''}")
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
        await interaction.response.send_message(f"**{row['name']}** is free to claim again.", ephemeral=True)
