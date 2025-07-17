from __future__ import annotations

import asyncio
import logging
import os
import re
import json
import unicodedata
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

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
SHORT_RE = re.compile(r"https?://(?:bit\.ly|t\.co|tinyurl\.com|goo\.gl|is\.gd|ow\.ly|buff\.ly|cutt\.ly|rb\.gy|v\.gd|shrtco\.de|git\.io|lnk\.fi|rebrand\.ly)/[^\s <>]{2,}", re.I)

class AntiRaid(commands.Cog):
    antiraid = app_commands.Group(name="antiraid", description="Anti-Raid 設定")

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.msg_times = load_json(MSG_TIMES_FILE)
        self.guild_cfg = load_json(GUILD_CFG_FILE)
        self.punished = load_json(PUNISHED_FILE)
        self.punish_locks = {}
        self.cleanup.start()

    def cfg(self, gid: int) -> dict[str, int]:
        gid_str = str(gid)
        if gid_str not in self.guild_cfg:
            self.guild_cfg[gid_str] = DEFAULTS.copy()
            save_json(GUILD_CFG_FILE, self.guild_cfg)
        return self.guild_cfg[gid_str]

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

        now = datetime.utcnow().isoformat()
        uid = str(m.author.id)

        if uid not in self.msg_times:
            self.msg_times[uid] = []
        self.msg_times[uid] = [t for t in self.msg_times[uid] if (datetime.fromisoformat(now) - datetime.fromisoformat(t)).total_seconds() < cfg["spam_interval"]]
        self.msg_times[uid].append(now)
        save_json(MSG_TIMES_FILE, self.msg_times)

        if len(self.msg_times[uid]) >= cfg["spam_count"]:
            await self._queue_punish(m, "連投スパム", cfg)

    async def _queue_punish(self, msg: discord.Message, reason: str, cfg: dict):
        uid = str(msg.author.id)
        gid = str(msg.guild.id)
        if gid not in self.punished:
            self.punished[gid] = {}
        if uid in self.punished[gid]:
            return

        lock = self.punish_locks.setdefault(uid, asyncio.Lock())
        async with lock:
            self.punished[gid][uid] = datetime.utcnow().isoformat()
            save_json(PUNISHED_FILE, self.punished)
            await self._punish(msg, reason)

    async def _punish(self, msg: discord.Message, reason: str):
        now = discord.utils.utcnow()
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
            description=f"{msg.author.mention} を **1時間タイムアウト** しました
理由 : **{reason}**",
            color=0xFF5555,
        )
        await msg.channel.send(embed=embed)

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
        save_json(PUNISHED_FILE, self.punished)

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
        save_json(GUILD_CFG_FILE, self.guild_cfg)
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
