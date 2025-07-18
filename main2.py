from __future__ import annotations

import asyncio
import os
import re
import json
import unicodedata
from pathlib import Path
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("DISCORD_TOKEN") or "YOUR_TOKEN_HERE"
MSG_TIMES_FILE = Path("msg_times.json")
GUILD_CFG_FILE = Path("guild_cfg.json")
PUNISHED_FILE = Path("punished.json")

DEFAULTS: dict[str, int] = {
    "spam_interval": 5,
    "spam_count": 6,
    "raid_window": 15,
    "raid_count": 6,
    "mention_limit": 6,
}

# ─────────────── JSON ヘルパー ───────────────
def load_json(path: Path, default: dict = {}) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 読み込み失敗 {path.name}: {e}")
    return default.copy()

def save_json(path: Path, data: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ 保存失敗 {path.name}: {e}")

def clean_text(text: str) -> str:
    invisible_chars = ["​", "‌", "‍", "﻿", "⁠", "᠎"]
    for ch in invisible_chars:
        text = text.replace(ch, "")
    return unicodedata.normalize("NFKC", text).lower()

INVITE_RE = re.compile(r"https?://(?:www\.)?discord(?:\.gg|\.com/invite)/[0-9A-Za-z-]{3,}", re.I)
SHORT_RE = re.compile(
    r"https?://(?:bit\.ly|t\.co|tinyurl\.com|goo\.gl|is\.gd|ow\.ly|buff\.ly|cutt\.ly|rb\.gy|v\.gd|shrtco\.de|git\.io|lnk\.fi|rebrand\.ly)/[^\s <>]{2,}",
    re.I
)

# ─────────────── ActionView ───────────────
class ModActionView(discord.ui.View):
    def __init__(self, member: discord.Member, *, timeout=300):
        super().__init__(timeout=timeout)
        self.member = member

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.guild_permissions.kick_members and not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("❌ 権限がありません", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger)
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.member.kick(reason=f"Manual kick by {interaction.user}")
            await interaction.response.send_message(f"✅ {self.member.mention} をKickしました", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Kickに失敗しました（権限不足）", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="タイムアウト解除", style=discord.ButtonStyle.secondary)
    async def untimeout_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self.member.timeout(None, reason=f"Untimeout by {interaction.user}")
            await interaction.response.send_message(f"✅ {self.member.mention} のタイムアウトを解除しました", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ 解除に失敗しました（権限不足）", ephemeral=True)
        self.disable_all_items()
        await interaction.message.edit(view=self)

# ─────────────── Cog: AntiRaid ───────────────
class AntiRaid(commands.Cog):
    antiraid = app_commands.Group(name="antiraid", description="Anti-Raid 設定")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.msg_times = load_json(MSG_TIMES_FILE)
        self.guild_cfg = load_json(GUILD_CFG_FILE)
        self.punished = load_json(PUNISHED_FILE)
        self.punish_locks = {}
        self.json_lock = asyncio.Lock()
        self.cleanup.start()

        # Nuke対策用トラッカー
        self.audit_tracker = {}      # {user_id: [timestamps]} 削除・作成
        self.ban_kick_tracker = {}   # {user_id: [timestamps]} BAN/KICK

    def cfg(self, gid: int) -> dict[str, int]:
        gid_str = str(gid)
        if gid_str not in self.guild_cfg:
            self.guild_cfg[gid_str] = DEFAULTS.copy()
            save_json(GUILD_CFG_FILE, self.guild_cfg)
        return self.guild_cfg[gid_str]

    async def save_json_async(self, path: Path, data: dict):
        async with self.json_lock:
            save_json(path, data)

    async def _send_alert(self, guild: discord.Guild, title: str, description: str, color=0xFF5555):
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        channel = discord.utils.get(guild.text_channels, name="mod-log")
        if not channel and guild.text_channels:
            channel = guild.text_channels[0]
        if channel:
            try:
                await channel.send(embed=embed)
            except Exception:
                pass

    # ─────────────── メッセージ監視 ───────────────
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if m.author.bot or not m.guild:
            return

        cfg = self.cfg(m.guild.id)
        clean = clean_text(m.content)

        if INVITE_RE.search(clean) or SHORT_RE.search(clean):
            return await self._queue_punish(m, "不審リンク", cfg)

        if len(m.mentions) >= cfg["mention_limit"]:
            return await self._queue_punish(m, "大量メンション", cfg)

        gid = str(m.guild.id)
        uid = str(m.author.id)
        now = datetime.utcnow().isoformat()

        if gid not in self.msg_times:
            self.msg_times[gid] = {}
        if uid not in self.msg_times[gid]:
            self.msg_times[gid][uid] = []

        self.msg_times[gid][uid] = [
            t for t in self.msg_times[gid][uid]
            if (datetime.fromisoformat(now) - datetime.fromisoformat(t)).total_seconds() < cfg["spam_interval"]
        ]
        self.msg_times[gid][uid].append(now)

        await self.save_json_async(MSG_TIMES_FILE, self.msg_times)

        if len(self.msg_times[gid][uid]) >= cfg["spam_count"]:
            await self._queue_punish(m, "連投スパム", cfg)

    async def _queue_punish(self, msg: discord.Message, reason: str, cfg: dict):
        gid = str(msg.guild.id)
        uid = str(msg.author.id)

        if gid not in self.punished:
            self.punished[gid] = {}
        if uid in self.punished[gid]:
            return

        lock = self.punish_locks.setdefault(uid, asyncio.Lock())
        async with lock:
            self.punished[gid][uid] = datetime.utcnow().isoformat()
            await self.save_json_async(PUNISHED_FILE, self.punished)
            await self._punish(msg, reason)

    async def _punish(self, msg: discord.Message, reason: str):
        now = datetime.now(timezone.utc)
        try:
            await msg.delete()
        except discord.HTTPException:
            pass
        try:
            await msg.author.timeout(now + timedelta(hours=1), reason=f"AntiRaid: {reason}")
        except discord.Forbidden:
            return

        embed = discord.Embed(
            title="🚨 自動モデレーション発動",
            description=f"{msg.author.mention} を **1時間タイムアウト** しました\n理由 : **{reason}**",
            color=0xFF5555,
        )
        view = ModActionView(msg.author)
        await msg.channel.send(embed=embed, view=view)
        await self._send_alert(msg.guild, "🚨 自動モデレーション", f"{msg.author.mention} をタイムアウトしました。\n理由: {reason}")

    # ─────────────── Nuke対策 ───────────────
    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry):
        if not entry.user or entry.user.bot:
            return

        now = datetime.utcnow()

        # チャンネル作成/削除 & ロール削除
        if entry.action in (
            discord.AuditLogAction.channel_create,
            discord.AuditLogAction.channel_delete,
            discord.AuditLogAction.role_delete
        ):
            self._track_action(self.audit_tracker, entry.user.id, now)
            if len(self.audit_tracker[entry.user.id]) >= 5:
                await self._punish_audit(entry.guild, entry.user, "短時間に5回以上のチャンネル作成/削除/ロール削除（Nuke疑惑）")

        # BAN/KICK
        if entry.action in (discord.AuditLogAction.kick, discord.AuditLogAction.ban):
            self._track_action(self.ban_kick_tracker, entry.user.id, now)
            if len(self.ban_kick_tracker[entry.user.id]) >= 5:
                await self._punish_audit(entry.guild, entry.user, "短時間に5回以上のBAN/KICK（Nuke疑惑）")

    def _track_action(self, tracker: dict, user_id: int, now: datetime):
        if user_id not in tracker:
            tracker[user_id] = []
        tracker[user_id] = [t for t in tracker[user_id] if (now - t).total_seconds() < 10]
        tracker[user_id].append(now)

    async def _punish_audit(self, guild: discord.Guild, user: discord.User, reason: str):
        member = guild.get_member(user.id)
        if not member:
            return
        try:
            await member.timeout(datetime.now(timezone.utc) + timedelta(hours=1), reason=reason)
            await self._send_alert(
                guild,
                "🚨 Nuke対策発動",
                f"{member.mention} を **1時間タイムアウト** しました。\n理由: **{reason}**"
            )
        except discord.Forbidden:
            await self._send_alert(
                guild,
                "⚠️ Nuke疑惑",
                f"{member.mention} に対するタイムアウトに失敗しました（権限不足）\n理由: **{reason}**"
            )

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.abc.GuildChannel):
        try:
            webhooks = await channel.webhooks()
            for webhook in webhooks:
                if webhook.user and not webhook.user.guild_permissions.manage_webhooks:
                    await webhook.delete(reason="不審Webhook削除")
                    await self._send_alert(
                        channel.guild,
                        "⚠️ 不審Webhook削除",
                        f"ユーザー `{webhook.user}` が作成した不審Webhookを削除しました。"
                    )
        except discord.Forbidden:
            pass

    @tasks.loop(minutes=5)
    async def cleanup(self):
        now = datetime.utcnow()
        expired = {}
        for gid, users in self.punished.items():
            expired[gid] = {
                uid: ts for uid, ts in users.items()
                if (now - datetime.fromisoformat(ts)).total_seconds() < 300
            }
        self.punished = expired
        await self.save_json_async(PUNISHED_FILE, self.punished)

    @cleanup.before_loop
    async def before_cleanup(self):
        await self.bot.wait_until_ready()

    @antiraid.command(name="stats", description="現在の自動対処条件を確認します")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def stats(self, itx: discord.Interaction):
        cfg = self.cfg(itx.guild_id)
        await itx.response.send_message(
            "\n".join(f"**{k}**: {v}" for k, v in cfg.items()),
            ephemeral=True,
        )

    @antiraid.command(name="set", description="しきい値を変更します")
    @app_commands.describe(key="項目名（例: spam_count）", value="新しい数値（例: 5）")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_cfg(self, itx: discord.Interaction, key: str, value: int):
        if key not in DEFAULTS:
            return await itx.response.send_message("❌ 無効な項目です", ephemeral=True)

        gid = str(itx.guild_id)
        if gid not in self.guild_cfg:
            self.guild_cfg[gid] = DEFAULTS.copy()

        self.guild_cfg[gid][key] = value
        await self.save_json_async(GUILD_CFG_FILE, self.guild_cfg)
        await itx.response.send_message(f"✅ `{key}` を **{value}** に更新しました", ephemeral=True)

# ─────────────── Bot起動 ───────────────
async def main():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.messages = True
    intents.members = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        print(f"✅ Logged in: {bot.user} ({bot.user.id})")
        try:
            synced = await bot.tree.sync()
            print(f"🔁 コマンド同期済: {len(synced)} 件")
        except Exception as e:
            print(f"⚠️ コマンド同期失敗: {e}")

    await bot.add_cog(AntiRaid(bot))
    await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
