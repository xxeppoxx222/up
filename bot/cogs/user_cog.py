import discord
from discord.ext import commands
from discord import app_commands
import random
import string
from config import LEVEL_NAMES, LEVEL_COLORS
from permissions import level_to_name, level_to_color

class UserCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show available commands")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        user = await db.get_user(str(interaction.user.id))
        if not user:
            embed = discord.Embed(
                title="Titan Manager Bot",
                description=(
                    "You are not linked yet.\n\n"
                    "**Option 1 — Have a license key?**\n"
                    "`/active <license_key>` — Activate here\n\n"
                    "**Option 2 — Using the desktop tool?**\n"
                    "Open the tool → Config → **LINK DISCORD**\n"
                    "Authorize in your browser.\n\n"
                    "**Option 3 — Activated here, want the tool?**\n"
                    "`/sync` — Get a code, enter it in the tool."
                ),
                color=0x1E90FF,
            )
            embed.set_footer(text="Titan Manager Bot")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        level = user["level"]
        cmds = [
            "\u2139\ufe0f **General**",
            "`/active <key>` — Activate license",
            "`/unlink` — Unlink your account",
            "`/profile` — Your account info",
            "`/sync` — Get code for desktop tool",
            "`/ping` — Bot latency",
            "`/help` — This menu",
        ]
        if level <= 4:
            cmds += ["", "\U0001f4ca **Staff**", "`/stats` — Bot statistics", "`/devices` — Connected devices"]
        if level <= 3:
            cmds += ["`/broadcast <msg>` — Announcement to all", "`/logs` — Activity logs"]
        if level <= 2:
            cmds += ["", "\U0001f4cb **Admin**", "`/license issue` — Issue a license",
                     "`/license revoke` — Revoke", "`/license info` — License details",
                     "`/license list` — All licenses", "`/users list` — Registered users"]
        if level <= 1:
            cmds += ["`/users remove` — Remove a user", "`/shutdown` — Stop the bot"]

        embed = discord.Embed(
            title=f"Commands \u2014 {level_to_name(level)}",
            description="\n".join(cmds),
            color=level_to_color(level),
        )
        embed.set_footer(text=f"Level {level} \u00b7 Titan Manager Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="ping", description="Check bot latency")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        latency = round(self.bot.latency * 1000)
        color = 0x00FF00 if latency < 200 else (0xFFAA00 if latency < 500 else 0xFF0000)
        embed = discord.Embed(title="Pong!", description=f"Latency: **{latency}ms**", color=color)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="sync", description="Get a code to link the desktop tool to your Discord")
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        user = await db.get_user(str(interaction.user.id))
        if not user:
            embed = discord.Embed(
                title="Not Linked",
                description="Use `/active <key>` first to link your account.",
                color=0xFF6600,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
        await db.create_sync_code(code, str(interaction.user.id))

        embed = discord.Embed(
            title="Sync Code Generated",
            description=(
                f"**Code: `{code}`**\n\n"
                "1. Open the desktop tool\n"
                "2. Go to **Config** tab → **Sync Code**\n"
                "3. Enter this code and click **CLAIM**\n\n"
                "The code expires in **5 minutes**."
            ),
            color=0x1E90FF,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="myinfo", description="Your linked account details")
    async def myinfo(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        user = await db.get_user(str(interaction.user.id))
        if not user:
            embed = discord.Embed(
                title="Not Linked",
                description="Use `/active <key>` or the desktop tool.",
                color=0xFF6600,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title=interaction.user.display_name, color=level_to_color(user["level"]))
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="Discord ID", value=user["discord_id"], inline=False)
        embed.add_field(name="License", value=f"`{user['license_key'][:16]}...`", inline=True)
        embed.add_field(name="Role", value=level_to_name(user["level"]), inline=True)
        embed.add_field(name="Subscription", value=user["subscription_name"], inline=True)
        embed.add_field(name="Linked", value="\u2705 Yes" if user["linked"] else "\u274C No", inline=True)
        if user["registered_at"]:
            embed.add_field(name="Since", value=user["registered_at"][:10], inline=True)
        if user["expires_at"]:
            embed.add_field(name="Expires", value=user["expires_at"][:10], inline=True)
        embed.set_footer(text="Titan Manager Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="tool", description="Link or check tool status")
    @app_commands.describe(action="link or status")
    async def tool(self, interaction: discord.Interaction, action: str):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        user = await db.get_user(str(interaction.user.id))
        if not user:
            embed = discord.Embed(
                title="Not Linked", description="Use `/active <key>` first.", color=0xFF0000)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if action == "link":
            embed = discord.Embed(
                title="Link Desktop Tool",
                description="1. Open the tool\n2. Config → **LINK DISCORD**\n3. Authorize in browser\n\n"
                            "Or use `/sync` for a code to enter in the tool.",
                color=level_to_color(user["level"]),
            )
        elif action == "status":
            embed = discord.Embed(
                title="Tool Status",
                description=f"License: **{user['subscription_name']}**\n"
                            f"Last: {user['last_login'][:19] if user['last_login'] else 'Never'}",
                color=level_to_color(user["level"]),
            )
        else:
            embed = discord.Embed(title="Invalid", description="Use: `link` or `status`", color=0xFF0000)
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCog(bot))
