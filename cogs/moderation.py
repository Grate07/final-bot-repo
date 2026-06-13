import discord
from discord.ext import commands

MODLOG_CHANNEL_ID = 0  # Put your modlogs channel ID here

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_action(self, guild, title, description):
        if not MODLOG_CHANNEL_ID:
            return

        channel = guild.get_channel(MODLOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.red()
            )
            await channel.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        await ctx.channel.purge(limit=amount + 1)

        msg = await ctx.send(f"🗑 Deleted {amount} messages.")
        await msg.delete(delay=3)

        await self.log_action(
            ctx.guild,
            "Message Purge",
            f"{ctx.author.mention} deleted {amount} messages in {ctx.channel.mention}"
        )

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.kick(reason=reason)

        await ctx.send(f"👢 Kicked {member}")

        await self.log_action(
            ctx.guild,
            "Member Kicked",
            f"**User:** {member}\n**Moderator:** {ctx.author}\n**Reason:** {reason}"
        )

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason="No reason provided"):
        await member.ban(reason=reason)

        await ctx.send(f"🔨 Banned {member}")

        await self.log_action(
            ctx.guild,
            "Member Banned",
            f"**User:** {member}\n**Moderator:** {ctx.author}\n**Reason:** {reason}"
        )

async def setup(bot):
    await bot.add_cog(Moderation(bot))
