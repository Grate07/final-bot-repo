import discord
from discord.ext import commands
from discord import Member
from datetime import timedelta

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🧹 Deleted {amount} messages.")
        await msg.delete(delay=3)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: Member, *, reason="No reason provided"):
        await member.kick(reason=reason)
        await ctx.send(f"👢 {member.mention} was kicked.\nReason: {reason}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: Member, *, reason="No reason provided"):
        await member.ban(reason=reason)
        await ctx.send(f"🔨 {member.mention} was banned.\nReason: {reason}")

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"✅ Unbanned {user}")

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: Member, minutes: int, *, reason="No reason provided"):
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await ctx.send(
            f"⏳ {member.mention} timed out for {minutes} minute(s).\nReason: {reason}"
        )

    @commands.command()
    @commands.has_permissions(moderate_members=True)
    async def untimeout(self, ctx, member: Member):
        await member.timeout(None)
        await ctx.send(f"✅ Removed timeout from {member.mention}")

    @commands.command()
@commands.has_permissions(moderate_members=True)
async def warn(self, ctx, member: Member, *, reason="No reason provided"):
    await ctx.send(
        f"⚠️ {member.mention} has been warned.\nReason: {reason}"
    )

    if hasattr(self.bot, "modlogs"):
        channel_id = self.bot.modlogs.get(ctx.guild.id)

        if channel_id:
            log_channel = self.bot.get_channel(channel_id)

            if log_channel:
                embed = discord.Embed(
                    title="⚠️ Member Warned",
                    color=discord.Color.orange()
                )

                embed.add_field(
                    name="User",
                    value=f"{member} ({member.id})",
                    inline=False
                )

                embed.add_field(
                    name="Moderator",
                    value=ctx.author.mention,
                    inline=False
                )

                embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )

                await log_channel.send(embed=embed)
    
    @commands.command()
@commands.has_permissions(administrator=True)
async def setmodlog(self, ctx, channel: discord.TextChannel):
    if not hasattr(self.bot, "modlogs"):
        self.bot.modlogs = {}

    self.bot.modlogs[ctx.guild.id] = channel.id

    await ctx.send(
        f"✅ Mod log channel set to {channel.mention}"
    )

async def setup(bot):
    await bot.add_cog(Moderation(bot))
