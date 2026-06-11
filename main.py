import discord
from discord.ext import commands
from discord import app_commands
import chat_exporter
import io
import os
from flask import Flask
from threading import Thread

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
LOG_CHANNEL_ID = 1513387589514694747  # Your log channel

# --- TICKET PANEL VIEW ---
class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        # Check if ticket exists
        existing_ticket = discord.utils.get(guild.text_channels, name=f"ticket-{user.name.lower()}")
        if existing_ticket:
            await interaction.response.send_message(f"You already have a ticket: {existing_ticket.mention}", ephemeral=True)
            return

        # Get or create category
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category(TICKET_CATEGORY_NAME)

        # Get staff role
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Create ticket channel
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="Ticket Created",
            description=f"Welcome {user.mention}! Support will be with you shortly.\nClick 🔒 to close this ticket.",
            color=discord.Color.green()
        )
        
        await channel.send(embed=embed, view=CloseTicket())
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

# --- CLOSE TICKET VIEW ---
class CloseTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket and generating transcript...", ephemeral=True)
        
        # Generate transcript
        transcript = await chat_exporter.export(interaction.channel)
        if transcript is None:
            return
        
        transcript_file = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html"
        )

        # Send to log channel
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="Ticket Closed",
                description=f"Ticket: {interaction.channel.name}\nClosed by: {interaction.user.mention}",
                color=discord.Color.red()
            )
            await log_channel.send(embed=embed, file=transcript_file)
        
        # Delete channel
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