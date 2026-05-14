import discord
from discord.ext import commands
from discord import app_commands
import random
import string
from datetime import datetime, timedelta
from config import LEVEL_NAMES, LEVEL_COLORS
from permissions import owner_only, founder_plus, check_level, subscription_to_level, level_to_name, level_to_color

def generate_key():
    return f"TITAN-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    license_group = app_commands.Group(name="license", description="License management commands")
    users_group = app_commands.Group(name="users", description="User management commands")

    @license_group.command(name="issue", description="Issue a new license key (Founder+)")
    @founder_plus()
    @app_commands.describe(
        user="Discord user to assign the license to (optional)",
        level="Permission level (1-6)",
        days="Number of days until expiry (0 = never)",
    )
    async def license_issue(self, interaction: discord.Interaction, level: int, days: int = 30, user: discord.User = None):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        caller = await db.get_user(str(interaction.user.id))
        if caller["level"] > level:
            embed = discord.Embed(
                title="Cannot Issue",
                description="You cannot issue a license with a level higher than or equal to your own.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        key = generate_key()
        sub_name = level_to_name(level)
        expires = (datetime.utcnow() + timedelta(days=days)).isoformat() if days > 0 else None

        await db.add_license(key, level, sub_name, str(interaction.user.id), expires)

        if user:
            await db.update_license_status(key, "active")
            await db.add_user(str(user.id), key, level, sub_name, expires)
            await db.add_log(str(interaction.user.id), "license_issue",
                             f"Issued {sub_name} to {user.name} ({user.id}), key: {key}")

            try:
                dm = discord.Embed(
                    title="License Issued",
                    description=f"You have been assigned **{sub_name}**!\n"
                                f"Key: `{key}`\n"
                                f"Use `/active {key}` to activate.",
                    color=level_to_color(level),
                )
                if expires:
                    dm.add_field(name="Expires", value=expires[:10])
                await user.send(embed=dm)
            except:
                pass

        embed = discord.Embed(
            title="License Issued",
            description=f"**Level:** {sub_name} ({level})\n"
                        f"**Key:** `{key}`\n"
                        f"**Duration:** {'%d days' % days if days > 0 else 'Never'}\n"
                        f"**Assigned to:** {user.mention if user else 'Unassigned'}",
            color=level_to_color(level),
        )
        embed.set_footer(text="Titan Manager Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @license_group.command(name="revoke", description="Revoke a license key (Founder+)")
    @founder_plus()
    @app_commands.describe(license_key="The license key to revoke")
    async def license_revoke(self, interaction: discord.Interaction, license_key: str):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        lic = await db.get_license(license_key)
        if not lic:
            embed = discord.Embed(title="Not Found", description="License key not found.", color=0xFF0000)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await db.update_license_status(license_key, "revoked")

        user_data = await db.get_user_by_license(license_key)
        if user_data:
            await db.remove_user(user_data["discord_id"])

        await db.add_log(str(interaction.user.id), "license_revoke", f"Revoked {license_key}")

        embed = discord.Embed(
            title="License Revoked",
            description=f"Key `{license_key[:16]}...` has been revoked.\n"
                        f"User has been removed from the bot.",
            color=0xFF0000,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @license_group.command(name="info", description="Get info about a license key (Founder+)")
    @founder_plus()
    @app_commands.describe(license_key="The license key")
    async def license_info(self, interaction: discord.Interaction, license_key: str):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        lic = await db.get_license(license_key)
        if not lic:
            embed = discord.Embed(title="Not Found", description="License key not found.", color=0xFF0000)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(
            title="License Info",
            color=level_to_color(lic["level"]),
        )
        embed.add_field(name="Key", value=f"`{lic['key']}`", inline=False)
        embed.add_field(name="Level", value=level_to_name(lic["level"]), inline=True)
        embed.add_field(name="Status", value=lic["status"].upper(), inline=True)
        embed.add_field(name="Subscription", value=lic["subscription_name"], inline=True)
        embed.add_field(name="Issued At", value=lic["issued_at"][:10] if lic["issued_at"] else "N/A", inline=True)
        embed.add_field(name="Expires At", value=lic["expires_at"][:10] if lic["expires_at"] else "Never", inline=True)
        if lic["issued_to_discord_id"]:
            embed.add_field(name="Assigned To", value=f"<@{lic['issued_to_discord_id']}>", inline=True)
        embed.set_footer(text="Titan Manager Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @license_group.command(name="list", description="List all license keys (Founder+)")
    @founder_plus()
    async def license_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        licenses = await db.get_all_licenses()
        if not licenses:
            embed = discord.Embed(title="No Licenses", description="No licenses in the database.", color=0xFFAA00)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        lines = []
        for lic in licenses[:25]:
            status_emoji = "\u2705" if lic["status"] == "active" else "\u274C"
            lines.append(f"{status_emoji} `{lic['key'][:16]}...` | {level_to_name(lic['level'])} | {lic['status']}")

        embed = discord.Embed(
            title=f"Licenses ({len(licenses)})",
            description="\n".join(lines),
            color=0x1E90FF,
        )
        if len(licenses) > 25:
            embed.set_footer(text=f"Showing 25 of {len(licenses)} licenses")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @users_group.command(name="list", description="List all registered users (Founder+)")
    @founder_plus()
    async def users_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        users = await db.get_all_users()
        if not users:
            embed = discord.Embed(title="No Users", description="No registered users.", color=0xFFAA00)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        lines = []
        for u in users[:25]:
            name = u["discord_name"] or f"<@{u['discord_id']}>"
            lines.append(f"{level_to_name(u['level'])} | {name} | `{u['license_key'][:12]}...`")

        embed = discord.Embed(
            title=f"Users ({len(users)})",
            description="\n".join(lines),
            color=0x1E90FF,
        )
        if len(users) > 25:
            embed.set_footer(text=f"Showing 25 of {len(users)} users")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @users_group.command(name="remove", description="Remove a user from the bot (Owner only)")
    @owner_only()
    @app_commands.describe(user="Discord user to remove")
    async def users_remove(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        target = await db.get_user(str(user.id))
        if not target:
            embed = discord.Embed(title="Not Found", description="User not registered.", color=0xFF0000)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        caller = await db.get_user(str(interaction.user.id))
        if caller and caller["level"] >= target["level"]:
            embed = discord.Embed(
                title="Cannot Remove",
                description="You cannot remove a user with a level equal to or higher than yours.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        license_key = target["license_key"]
        await db.remove_user(str(user.id))
        await db.update_license_status(license_key, "active")
        await db.add_log(str(interaction.user.id), "user_remove", f"Removed {user.name} ({user.id})")

        embed = discord.Embed(
            title="User Removed",
            description=f"**{user.name}** has been removed.\nTheir license has been freed.",
            color=0x00FF00,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="shutdown", description="Shutdown the bot (Owner only)")
    @owner_only()
    async def shutdown(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        await db.add_log(str(interaction.user.id), "shutdown", "Bot shutdown initiated")

        embed = discord.Embed(
            title="Shutting Down",
            description="Bot will shut down now.",
            color=0xFF0000,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

        await self.bot.close()

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
