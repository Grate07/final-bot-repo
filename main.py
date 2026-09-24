import discord
from discord.ext import commands, tasks
from discord import app_commands
import io, os, json, gc, random, time, asyncio, aiohttp
from flask import Flask
from threading import Thread
from datetime import datetime
gc.set_threshold(700, 10, 10)

try: import chat_exporter
except: chat_exporter = None
try:
    from groq import Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except: groq_client = None

app = Flask('')
@app.route('/')
def home(): return "RUNCANDELS Running!"
def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
def keep_alive():
    t = Thread(target=run); t.daemon=True; t.start()

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

ACCENT = 0x0F0F0F
STAFF_ROLE_ID = 1480151118276202649
TICKET_CATEGORY_FALLBACK = 1513372898058833981
LOG_CHANNEL_ID = 1513387589514694747
CONFIG_FILE = "config.json"
LEVELS_FILE = "levels.json"
HF_TOKEN = os.getenv("HF_TOKEN")
AI_CHANNEL_ID = 1514982328584241316
LEVEL_ROLES = {5: 1485818597870796840, 10: 1485817312098385950, 20: 1485817682682183731, 50: 1485817752965877790}
STATS_GUILD_ID = 1465300538491932869
STATS_MEMBER_CHANNEL = 1514982328584241317
STATS_BOT_CHANNEL = 1514982328584241318
BANNED_WORDS = ["badword1", "slur2"]
INVITE_WHITELIST = []
http_session = None

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f: return json.load(f)
        except: pass
    return {"transcript_channel": LOG_CHANNEL_ID, "ticket_categories": {"queries": TICKET_CATEGORY_FALLBACK, "report": TICKET_CATEGORY_FALLBACK}, "welcome_channel": None, "auto_role": None, "ticket_count": 0}

def save_config(d):
    with open(CONFIG_FILE, 'w') as f: json.dump(d, f, indent=4)

def set_guild_config(gid, k, v):
    c = load_config(); c[k]=v; save_config(c)

def is_ticket_staff():
    async def predicate(interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator: return True
        if any(r.id == STAFF_ROLE_ID for r in interaction.user.roles): return True
        view = discord.ui.LayoutView()
        view.add_item(discord.ui.Container(accent_colour=0xFF0000, children=[discord.ui.TextDisplay(f"❌ Need <@&{STAFF_ROLE_ID}>")] ))
        await interaction.response.send_message(view=view, ephemeral=True)
        return False
    return app_commands.check(predicate)

def load_levels():
    if os.path.exists(LEVELS_FILE):
        try:
            with open(LEVELS_FILE,'r') as f: return json.load(f)
        except: pass
    return {}
def save_levels(d):
    with open(LEVELS_FILE,'w') as f: json.dump(d,f,indent=4)
def get_xp_for_level(l): return 5*(l**2)+50*l+100
def get_level_from_xp(xp):
    l=0
    while xp>=get_xp_for_level(l): xp-=get_xp_for_level(l); l+=1
    return l

# --- RUNCANDELS TICKET SYSTEM - ONLY ISSUE ---

class CloseBtn(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="runcandels_close")
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        c = load_config()
        trans_id = c.get("transcript_channel")
        if trans_id and chat_exporter:
            ch = interaction.guild.get_channel(trans_id)
            if ch:
                try:
                    transcript = await chat_exporter.export(interaction.channel, limit=None, tz_info="UTC")
                    if transcript:
                        file = discord.File(io.BytesIO(transcript.encode()), filename=f"transcript-{interaction.channel.name}.html")
                        v = discord.ui.LayoutView()
                        cont = discord.ui.Container(accent_colour=ACCENT)
                        cont.add_item(discord.ui.TextDisplay(f"### RUNCANDELS Ticket Closed\n**Channel:** {interaction.channel.name}\n**Closed by:** {interaction.user.mention}"))
                        v.add_item(cont)
                        await ch.send(view=v, file=file)
                except Exception as e: print(e)
        await interaction.channel.send("🔒 Closing in 3s...")
        await asyncio.sleep(3)
        try: await interaction.channel.delete(reason=f"Closed by {interaction.user}")
        except: pass

class TicketModal(discord.ui.Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title=f"{ticket_type} Ticket")
        self.ticket_type = ticket_type
        self.issue = discord.ui.TextInput(
            label="Issue",
            placeholder="Describe your issue / report in detail...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000
        )
        self.add_item(self.issue)

    async def on_submit(self, interaction: discord.Interaction):
        await create_ticket_channel(interaction, self.ticket_type, self.issue.value)

async def create_ticket_channel(interaction: discord.Interaction, ticket_type: str, issue_text: str):
    await interaction.response.defer(ephemeral=True, thinking=True)
    config = load_config()
    guild = interaction.guild
    category_id = config.get("ticket_categories", {}).get(ticket_type.lower(), TICKET_CATEGORY_FALLBACK)
    category = guild.get_channel(category_id) if category_id else None

    existing = discord.utils.get(guild.text_channels, name=f"{ticket_type.lower()}-{interaction.user.name.lower()}"[:90])
    if existing:
        return await interaction.followup.send(f"You already have a ticket: {existing.mention}", ephemeral=True)

    config["ticket_count"] = config.get("ticket_count", 0) + 1
    save_config(config)
    ticket_id = f"SUP-{config['ticket_count']:05d}"

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    staff_role = guild.get_role(STAFF_ROLE_ID)
    if staff_role:
        overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

    channel = await guild.create_text_channel(name=f"{ticket_type.lower()}-{interaction.user.name}"[:90], category=category, overwrites=overwrites, topic=f"ID:{ticket_id} | UID:{interaction.user.id}")

    view = discord.ui.LayoutView(timeout=None)
    container = discord.ui.Container(accent_colour=ACCENT)
    container.add_item(discord.ui.TextDisplay(f"### 🎫 {ticket_id} — {ticket_type}"))
    container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

    # CLEAN VERSION - ONLY ISSUE (like you asked)
    body = f"**Opened by**\n{interaction.user.mention}\n\n"
    body += f"**Type**\n{ticket_type}\n\n"
    body += f"**Status**\nOpen\n\n"
    body += f"**Issue**\n{issue_text}\n\n"
    body += f"-# RUNCANDELS Ticket Desk | Today at {datetime.now().strftime('%H:%M')}"

    container.add_item(discord.ui.TextDisplay(body))
    view.add_item(container)
    view.add_item(discord.ui.ActionRow(CloseBtn()))

    ping = f"{interaction.user.mention} {staff_role.mention if staff_role else ''}"
    await channel.send(content=ping, view=view)
    await interaction.followup.send(f"✅ Ticket created: {channel.mention} | `{ticket_id}`", ephemeral=True)

class TicketSelect(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Select ticket type...", custom_id="runcandels_select", options=[
            discord.SelectOption(label="Queries", value="Queries", description="Ask a question", emoji="💬"),
            discord.SelectOption(label="Report", value="Report", description="Report a user/bug", emoji="🚨")
        ])
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal(self.values[0]))

class TicketPanelView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        container = discord.ui.Container(accent_colour=ACCENT)
        container.add_item(discord.ui.TextDisplay("## RUNCANDELS Support Panel\n-# Select below to open a ticket"))
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay("> 💬 **Queries** — Questions, help, info\n> 🚨 **Report** — Report player / bug / issue"))
        container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.large))
        container.add_item(discord.ui.TextDisplay("-# One ticket per category. Abuse = punishment."))
        self.add_item(container)
        self.add_item(discord.ui.ActionRow(TicketSelect()))

class CloseView(discord.ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.ActionRow(CloseBtn()))

async def send_welcome(member, channel):
    view = discord.ui.LayoutView()
    container = discord.ui.Container(accent_colour=ACCENT)
    container.add_item(discord.ui.TextDisplay(f"## 👋 Welcome to {member.guild.name}!\nHey {member.mention}, welcome to **RUNCANDELS**! 🎉\nMember #{member.guild.member_count}"))
    view.add_item(container)
    await channel.send(view=view)

@tasks.loop(minutes=5)
async def update_stats():
    guild = bot.get_guild(STATS_GUILD_ID)
    if not guild: return
    mc = bot.get_channel(STATS_MEMBER_CHANNEL)
    if mc:
        try: await mc.edit(name=f"👥 Members: {guild.member_count}")
        except: pass
    bc = bot.get_channel(STATS_BOT_CHANNEL)
    if bc:
        try: await bc.edit(name=f"🤖 Bots: {len([m for m in guild.members if m.bot])}")
        except: pass
@update_stats.before_loop
async def before_update_stats(): await bot.wait_until_ready()

@bot.event
async def on_ready():
    global http_session
    http_session = aiohttp.ClientSession()
    bot.add_view(TicketPanelView())
    bot.add_view(CloseView())
    update_stats.start()
    for guild in bot.guilds:
        try:
            await bot.tree.sync(guild=guild)
        except Exception as e: print(e)
    print(f"Logged in as {bot.user} | RUNCANDELS V2")

@bot.event
async def on_member_join(member):
    c = load_config()
    if c.get("auto_role"):
        r = member.guild.get_role(c["auto_role"])
        if r:
            try: await member.add_roles(r)
            except: pass
    if c.get("welcome_channel"):
        ch = bot.get_channel(c["welcome_channel"])
        if ch: await send_welcome(member, ch)

@bot.event
async def on_message(message):
    if message.author.bot: return
    if not message.author.guild_permissions.manage_messages:
        if "discord.gg/" in message.content.lower():
            if message.channel.id not in INVITE_WHITELIST:
                try: await message.delete(); await message.channel.send(f"{message.author.mention} No invites.", delete_after=5); return
                except: pass
    if message.guild and not message.content.startswith('!'):
        levels = load_levels()
        gid, uid = str(message.guild.id), str(message.author.id)
        if gid not in levels: levels[gid]={}
        if uid not in levels[gid]: levels[gid][uid]={"xp":0,"level":0,"last_msg":0}
        if (datetime.now().timestamp()-levels[gid][uid]["last_msg"])>60:
            levels[gid][uid]["xp"]+=random.randint(15,25)
            levels[gid][uid]["last_msg"]=datetime.now().timestamp()
            new = get_level_from_xp(levels[gid][uid]["xp"])
            if new>levels[gid][uid]["level"]:
                levels[gid][uid]["level"]=new
                v = discord.ui.LayoutView(); cont = discord.ui.Container(accent_colour=ACCENT); cont.add_item(discord.ui.TextDisplay(f"### 🎉 Level Up!\n{message.author.mention} reached **Level {new}**!")); v.add_item(cont)
                try: await message.channel.send(view=v, delete_after=10)
                except: pass
            save_levels(levels)
    if groq_client and (bot.user in message.mentions or message.channel.id==AI_CHANNEL_ID):
        if not message.content.startswith('!'):
            async with message.channel.typing():
                try:
                    content=message.content.replace(f'<@{bot.user.id}>','').strip()
                    if content:
                        comp=groq_client.chat.completions.create(messages=[{"role":"system","content":"You are RUNCANDELS AI, friendly, casual."},{"role":"user","content":content}], model="llama-3.1-8b-instant", max_tokens=400)
                        await message.reply(comp.choices[0].message.content[:2000])
                except: pass
    await bot.process_commands(message)

@bot.tree.command(name="ticket-panel", description="Post RUNCANDELS ticket panel")
@bot.tree.command(name="setup-ticket-panel", description="Post RUNCANDELS ticket panel")
@is_ticket_staff()
async def ticket_panel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.channel.send(view=TicketPanelView())
    await interaction.followup.send("✅ RUNCANDELS panel sent!", ephemeral=True)

@bot.tree.command(name="set-transcript", description="Set transcript log channel")
@is_ticket_staff()
async def set_transcript(interaction: discord.Interaction, channel: discord.TextChannel):
    try:
        c=load_config(); c["transcript_channel"]=channel.id; save_config(c)
        v=discord.ui.LayoutView(); v.add_item(discord.ui.Container(accent_colour=ACCENT, children=[discord.ui.TextDisplay(f"✅ Transcript → {channel.mention}")]))
        await interaction.response.send_message(view=v, ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Error: {e}", ephemeral=True)

@bot.tree.command(name="set-ticket-category", description="Set category for ticket type")
@is_ticket_staff()
@app_commands.choices(ticket_type=[app_commands.Choice(name="Queries", value="queries"), app_commands.Choice(name="Report", value="report")])
async def set_ticket_category(interaction: discord.Interaction, ticket_type: app_commands.Choice[str], category: discord.CategoryChannel):
    try:
        await interaction.response.defer(ephemeral=True)
        c=load_config()
        if "ticket_categories" not in c: c["ticket_categories"]={}
        real = ticket_type.value
        c["ticket_categories"][real]=category.id
        save_config(c)
        v=discord.ui.LayoutView(); v.add_item(discord.ui.Container(accent_colour=ACCENT, children=[discord.ui.TextDisplay(f"✅ **{real.capitalize()}** → **{category.name}**")]))
        await interaction.followup.send(view=v, ephemeral=True)
    except Exception as e:
        try: await interaction.followup.send(f"❌ {e}", ephemeral=True)
        except: pass

@bot.tree.command(name="welcomeset", description="Set welcome channel")
@app_commands.checks.has_permissions(administrator=True)
async def welcomeset(interaction: discord.Interaction, channel: discord.TextChannel):
    set_guild_config(interaction.guild_id, "welcome_channel", channel.id)
    v=discord.ui.LayoutView(); v.add_item(discord.ui.Container(accent_colour=ACCENT, children=[discord.ui.TextDisplay(f"Welcome → {channel.mention}")]))
    await interaction.response.send_message(view=v, ephemeral=True)

@bot.tree.command(name="rank", description="Check level")
async def rank(interaction: discord.Interaction, member: discord.Member=None):
    member=member or interaction.user
    levels=load_levels(); gid=str(interaction.guild.id); uid=str(member.id)
    if gid not in levels or uid not in levels[gid]: return await interaction.response.send_message("No XP", ephemeral=True)
    data=levels[gid][uid]
    v=discord.ui.LayoutView(); c=discord.ui.Container(accent_colour=ACCENT); c.add_item(discord.ui.TextDisplay(f"## {member.display_name}'s Rank\nLevel {data['level']} | XP {data['xp']}")); v.add_item(c)
    await interaction.response.send_message(view=v)

@bot.tree.command(name="leaderboard", description="Show leaderboard")
async def leaderboard(interaction: discord.Interaction):
    levels=load_levels(); gid=str(interaction.guild.id)
    if gid not in levels: return await interaction.response.send_message("No XP", ephemeral=True)
    sorted_users=sorted(levels[gid].items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    desc="\n".join([f"**{i}.** <@{uid}> - Lvl {d['level']} ({d['xp']} XP)" for i,(uid,d) in enumerate(sorted_users,1)])
    v=discord.ui.LayoutView(); c=discord.ui.Container(accent_colour=ACCENT); c.add_item(discord.ui.TextDisplay(f"### 🏆 RUNCANDELS Leaderboard\n{desc}")); v.add_item(c)
    await interaction.response.send_message(view=v)

@bot.command(name="imagine")
@commands.cooldown(1,30,commands.BucketType.user)
async def imagine(ctx, *, prompt: str=None):
    if ctx.channel.id!=AI_CHANNEL_ID: return await ctx.reply(f"Use <#{AI_CHANNEL_ID}>", delete_after=5)
    if not prompt: return await ctx.reply("Prompt?")
    msg=await ctx.reply(f"🎨 {prompt}")
    API_URL="https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
    headers={"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    try:
        async with http_session.post(API_URL, headers=headers, json={"inputs": prompt}, timeout=60) as r:
            if r.status!=200: return await msg.edit(content=f"Error {r.status}")
            image_bytes=await r.read()
        file=discord.File(io.BytesIO(image_bytes), filename="imagine.png")
        await msg.delete()
        v=discord.ui.LayoutView(); c=discord.ui.Container(accent_colour=ACCENT); c.add_item(discord.ui.TextDisplay(f"`{prompt}`")); v.add_item(c)
        await ctx.send(view=v, file=file)
    except Exception as e: await msg.edit(content=f"Failed {e}")

async def load_cogs():
    try: await bot.load_extension("cogs.moderation")
    except Exception as e: print(e)

if __name__=="__main__":
    keep_alive()
    token=os.getenv("DISCORD_TOKEN")
    if token:
        async def main():
            await load_cogs(); await bot.start(token)
        asyncio.run(main())