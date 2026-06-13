import discord
from discord.ext import commands, tasks
from discord import app_commands
import chat_exporter
import io
import os
from flask import Flask
from threading import Thread
from datetime import datetime, timedelta
import json
import gc
import random
from groq import Groq
import requests
import time
import asyncio
gc.set_threshold(700, 10, 10)

# --- KEEP RENDER ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT SETUP WITH INTENTS ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIG ---
TICKET_CATEGORY_ID = 1513372898058833981
STAFF_ROLE_NAME = "Staff"
LOG_CHANNEL_ID = 1513387589514694747
CONFIG_FILE = "config.json"
LEVELS_FILE = "levels.json"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
AI_CHANNEL_ID = 1514982328584241316
CONFESS_CHANNEL = 1514982328584241316
LEVEL_ROLES = {
    5: 1485818597870796840,
    10: 1485817312098385950,
    20: 1485817682682183731,
    50: 1485817752965877790
}
STATS_GUILD_ID = 1465300538491932869
STATS_MEMBER_CHANNEL = 1514982328584241317
STATS_BOT_CHANNEL = 1514982328584241318
BANNED_WORDS = ["badword1", "slur2"]
INVITE_WHITELIST = []

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# --- CONFIG HANDLERS ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_guild_config(guild_id):
    config = load_config()
    return config.get(str(guild_id), {
        "welcome_channel": None,
        "auto_role": None
    })

def set_guild_config(guild_id, key, value):
    config = load_config()
    guild_id = str(guild_id)
    if guild_id not in config:
        config[guild_id] = {}
    config[guild_id][key] = value
    save_config(config)

# --- LEVEL SYSTEM ---
def load_levels():
    if os.path.exists(LEVELS_FILE):
        with open(LEVELS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_levels(data):
    with open(LEVELS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_xp_for_level(level):
    return 5 * (level ** 2) + 50 * level + 100

def get_level_from_xp(xp):
    level = 0
    while xp >= get_xp_for_level(level):
        xp -= get_xp_for_level(level)
        level += 1
    return level

# --- TICKET PANEL VIEW - RUNCANDELS ---
class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket_channel(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        user = interaction.user

        existing_ticket = discord.utils.get(guild.text_channels, name=f"{ticket_type.lower()}-{user.name.lower()}")
        if existing_ticket:
            await interaction.response.send_message(f"You already have an open {ticket_type} ticket: {existing_ticket.mention}", ephemeral=True)
            return

        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            await interaction.response.send_message("Ticket category not found. Contact an admin.", ephemeral=True)
            return

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"{ticket_type.lower()}-{user.name}",
            category=category,
            overwrites=overwrites,
            topic=f"{ticket_type} ticket for {user.id}"
        )

        embed = discord.Embed(
            title=f"🎫 {ticket_type} Ticket",
            description=f"Hey {user.mention}, thanks for contacting RUNCANDELS Support!\n\nPlease describe your issue in detail. A staff member will assist you shortly.",
            color=discord.Color.blue()
        )
        embed.add_field(name="Close ticket", value="Click the 🔒 button below when your issue is resolved.", inline=False)
        embed.set_footer(text=f"User ID: {user.id}")

        ping_content = f"{user.mention}"
        if staff_role:
            ping_content += f" {staff_role.mention}"

        await channel.send(content=ping_content, embed=embed, view=CloseTicket())
        await interaction.response.send_message(f"Your {ticket_type} ticket has been created: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="General Support", style=discord.ButtonStyle.blurple, custom_id="general_support", emoji="🛠️")
    async def general_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket_channel(interaction, "General")

    @discord.ui.button(label="Report", style=discord.ButtonStyle.green, custom_id="report_member", emoji="🚨")
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket_channel(interaction, "Report")

# --- CLOSE TICKET VIEW ---
class CloseTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket and generating transcript...", ephemeral=True)

        transcript = await chat_exporter.export(interaction.channel)
        if transcript is None:
            return

        transcript_file = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html"
        )

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Ticket Closed",
                description=f"Ticket: {interaction.channel.name}\nClosed by: {interaction.user.mention}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed, file=transcript_file)

        await interaction.channel.delete()

# --- WELCOME FUNCTION ---
async def send_welcome(member, channel):
    embed = discord.Embed(
        title=f"👋 Welcome to {member.guild.name}!",
        description=f"Hey {member.mention}, welcome to **{member.guild.name}**! We're glad to have you here.\n\nMake sure to read the rules and enjoy your stay! 🎉",
        color=0x5865F2
    )

    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Member", value=f"`{member.name}`", inline=False)
    embed.add_field(name="Member Count", value=f"`{member.guild.member_count}`", inline=False)

    await channel.send(embed=embed)

# --- FEATURE 4: SERVER STATS CHANNELS ---
@tasks.loop(minutes=5)
async def update_stats():
    guild = bot.get_guild(STATS_GUILD_ID)
    if not guild:
        return

    member_channel = bot.get_channel(STATS_MEMBER_CHANNEL)
    if member_channel:
        try:
            await member_channel.edit(name=f"👥 Members: {guild.member_count}")
        except:
            pass

    bot_channel = bot.get_channel(STATS_BOT_CHANNEL)
    if bot_channel:
        try:
            bot_count = len([m for m in guild.members if m.bot])
            await bot_channel.edit(name=f"🤖 Bots: {bot_count}")
        except:
            pass

@update_stats.before_loop
async def before_update_stats():
    await bot.wait_until_ready()

# --- BOT EVENTS ---
@bot.event
async def on_ready():
    bot.add_view(TicketPanel())
    bot.add_view(CloseTicket())
    update_stats.start()

    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to {guild.name}")
        except Exception as e:
            print(f"Failed to sync to {guild.name}: {e}")

    print(f"Logged in as {bot.user}")

@bot.event
async def on_member_join(member):
    guild_config = get_guild_config(member.guild.id)

    role_id = guild_config.get("auto_role")
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role, reason="Auto role on join")
            except discord.Forbidden:
                print("Bot doesn't have permission to give that role. Move bot role higher.")

    channel_id = guild_config.get("welcome_channel")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            await send_welcome(member, channel)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.author.guild_permissions.manage_messages:
        if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
            if message.channel.id not in INVITE_WHITELIST:
                await message.delete()
                await message.channel.send(f"{message.author.mention} No server invites allowed.", delete_after=5)
                return

        content_lower = message.content.lower()
        for word in BANNED_WORDS:
            if word in content_lower:
                await message.delete()
                await message.channel.send(f"{message.author.mention} That word is not allowed.", delete_after=5)
                return

        if not hasattr(bot, 'spam_check'):
            bot.spam_check = {}

        user_id = message.author.id
        now = time.time()

        if user_id not in bot.spam_check:
            bot.spam_check[user_id] = []

        bot.spam_check[user_id] = [t for t in bot.spam_check[user_id] if now - t < 10]
        bot.spam_check[user_id].append(now)

        if len(bot.spam_check[user_id]) > 5:
            await message.delete()
            try:
                await message.author.timeout(discord.utils.utcnow() + timedelta(seconds=60), reason="AutoMod: Spam")
                await message.channel.send(f"{message.author.mention} timed out for 60s for spamming.", delete_after=5)
            except:
                pass
            bot.spam_check[user_id] = []
            return

    if message.guild and not message.content.startswith('!'):
        levels = load_levels()
        guild_id = str(message.guild.id)
        user_id = str(message.author.id)

        if guild_id not in levels:
            levels[guild_id] = {}
        if user_id not in levels[guild_id]:
            levels[guild_id][user_id] = {"xp": 0, "level": 0, "last_msg": 0}

        if (datetime.now().timestamp() - levels[guild_id][user_id]["last_msg"]) > 60:
            xp_gain = random.randint(15, 25)
            levels[guild_id][user_id]["xp"] += xp_gain
            levels[guild_id][user_id]["last_msg"] = datetime.now().timestamp()

            current_level = levels[guild_id][user_id]["level"]
            new_level = get_level_from_xp(levels[guild_id][user_id]["xp"])

            if new_level > current_level:
                levels[guild_id][user_id]["level"] = new_level
                embed = discord.Embed(title="🎉 Level Up!", description=f"{message.author.mention} reached level **{new_level}**!", color=discord.Color.gold())

                if new_level in LEVEL_ROLES:
                    role = message.guild.get_role(LEVEL_ROLES[new_level])
                    if role and role not in message.author.roles:
                        try:
                            await message.author.add_roles(role, reason=f"Reached level {new_level}")
                            embed.add_field(name="Role Unlocked!", value=f"You earned the {role.mention} role", inline=False)
                        except discord.Forbidden:
                            embed.add_field(name="Role Error", value="I can't give that role. Move my role higher.", inline=False)

                await message.channel.send(embed=embed, delete_after=10)
            save_levels(levels)

    if groq_client and (bot.user in message.mentions or (AI_CHANNEL_ID!= 0 and message.channel.id == AI_CHANNEL_ID)):
        if message.content.startswith('!'):
            await bot.process_commands(message)
            return
        async with message.channel.typing():
            try:
                content = message.content.replace(f'<@{bot.user.id}>', '').strip()
                if not content: return
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "You are RUNCANDELS AI for the RUNCANDELS Discord server. Be friendly, casual, use emojis. Keep replies under 300 chars unless asked for detail. You help with server questions, general chat, and keep vibes good. Never say you're an AI assistant - just be RUNCANDELS AI."},
                        {"role": "user", "content": content}
                    ],
                    model="llama-3.1-8b-instant",
                    max_tokens=400
                )
                await message.reply(chat_completion.choices[0].message.content[:2000])
            except Exception as e:
                print(f"AI Error: {e}")
                await message.reply("AI is down rn 😴")

    await bot.process_commands(message)

# --- SLASH COMMANDS ---
@bot.tree.command(name="ticket-panel", description="Post the RUNCANDELS ticket panel")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📩 RUNCANDELS Help Desk",
        description="Select a category below to open a ticket.\n\n🛠️ **General Support** — General help\n🚨 **Report** — Report a member\n\nOne active ticket per user per category.",
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.set_footer(text="RUNCANDELS Support Team")
    await interaction.response.send_message(embed=embed, view=TicketPanel())

@bot.tree.command(name="welcomeset", description="Set the welcome channel")
@app_commands.checks.has_permissions(administrator=True)
async def welcomeset(interaction: discord.Interaction, channel: discord.TextChannel):
    set_guild_config(interaction.guild_id, "welcome_channel", channel.id)
    await interaction.response.send_message(f"Welcome channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="autorole", description="Set the auto role for new members")
@app_commands.checks.has_permissions(administrator=True)
async def autorole(interaction: discord.Interaction, role: discord.Role):
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("I can't give that role. Move my role higher than it.", ephemeral=True)
        return
    set_guild_config(interaction.guild_id, "auto_role", role.id)
    await interaction.response.send_message(f"Auto role set to {role.mention}", ephemeral=True)

@bot.tree.command(name="welcome", description="Test or manage welcome messages")
@app_commands.checks.has_permissions(administrator=True)
async def welcome(interaction: discord.Interaction, action: str):
    if action.lower() == "test":
        guild_config = get_guild_config(interaction.guild_id)
        channel_id = guild_config.get("welcome_channel")
        if not channel_id:
            await interaction.response.send_message("Set a welcome channel first with `/welcomeset`", ephemeral=True)
            return
        channel = bot.get_channel(channel_id)
        if channel:
            await send_welcome(interaction.user, channel)
            await interaction.response.send_message("Sent test welcome message!", ephemeral=True)
        else:
            await interaction.response.send_message("Welcome channel not found.", ephemeral=True)
    else:
        await interaction.response.send_message("Use `/welcome test` to send a test message.", ephemeral=True)

@bot.tree.command(name="rank", description="Check your level and XP")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user

    levels = load_levels()
    guild_id = str(interaction.guild.id)
    user_id = str(member.id)

    if guild_id not in levels or user_id not in levels[guild_id]:
        await interaction.response.send_message(f"{member.mention} hasn't earned any XP yet!", ephemeral=True)
        return

    user_data = levels[guild_id][user_id]
    level = user_data["level"]
    xp = user_data["xp"]

    current_level_xp = sum([get_xp_for_level(i) for i in range(level)])
    next_level_xp = get_xp_for_level(level)
    progress = xp - current_level_xp

    embed = discord.Embed(title=f"{member.display_name}'s Rank", color=discord.Color.blurple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Level", value=f"`{level}`", inline=True)
    embed.add_field(name="XP", value=f"`{xp}`", inline=True)
    embed.add_field(name="Progress", value=f"`{progress}/{next_level_xp}`", inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard", description="Show the server XP leaderboard")
async def leaderboard(interaction: discord.Interaction):
    levels = load_levels()
    guild_id = str(interaction.guild.id)

    if guild_id not in levels or not levels[guild_id]:
        await interaction.response.send_message("No one has earned XP yet!", ephemeral=True)
        return

    sorted_users = sorted(levels[guild_id].items(), key=lambda x: x[1]["xp"], reverse=True)[:10]

    embed = discord.Embed(title="🏆 RUNCANDELS Leaderboard", color=discord.Color.gold())

    desc = ""
    for i, (user_id, data) in enumerate(sorted_users, 1):
        user = interaction.guild.get_member(int(user_id))
        if user:
            desc += f"**{i}.** {user.mention} - Level `{data['level']}` | `{data['xp']}` XP\n"

    embed.description = desc if desc else "No data"
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rewards", description="Show all level role rewards")
async def rewards(interaction: discord.Interaction):
    embed = discord.Embed(title="🏅 Level Rewards", description="Reach these levels to unlock roles:", color=discord.Color.blue())
    for level, role_id in sorted(LEVEL_ROLES.items()):
        role = interaction.guild.get_role(role_id)
        if role:
            embed.add_field(name=f"Level {level}", value=role.mention, inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="roast", description="Get RUNCANDELS AI to roast someone")
@app_commands.describe(user="Who to roast")
@commands.cooldown(1, 30, commands.BucketType.user)
async def roast(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer()

    if user.id == interaction.user.id:
        await interaction.followup.send("You can't roast yourself 💀")
        return

    if not groq_client:
        await interaction.followup.send("AI is not set up.")
        return

        try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are RUNCANDELS AI. Roast the user savagely but keep it playful, no slurs or actual hate. Max 2 sentences. Use emojis."},
                {"role": "user", "content": f"Roast this person: {user.display_name}"}
            ],
            model="llama-3.1-8b-instant",
            max_tokens=100
        )
        roast_text = chat_completion.choices[0].message.content
        await interaction.followup.send(f"{user.mention} {roast_text}")
    except Exception as e:
        await interaction.followup.send("Roast machine broke 💀")