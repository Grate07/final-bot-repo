import discord
from discord.ext import commands
from discord import Member, app_commands
from datetime import timedelta

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    if not hasattr(bot, "modlogs"):
        bot.modlogs = {}

async def send_modlog(self, guild, embed):
    channel_id = self.bot.modlogs.get(guild.id)

    if not channel_id:
        return

    channel = guild.get_channel(channel_id)

    if channel:
        await channel.send(embed=embed)

@app_commands.command(
    name="setmodlogs",
    description="Set the moderation logs channel"
)
@app_commands.checks.has_permissions(administrator=True)
async def setmodlogs(
    self,
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    self.bot.modlogs[interaction.guild.id] = channel.id

    await interaction.response.send_message(
        f"✅ Mod logs channel set to {channel.mention}",
        ephemeral=True
    )

@commands.Cog.listener()
async def on_message_delete(self, message):
    if message.author.bot or not message.guild:
        return

    embed = discord.Embed(
        title="🗑️ Message Deleted",
        color=discord.Color.red()
    )

    embed.add_field(
        name="Author",
        value=f"{message.author} ({message.author.id})",
        inline=False
    )

    embed.add_field(
        name="Channel",
        value=message.channel.mention,
        inline=False
    )

    embed.add_field(
        name="Content",
        value=message.content[:1024] if message.content else "No text content",
        inline=False
    )

    await self.send_modlog(message.guild, embed)

@commands.Cog.listener()
async def on_message_edit(self, before, after):
    if before.author.bot or not before.guild:
        return

    if before.content == after.content:
        return

    embed = discord.Embed(
        title="✏️ Message Edited",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Author",
        value=f"{before.author} ({before.author.id})",
        inline=False
    )

    embed.add_field(
        name="Channel",
        value=before.channel.mention,
        inline=False
    )

    embed.add_field(
        name="Before",
        value=before.content[:1024] if before.content else "Empty",
        inline=False
    )

    embed.add_field(
        name="After",
        value=after.content[:1024] if after.content else "Empty",
        inline=False
    )

    await self.send_modlog(before.guild, embed)

@commands.command()
@commands.has_permissions(manage_messages=True)
async def purge(self, ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)

    msg = await ctx.send(f"🗑️ Deleted {amount} messages.")
    await msg.delete(delay=3)

    embed = discord.Embed(
        title="🗑️ Messages Purged",
        description=f"{amount} messages deleted.",
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Moderator",
        value=ctx.author.mention,
        inline=False
    )

    await self.send_modlog(ctx.guild, embed)

@commands.command()
@commands.has_permissions(kick_members=True)
async def kick(self, ctx, member: Member, *, reason="No reason provided"):
    await member.kick(reason=reason)

    embed = discord.Embed(
        title="🔨 Member Kicked",
        color=discord.Color.red()
    )

    embed.add_field(name="User", value=str(member), inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)

    await self.send_modlog(ctx.guild, embed)
    await ctx.send(f"🔨 {member.mention} was kicked.")

@commands.command()
@commands.has_permissions(ban_members=True)
async def ban(self, ctx, member: Member, *, reason="No reason provided"):
    await member.ban(reason=reason)

    embed = discord.Embed(
        title="🔨 Member Banned",
        color=discord.Color.dark_red()
    )

    embed.add_field(name="User", value=str(member), inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)

    await self.send_modlog(ctx.guild, embed)
    await ctx.send(f"🔨 {member.mention} was banned.")

@commands.command()
@commands.has_permissions(ban_members=True)
async def unban(self, ctx, user_id: int):
    user = await self.bot.fetch_user(user_id)

    await ctx.guild.unban(user)

    embed = discord.Embed(
        title="✅ Member Unbanned",
        color=discord.Color.green()
    )

    embed.add_field(name="User", value=str(user), inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)

    await self.send_modlog(ctx.guild, embed)
    await ctx.send(f"✅ Unbanned {user}")

@commands.command()
@commands.has_permissions(moderate_members=True)
async def timeout(self, ctx, member: Member, minutes: int, *, reason="No reason provided"):
    duration = timedelta(minutes=minutes)

    await member.timeout(duration, reason=reason)

    embed = discord.Embed(
        title="⏳ Member Timed Out",
        color=discord.Color.gold()
    )

    embed.add_field(name="User", value=str(member), inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
    embed.add_field(name="Duration", value=f"{minutes} minute(s)", inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)

    await self.send_modlog(ctx.guild, embed)

    await ctx.send(
        f"⏳ {member.mention} timed out for {minutes} minute(s)."
    )

@commands.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(self, ctx, member: Member):
    await member.timeout(None)

    embed = discord.Embed(
        title="✅ Timeout Removed",
        color=discord.Color.green()
    )

    embed.add_field(name="User", value=str(member), inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)

    await self.send_modlog(ctx.guild, embed)
    await ctx.send(f"✅ Removed timeout from {member.mention}")

@commands.command()
@commands.has_permissions(moderate_members=True)
async def warn(self, ctx, member: Member, *, reason="No reason provided"):
    embed = discord.Embed(
        title="⚠️ Member Warned",
        color=discord.Color.yellow()
    )

    embed.add_field(name="User", value=str(member), inline=False)
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)

    await self.send_modlog(ctx.guild, embed)

    await ctx.send(
        f"⚠️ {member.mention} has been warned.\nReason: {reason}"
    )

async def setup(bot):
await bot.add_cog(Moderation(bot))
