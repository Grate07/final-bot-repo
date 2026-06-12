import discord
from discord.ext import commands
from discord import app_commands
import chat_exporter
import io
import os
from flask import Flask
from threading import Thread
from datetime import datetime
import json

# --- KEEP RENDER ALIVE ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BOT SETUP WITH INTENTS ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- CONFIG ---
TICKET_CATEGORY_NAME = "Tickets"
STAFF_ROLE_NAME = "Staff"
LOG_CHANNEL_ID = 1513387589514694747
CONFIG_FILE = "config.json"

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

# --- TICKET PANEL VIEW ---
class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        existing_ticket = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing_ticket:
            await interaction.response.send_message(f"You already have a ticket: {existing_ticket.mention}", ephemeral=True)
            return

        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Support Ticket",
            description=f"Hey {user.mention}, thanks for creating a ticket!",
            color=discord.Color.blue()
        )
        embed.add_field(name="How to proceed", value="Please describe your issue in detail. A staff member will assist you shortly.", inline=False)
        embed.add_field(name="Close ticket", value="Click the 🔒 button below when your issue is resolved.", inline=False)
        embed.set_footer(text=f"User ID: {user.id}")

        ping_content = f"{user.mention}"
        if staff_role:
            ping_content += f" {staff_role.mention}"

        await channel.send(content=ping_content, embed=embed, view=CloseTicket())
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

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

# --- BOT EVENTS ---
@bot.event
async def on_ready():
    bot.add_view(TicketPanel())
    bot.add_view(CloseTicket())

    # Sync commands to all servers instantly
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

    # 1. Auto role
    role_id = guild_config.get("auto_role")
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            try:
                await member.add_roles(role, reason="Auto role on join")
            except discord.Forbidden:
                print("Bot doesn't have permission to give that role. Move bot role higher.")

    # 2. Welcome message
    channel_id = guild_config.get("welcome_channel")
    if channel_id:
        channel = bot.get_channel(channel_id)
        if channel:
            await send_welcome(member, channel)

# --- SLASH COMMANDS ---
@bot.tree.command(name="ticket-panel", description="Post the ticket creation panel")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Support Tickets",
        description="Click the button below to create a support ticket.\nOur staff will assist you as soon as possible.",
        color=discord.Color.blue()
    )
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

@ticket_panel.error
@welcomeset.error
@autorole.error
@welcome.error
async def cmd_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You need Administrator permission to use this.", ephemeral=True)

# --- RUN BOT ---
keep_alive()
bot.run(os.getenv("TOKEN"))