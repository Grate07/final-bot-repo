import discord
from discord.ext import commands
from discord import app_commands
import chat_exporter
import io
import os
from flask import Flask
from threading import Thread
from datetime import datetime

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
WELCOME_CHANNEL_ID = 1484006886310412329  # Your welcome channel
AUTO_ROLE_ID = 1485336874355658862        # Role to give on join

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

# --- BOT EVENTS ---
@bot.event
async def on_ready():
    bot.add_view(TicketPanel())
    bot.add_view(CloseTicket())
    try:
        synced = await bot.tree.sync()
        print(f"Logged in as {bot.user}")
        print(f"Slash commands synced: {len(synced)}")
    except Exception as e:
        print(e)

@bot.event
async def on_member_join(member):
    # 1. Give auto role
    role = member.guild.get_role(AUTO_ROLE_ID)
    if role:
        try:
            await member.add_roles(role, reason="Auto role on join")
        except discord.Forbidden:
            print("Bot doesn't have permission to give that role. Move bot role higher.")

    # 2. Send welcome message
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel is None:
        return
    
    embed = discord.Embed(
        title=f"Welcome to {member.guild.name}! 🎉",
        description=f"Hey {member.mention}, you’re member #{member.guild.member_count}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Next steps", value="• Check rules\n• Get roles\n• Introduce yourself", inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)  # User's avatar
    embed.set_footer(text=f"Joined: {datetime.now().strftime('%d %b %Y')}")
    
    await channel.send(content=member.mention, embed=embed)

# --- SLASH COMMAND ---
@bot.tree.command(name="ticket-panel", description="Post the ticket creation panel")
@app_commands.checks.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Support Tickets",
        description="Click the button below to create a support ticket.\nOur staff will assist you as soon as possible.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, view=TicketPanel())

@ticket_panel.error
async def ticket_panel_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You need Administrator permission to use this.", ephemeral=True)

# --- RUN BOT ---
keep_alive()
bot.run(os.getenv("TOKEN"))