import discord
from discord.ext import commands
from discord import app_commands
import datetime

ONYX = 0x0F0F0F
STAFF_ROLE_ID = 1480151118276202649

def is_staff():
    async def predicate(interaction: discord.Interaction):
        has_role = any(r.id == STAFF_ROLE_ID for r in interaction.user.roles)
        if has_role or interaction.user.guild_permissions.moderate_members:
            return True
        # V2 deny message
        view = discord.ui.LayoutView()
        view.add_item(discord.ui.Container(accent_colour=0xFF0000, children=[
            discord.ui.TextDisplay(f"❌ You need <@&{STAFF_ROLE_ID}> to use moderation.")
        ]))
        await interaction.response.send_message(view=view, ephemeral=True)
        return False
    return app_commands.check(predicate)

def onyx_embed_view(title: str, description: str, color=ONYX):
    view = discord.ui.LayoutView()
    container = discord.ui.Container(accent_colour=color)
    container.add_item(discord.ui.TextDisplay(f"### {title}\n{description}"))
    container.add_item(discord.ui.TextDisplay(f"-# Onyx Moderation • {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"))
    view.add_item(container)
    return view

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warns = {} # simple in-memory warns, you can move to json later

    @app_commands.command(name="ban", description="Ban a member [Onyx V2]")
    @is_staff()
    @app_commands.describe(member="Member to ban", reason="Reason")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        if member.top_role >= interaction.user.top_role and interaction.guild.owner_id!= interaction.user.id:
            return await interaction.response.send_message(view=onyx_embed_view("Error", f"You can't ban {member.mention} - higher role.", 0xFF0000), ephemeral=True)
        try:
            await member.ban(reason=f"Banned by {interaction.user} | {reason}")
            await interaction.response.send_message(view=onyx_embed_view("🔨 Member Banned", f"**User:** {member.mention} (`{member.id}`)\n**By:** {interaction.user.mention}\n**Reason:** `{reason}`"))
        except Exception as e:
            await interaction.response.send_message(view=onyx_embed_view("Error", f"Failed: {e}", 0xFF0000), ephemeral=True)

    @app_commands.command(name="kick", description="Kick a member [Onyx V2]")
    @is_staff()
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        try:
            await member.kick(reason=reason)
            await interaction.response.send_message(view=onyx_embed_view("👢 Member Kicked", f"**User:** {member.mention}\n**Reason:** `{reason}`\n**By:** {interaction.user.mention}"))
        except Exception as e:
            await interaction.response.send_message(view=onyx_embed_view("Error", str(e), 0xFF0000), ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member")
    @is_staff()
    @app_commands.describe(member="Member", duration="Duration in minutes", reason="Reason")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason"):
        try:
            until = discord.utils.utcnow() + datetime.timedelta(minutes=duration)
            await member.timeout(until, reason=reason)
            await interaction.response.send_message(view=onyx_embed_view("⏰ Member Timed Out", f"**User:** {member.mention}\n**Duration:** `{duration}m`\n**Reason:** `{reason}`"))
        except Exception as e:
            await interaction.response.send_message(view=onyx_embed_view("Error", str(e), 0xFF0000), ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove timeout")
    @is_staff()
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await member.timeout(None)
            await interaction.response.send_message(view=onyx_embed_view("✅ Timeout Removed", f"{member.mention} can speak again."))
        except Exception as e:
            await interaction.response.send_message(view=onyx_embed_view("Error", str(e), 0xFF0000), ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by ID")
    @is_staff()
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Unbanned"):
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=reason)
            await interaction.response.send_message(view=onyx_embed_view("✅ Unbanned", f"**User:** {user.mention} (`{user_id}`)\n**By:** {interaction.user.mention}"))
        except Exception as e:
            await interaction.response.send_message(view=onyx_embed_view("Error", str(e), 0xFF0000), ephemeral=True)

    @app_commands.command(name="clear", description="Clear messages")
    @is_staff()
    @app_commands.describe(amount="Amount 1-100")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            return await interaction.response.send_message(view=onyx_embed_view("Error", "Amount must be 1-100", 0xFF0000), ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        try:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(view=onyx_embed_view("🧹 Cleared", f"Deleted `{len(deleted)}` messages in {interaction.channel.mention}"), ephemeral=True)
        except Exception as e:
            await interaction.followup.send(view=onyx_embed_view("Error", str(e), 0xFF0000), ephemeral=True)

    @app_commands.command(name="warn", description="Warn a user")
    @is_staff()
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        uid = str(member.id)
        if uid not in self.warns: self.warns[uid] = []
        self.warns[uid].append({"reason": reason, "by": interaction.user.id, "at": datetime.datetime.now().isoformat()})

        view = discord.ui.LayoutView()
        container = discord.ui.Container(accent_colour=ONYX)
        container.add_item(discord.ui.TextDisplay(f"### ⚠️ {member.display_name} Warned\n**Reason:** `{reason}`\n**Total Warns:** `{len(self.warns[uid])}`\n**By:** {interaction.user.mention}"))
        view.add_item(container)
        await interaction.response.send_message(view=view)
        try:
            dm_view = discord.ui.LayoutView()
            dm_container = discord.ui.Container(accent_colour=0xFFA500)
            dm_container.add_item(discord.ui.TextDisplay(f"### You were warned in {interaction.guild.name}\n**Reason:** `{reason}`"))
            dm_view.add_item(dm_container)
            await member.send(view=dm_view)
        except: pass

    @app_commands.command(name="warnings", description="Check warnings of a user")
    @is_staff()
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        uid = str(member.id)
        warns = self.warns.get(uid, [])
        if not warns:
            return await interaction.response.send_message(view=onyx_embed_view("Warnings", f"{member.mention} has no warnings."), ephemeral=True)

        desc = "\n".join([f"`{i+1}.` {w['reason']} - <@{w['by']}> - <t:{int(datetime.datetime.fromisoformat(w['at']).timestamp())}:R>" for i,w in enumerate(warns)])
        view = discord.ui.LayoutView()
        container = discord.ui.Container(accent_colour=ONYX)
        container.add_item(discord.ui.TextDisplay(f"### ⚠️ Warnings for {member.display_name}\n{desc}"))
        view.add_item(container)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.command(name="slowmode", description="Set slowmode")
    @is_staff()
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            await interaction.response.send_message(view=onyx_embed_view("🐢 Slowmode", f"Slowmode set to `{seconds}s` in {interaction.channel.mention}"))
        except Exception as e:
            await interaction.response.send_message(view=onyx_embed_view("Error", str(e), 0xFF0000), ephemeral=True)

    @app_commands.command(name="lock", description="Lock the channel")
    @is_staff()
    async def lock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(view=onyx_embed_view("🔒 Channel Locked", f"{interaction.channel.mention} locked by {interaction.user.mention}"))

    @app_commands.command(name="unlock", description="Unlock the channel")
    @is_staff()
    async def unlock(self, interaction: discord.Interaction):
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message(view=onyx_embed_view("🔓 Channel Unlocked", f"{interaction.channel.mention} unlocked by {interaction.user.mention}"))

async def setup(bot):
    await bot.add_cog(Moderation(bot))