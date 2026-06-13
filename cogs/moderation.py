import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int):
        await ctx.channel.purge(limit=amount + 1)

        msg = await ctx.send(f"🗑️ Deleted {amount} messages.")
        await msg.delete(delay=3)

async def setup(bot):
    await bot.add_cog(Moderation(bot))