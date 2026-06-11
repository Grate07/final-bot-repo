import discord
from discord.ext import commands
import os, asyncio, chat_exporter, io
from flask import Flask
from threading import Thread

app = Flask('')
@app.route('/')
def home(): return "Bot is running!"
def run(): app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Config - replace with your IDs
TICKET_CATEGORY = 0  # Right click category -> Copy ID
LOG_CHANNEL = 0      # Right click channel -> Copy ID  
WELCOME_CHANNEL = 0  # Right click channel -> Copy ID

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY)
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await channel.set_permissions(guild.default_role, read_messages=False)
        
        embed = discord.Embed(title="Ticket Opened", description="Support will be with you shortly.\nClick 🔒 to close.", color=0x00ff00)
        await channel.send(content=interaction.user.mention, embed=embed, view=CloseView())
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

class CloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        log_channel = bot.get_channel(LOG_CHANNEL)
        transcript = await chat_exporter.export(interaction.channel)
        if transcript:
            transcript_file = discord.File(io.BytesIO(transcript.encode()), filename=f"{interaction.channel.name}.html")
            await log_channel.send(f"Ticket {interaction.channel.name} closed by {interaction.user.mention}", file=transcript_file)
        await interaction.response.send_message("Closing ticket in 5 seconds...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    bot.add_view(TicketView())
    bot.add_view(CloseView())
    await bot.tree.sync()

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL)
    if channel:
        embed = discord.Embed(title="Welcome!", description=f"{member.mention} just joined {member.guild.name}!", color=0x00ff00)
        embed.set_thumbnail(url=member.avatar.url)
        await channel.send(embed=embed)

@bot.tree.command(name="ticket-panel")
@commands.has_permissions(administrator=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(title="Support Tickets", description="Click below to create a ticket", color=0x3498db)
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Panel created!", ephemeral=True)

@bot.tree.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"Banned {member.mention} | Reason: {reason}")

@bot.tree.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"Kicked {member.mention} | Reason: {reason}")

@bot.tree.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"Deleted {amount} messages", ephemeral=True)

bot.run(os.getenv("TOKEN"))
