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
import aiohttp
gc.set_threshold(700, 10, 10)

# --- KEEP RENDER ALIVE ---
app = Flask('')
@app.route('/')
def home():
    return "Onyx is running!"
def run():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIG ---
ONYX = 0x0F0F0F
STAFF_ROLE_ID = 1480151118276202649 # YOUR REQUIRED ROLE
TICKET_CATEGORY_FALLBACK = 1513372898058833981
LOG_CHANNEL_ID = 1513387589514694747
CONFIG_FILE = "config.json"
LEVELS_FILE = "levels.json"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")
AI_CHANNEL_ID = 1514982328584241316
LEVEL_ROLES = {5: 1485818597870796840, 10: 1485817312098385950, 20: 1485817682682183731, 50: 1485817752965877790}
STATS_GUILD_ID = 1465300538491932869
STATS_MEMBER_CHANNEL = 1514982328584241317
STATS_BOT_CHANNEL = 1514982328584241318
BANNED_WORDS = ["badword1", "slur2"]
INVITE_WHITELIST = []

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
http_session = None

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    return {"transcript_channel": LOG_CHANNEL_ID, "ticket_categories": {"queries": TICKET_CATEGORY_FALLBACK, "report": TICKET_CATEGORY_FALLBACK}, "welcome_channel": None, "auto_role": None}

def save_config(data):
    with open(CONFIG_FILE, 'w') as f: json.dump(data, f, indent=4)

def get_guild_config(guild_id):
    c = load_config()
    return c

def set_guild_config(guild_id, key, value):
    c = load_config()
    c[key] = value
    save_config(c)

# --- PERMISSION CHECK FOR YOUR ROLE ---
def is_ticket_staff():
    async def predicate(interaction: discord.Interaction):
        has_role = any(r.id == STAFF_ROLE_ID for r in interaction.user.roles)
        if has_role or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message(f"❌ You need <@&{STAFF_ROLE_ID}> to use this.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# --- LEVEL SYSTEM (same) ---
def load_levels():
    if os.path.exists(LEVELS_FILE):
        with open(LEVELS_FILE, 'r') as f: return json.load(f)
    return {}
def save_levels(data):
    with open(LEVELS_FILE, 'w') as f: json.dump(data, f, indent=4)
def get_xp_for_level(level): return 5 * (level ** 2) + 50 * level + 100
def get_level_from_xp(xp):
    level = 0
    while xp >= get_xp_for_level(level):
        xp -= get_xp_for_level(level)
        level += 1
    return level

# --- NEW ONYX TICKET SYSTEM - COMPONENTS V2 ---
class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"{ticket_type.capitalize()} Ticket")
        self.ticket_type = ticket_type.lower()
        label = "Write your query" if self.ticket_type == "queries" else "What do you want to report?"
        self.desc = discord.ui.TextInput(label=label, placeholder="Describe in detail...", style=discord.TextStyle.paragraph, required=True, max_length=1000)
        self.add_item(self.desc)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        config = load_config()
        guild = interaction.guild

        category_id = config.get("ticket_categories", {}).get(self.ticket_type, TICKET_CATEGORY_FALLBACK)
        category = guild.get_channel(category_id) if category_id else None

        # prevent duplicate
        existing = discord.utils.get(guild.text_channels, name=f"{self.ticket_type}-{interaction.user.name.lower()}"[:90])
        if existing:
            return await interaction.followup.send(f"You already have a ticket: {existing.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

        channel = await guild.create_text_channel(
            name=f"{self.ticket_type}-{interaction.user.name}"[:90],
            category=category,
            overwrites=overwrites,
            topic=f"UID:{interaction.user.id} | Type:{self.ticket_type}"
        )

        # Components V2 ticket welcome
        view = discord.ui.LayoutView(timeout=None)
        container = discord.ui.Container(accent_colour=ONYX)
        container.add_item(discord.ui.TextDisplay(f"## 🎫 {self.ticket_type.capitalize()} Ticket\nWelcome {interaction.user.mention}, staff will be with you shortly."))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(f"**Description:**\n>>> {self.desc.value}"))
        container.add_item(discord.ui.TextDisplay(f"-# User ID: {interaction.user.id}"))
        view.add_item(container)
        view.add_item(discord.ui.ActionRow(CloseTicketBtn()))

        await channel.send(content=f"{interaction.user.mention} {staff_role.mention if staff_role else ''}", view=view)
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select ticket type...", custom_id="onyx_select", options=[
            discord.SelectOption(label="Queries", value="queries", description="Write description", emoji="💬"),
            discord.SelectOption(label="Report", value="report", description="Report something", emoji="🚨")
        ])
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.values[0]))

class TicketPanelView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=ONYX)
        container.add_item(discord.ui.TextDisplay("## Onyx Support Panel\n-# Fully configurable ticket system"))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay("**Options:**\n> 💬 **Queries** - Have a question? Select it.\n> 🚨 **Report** - Report a user, bug or issue."))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(discord.ui.TextDisplay("-# Abuse of tickets will result in punishment."))
        self.add_item(container)
        self.add_item(discord.ui.ActionRow(TicketSelect()))

class CloseTicketBtn(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close & Transcript", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_v2")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        config = load_config()
        transcript_channel_id = config.get("transcript_channel")

        if transcript_channel_id:
            transcript_channel = interaction.guild.get_channel(transcript_channel_id)
            if transcript_channel:
                try:
                    transcript = await chat_exporter.export(interaction.channel, limit=None, tz_info="UTC")
                    if transcript:
                        file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{interaction.channel.name}.html")
                        v = discord.ui.LayoutView()
                        c = discord.ui.Container(accent_colour=ONYX)
                        c.add_item(discord.ui.TextDisplay(f"### Ticket Closed\n**Channel:** {interaction.channel.name}\n**Closed by:** {interaction.user.mention}\n**Topic:** {interaction.channel.topic}"))
                        v.add_item(c)
                        await transcript_channel.send(view=v, file=file)
                except Exception as e:
                    print(f"Transcript error: {e}")

        await interaction.channel.send("🔒 Closing in 3s...")
        await asyncio.sleep(3)
        try: await interaction.channel.delete(reason=f"Closed by {interaction.user}")
        except: pass

class CloseView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.ActionRow(CloseTicketBtn()))

# --- WELCOME - V2 ---
async def send_welcome(member, channel):
    view = discord.ui.LayoutView()
    container = discord.ui.Container(accent_colour=ONYX)
    container.add_item(discord.ui.TextDisplay(f"## 👋 Welcome to {member.guild.name}!"))
    container.add_item(discord.ui.TextDisplay(f"Hey {member.mention}, glad to have you here! 🎉\nMember #{member.guild.member_count}"))
    container.add_item(discord.ui.Separator())
    container.add_item(discord.ui.TextDisplay(f"-# Member: `{member.name}`"))
    view.add_item(container)
    await channel.send(view=view)

@tasks.loop(minutes=5)
async def update_stats():
    guild = bot.get_guild(STATS_GUILD_ID)
    if not guild: return
    member_channel = bot.get_channel(STATS_MEMBER_CHANNEL)
    if member_channel:
        try: await member_channel.edit(name=f"👥 Members: {guild.member_count}")
        except: pass
    bot_channel = bot.get_channel(STATS_BOT_CHANNEL)
    if bot_channel:
        try:
            bot_count = len([m for m in guild.members if m.bot])
            await bot_channel.edit(name=f"🤖 Bots: {bot_count}")
        except: pass
@update_stats.before_loop
async def before_update_stats(): await bot.wait_until_ready()

# --- EVENTS ---
@bot.event
async def on_ready():
    global http_session
    http_session = aiohttp.ClientSession()
    bot.add_view(TicketPanelView())
    bot.add_view(CloseView())
    update_stats.start()
    for guild in bot.guilds:
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"Synced {len(synced)} to {guild.name}")
        except Exception as e: print(e)
    print(f"Logged in as {bot.user} | ONYX V2 READY")

@bot.event
async def on_member_join(member):
    config = load_config()
    role_id = config.get("auto_role")
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try: await member.add_roles(role, reason="Auto role")
            except: pass
    channel_id = config.get("welcome_channel")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel: await send_welcome(member, channel)

@bot.event
async def on_message(message):
    if message.author.bot: return
    # automod + level + AI (kept same as yours)
    if not message.author.guild_permissions.manage_messages:
        if "discord.gg/" in message.content.lower():
            if message.channel.id not in INVITE_WHITELIST:
                await message.delete()
                await message.channel.send(f"{message.author.mention} No invites.", delete_after=5)
                return
        for word in BANNED_WORDS:
            if word in message.content.lower():
                await message.delete()
                await message.channel.send(f"{message.author.mention} Word not allowed.", delete_after=5)
                return
    if message.guild and not message.content.startswith('!'):
        levels = load_levels()
        gid, uid = str(message.guild.id), str(message.author.id)
        if gid not in levels: levels[gid] = {}
        if uid not in levels[gid]: levels[gid][uid] = {"xp":0,"level":0,"last_msg":0}
        if (datetime.now().timestamp() - levels[gid][uid]["last_msg"]) > 60:
            levels[gid][uid]["xp"] += random.randint(15,25)
            levels[gid][uid]["last_msg"] = datetime.now().timestamp()
            new_level = get_level_from_xp(levels[gid][uid]["xp"])
            if new_level > levels[gid][uid]["level"]:
                levels[gid][uid]["level"] = new_level
                view = discord.ui.LayoutView()
                c = discord.ui.Container(accent_colour=ONYX)
                c.add_item(discord.ui.TextDisplay(f"### 🎉 Level Up!\n{message.author.mention} reached **Level {new_level}**"))
                view.add_item(c)
                await message.channel.send(view=view, delete_after=10)
            save_levels(levels)
    if groq_client and (bot.user in message.mentions or message.channel.id == AI_CHANNEL_ID):
        if not message.content.startswith('!'):
            async with message.channel.typing():
                try:
                    content = message.content.replace(f'<@{bot.user.id}>','').strip()
                    if content:
                        comp = groq_client.chat.completions.create(messages=[{"role":"system","content":"You are Onyx AI, friendly, casual, use emojis. Keep replies under 300 chars."},{"role":"user","content":content}], model="llama-3.1-8b-instant", max_tokens=400)
                        await message.reply(comp.choices[0].message.content[:2000])
                except Exception as e: print(e)
    await bot.process_commands(message)

# --- SLASH COMMANDS - ALL V2 ---

@bot.tree.command(name="setup-ticket-panel", description="Post Onyx ticket panel (V2 + Dropdown)")
@is_ticket_staff()
async def setup_panel(interaction: discord.Interaction):
    await interaction.response.send_message("Sending panel...", ephemeral=True)
    await interaction.channel.send(view=TicketPanelView())

@bot.tree.command(name="set-transcript", description="Set transcript log channel")
@is_ticket_staff()
async def set_transcript(interaction: discord.Interaction, channel: discord.TextChannel):
    c = load_config()
    c["transcript_channel"] = channel.id
    save_config(c)
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(accent_colour=ONYX, children=[discord.ui.TextDisplay(f"✅ Transcript channel set to {channel.mention}")]))
    await interaction.response.send_message(view=v, ephemeral=True)

@bot.tree.command(name="set-ticket-category", description="Set category for ticket types")
@is_ticket_staff()
@app_commands.choices(ticket_type=[app_commands.Choice(name="Queries", value="queries"), app_commands.Choice(name="Report", value="report")])
async def set_ticket_category(interaction: discord.Interaction, ticket_type: str, category: discord.CategoryChannel):
    c = load_config()
    if "ticket_categories" not in c: c["ticket_categories"] = {}
    c["ticket_categories"][ticket_type] = category.id
    save_config(c)
    v = discord.ui.LayoutView()
    v.add_item(discord.ui.Container(accent_colour=ONYX, children=[discord.ui.TextDisplay(f"✅ `{ticket_type}` tickets will now open in **{category.name}**")]))
    await interaction.response.send_message(view=v, ephemeral=True)

@bot.tree.command(name="welcomeset", description="Set the welcome channel")
@app_commands.checks.has_permissions(administrator=True)
async def welcomeset(interaction: discord.Interaction, channel: discord.TextChannel):
    set_guild_config(interaction.guild_id, "welcome_channel", channel.id)
    view = discord.ui.LayoutView()
    view.add_item(discord.ui.Container(accent_colour=ONYX, children=[discord.ui.TextDisplay(f"Welcome channel set to {channel.mention}")]))
    await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="rank", description="Check your level")
async def rank(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    levels = load_levels()
    gid, uid = str(interaction.guild.id), str(member.id)
    if gid not in levels or uid not in levels[gid]:
        return await interaction.response.send_message(f"{member.mention} has no XP", ephemeral=True)
    data = levels[gid][uid]
    view = discord.ui.LayoutView()
    c = discord.ui.Container(accent_colour=ONYX)
    c.add_item(discord.ui.TextDisplay(f"## {member.display_name}'s Rank\n**Level:** {data['level']}\n**XP:** {data['xp']}"))
    view.add_item(c)
    await interaction.response.send_message(view=view)

@bot.tree.command(name="leaderboard", description="Show leaderboard")
async def leaderboard(interaction: discord.Interaction):
    levels = load_levels()
    gid = str(interaction.guild.id)
    if gid not in levels: return await interaction.response.send_message("No XP yet", ephemeral=True)
    sorted_users = sorted(levels[gid].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    desc = "\n".join([f"**{i}.** <@{uid}> - Level {d['level']} ({d['xp']} XP)" for i,(uid,d) in enumerate(sorted_users,1)])
    view = discord.ui.LayoutView()
    c = discord.ui.Container(accent_colour=ONYX)
    c.add_item(discord.ui.TextDisplay(f"### 🏆 Leaderboard\n{desc}"))
    view.add_item(c)
    await interaction.response.send_message(view=view)

# --- YOUR IMAGINE COMMAND SAME BUT V2 RESPONSE ---
@bot.command(name="imagine")
@commands.cooldown(1, 30, commands.BucketType.user)
async def imagine(ctx, *, prompt: str = None):
    if ctx.channel.id!= AI_CHANNEL_ID: return await ctx.reply(f"Use in <#{AI_CHANNEL_ID}>", delete_after=5)
    if not prompt: return await ctx.reply("Give prompt: `!imagine a cyberpunk penguin`")
    msg = await ctx.reply(f"🎨 Drawing: `{prompt}`")
    API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    try:
        async with http_session.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=60) as r:
            if r.status!= 200: return await msg.edit(content=f"Error {r.status}")
            image_bytes = await r.read()
        file = discord.File(io.BytesIO(image_bytes), filename="imagine.png")
        await msg.delete()
        view = discord.ui.LayoutView()
        c = discord.ui.Container(accent_colour=ONYX)
        c.add_item(discord.ui.TextDisplay(f"### Generated\n`{prompt}`\n-# Requested by {ctx.author.display_name}"))
        view.add_item(c)
        await ctx.send(view=view, file=file)
    except Exception as e:
        await msg.edit(content=f"Failed: {e}")

async def load_cogs():
    try: await bot.load_extension("cogs.moderation")
    except Exception as e: print(f"Cog load error: {e}")

if __name__ == "__main__":
    keep_alive()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        async def main():
            await load_cogs()
            await bot.start(token)
        asyncio.run(main())