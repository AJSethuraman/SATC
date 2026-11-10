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


def data_as_of(rows, fallback: str | None) -> str:
    """Footer for lists built from per-row fetch times: the oldest row shown, so stale data is not
    presented as fresh just because a later sync ran."""
    times = [r["fetched_at"] for r in rows if r["fetched_at"]]
    return f"Data as of {min(times) if times else (fallback or 'never')} UTC (oldest shown)"


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


class GuildBot(discord.Client):
    def __init__(self, cfg: Config, db: Database, blizzard):
        super().__init__(intents=discord.Intents.default())
        self.cfg, self.db, self.blizzard = cfg, db, blizzard
        self.tree = app_commands.CommandTree(self)
        self._sync_lock = asyncio.Lock()
        register_commands(self)

    async def setup_hook(self) -> None:
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
            e.set_footer(text=f"Profile fetched {r['profile_at'] or 'never'} UTC")
            embeds.append(e)
        await interaction.response.send_message(embeds=embeds)

    @tree.command(name="roster", description="List guild characters")
    async def roster(interaction: discord.Interaction, class_name: str | None = None,
                     min_level: int | None = None):
        rows = db.roster(class_name, min_level)
        lines = [f"**{r['name']}**: L{r['level'] or '?'} {r['class_name'] or ''}" for r in rows]
        e = discord.Embed(title=f"Roster ({len(rows)})", description=clip(lines, 4000) or "Nobody found.")
        e.set_footer(text=f"Synced {db.get_meta('last_sync_at') or 'never'} UTC")
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
    async def raid_create(interaction: discord.Interaction, title: str, date: str, time: str,
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
            db.delete_raid(raid_id)      # never posted: don't leave a raid with no message behind
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
    async def raid_edit(interaction: discord.Interaction, raid_id: int, title: str | None = None,
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
        db.update_raid(raid_id, title, start.isoformat(timespec="seconds") if start else None, size, caps)
        raid = db.get_raid(raid_id)
        note = ""
        try:
            chan = bot.get_channel(raid["channel_id"]) or await bot.fetch_channel(raid["channel_id"])
            msg = await chan.fetch_message(raid["message_id"])
            await msg.edit(embed=raid_embed(db, raid))
            ev = interaction.guild.get_scheduled_event(raid["discord_event_id"]) if raid["discord_event_id"] else None
            if ev:
                new_start = datetime.fromisoformat(raid["starts_at"])
                await ev.edit(name=raid["title"], start_time=new_start, end_time=new_start + timedelta(hours=3))
        except discord.HTTPException:
            log.exception("could not refresh edited raid %s", raid_id)
            note = " Saved, but I couldn't refresh the post or event."
        if caps:
            note += " Lower limits don't remove anyone already signed up; they only block new signups."
        await interaction.response.send_message(f"Raid #{raid_id} updated.{note}", ephemeral=True)

    @tree.command(name="raid-cancel", description="Cancel a raid")
    @app_commands.guild_only()
    @officer
    async def raid_cancel(interaction: discord.Interaction, raid_id: int):
        raid = db.get_raid(raid_id)
        if not raid or raid["status"] != "open":
            await interaction.response.send_message("No open raid with that number.", ephemeral=True)
            return
        # Tidy Discord first and cancel only once that worked, so a failure can be retried by running
        # /raid-cancel again. The event goes first: if it fails, the post is untouched and still
        # matches the open raid. A message or event that is already gone counts as tidy.
        try:
            if raid["discord_event_id"]:
                ev = interaction.guild.get_scheduled_event(raid["discord_event_id"])
                if ev:
                    await ev.delete()
        except discord.NotFound:
            pass
        except discord.HTTPException:
            log.exception("could not delete the event for raid %s", raid_id)
            await interaction.response.send_message(
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
            await interaction.response.send_message(
                f"Couldn't update the raid post, so #{raid_id} is not cancelled yet. Try again.", ephemeral=True)
            return
        db.cancel_raid(raid_id)
        await interaction.response.send_message(f"Raid #{raid_id} cancelled.", ephemeral=True)

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

    @tree.command(name="sync", description="Refresh guild data from Blizzard now")
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
