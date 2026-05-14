import discord
from discord.ext import commands
from discord import app_commands
from config import LEVEL_NAMES, LEVEL_COLORS
from permissions import level_to_name, level_to_color

class AuthCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="active", description="Activate your license key")
    @app_commands.describe(license_key="Your license key to activate")
    async def active(self, interaction: discord.Interaction, license_key: str):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        existing = await db.get_user(str(interaction.user.id))
        if existing:
            embed = discord.Embed(
                title="Already Active",
                description=f"You are already linked as **{level_to_name(existing['level'])}**.\n"
                            f"License: `{existing['license_key'][:16]}...`\n"
                            f"Use `/unlink` first if you want to change accounts.",
                color=level_to_color(existing["level"]),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        lic = await db.get_license(license_key)
        if not lic:
            embed = discord.Embed(
                title="Invalid Key",
                description="This license key does not exist in our database.\n"
                            "Contact an admin or use the desktop tool to link via OAuth2.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        if lic["status"] != "active":
            embed = discord.Embed(
                title="Key Not Active",
                description=f"This license is **{lic['status']}**. Contact an admin.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        assigned_to = lic["issued_to_discord_id"]
        if assigned_to and assigned_to != str(interaction.user.id):
            embed = discord.Embed(
                title="Key Already Used",
                description="This license key is already linked to another Discord account.",
                color=0xFF0000,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        await db.add_user(
            str(interaction.user.id), license_key,
            lic["level"], lic["subscription_name"], lic["expires_at"],
        )
        await db.update_discord_name(str(interaction.user.id), str(interaction.user))
        await db.add_log(str(interaction.user.id), "activate",
                         f"Activated: {lic['subscription_name']} ({license_key[:12]}...)")

        embed = discord.Embed(
            title="License Activated!",
            description=f"Welcome **{interaction.user.name}**!\n"
                        f"Role: **{level_to_name(lic['level'])}**\n"
                        f"Use `/help` to see your commands.\n\n"
                        f"Want the desktop tool? Use `/sync` to get a code.",
            color=level_to_color(lic["level"]),
        )
        embed.set_footer(text="Titan Manager Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="unlink", description="Unlink your Discord from the current license")
    async def unlink(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        user = await db.get_user(str(interaction.user.id))
        if not user:
            embed = discord.Embed(
                title="Not Linked",
                description="Nothing to unlink. Use `/active <key>` or the desktop tool.",
                color=0xFF6600,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        license_key = user["license_key"]
        await db.remove_user(str(interaction.user.id))
        await db.update_license_status(license_key, "active")
        await db.add_log(str(interaction.user.id), "unlink",
                         f"Unlinked: {user['subscription_name']} ({license_key[:12]}...)")

        embed = discord.Embed(
            title="Unlinked",
            description=f"Your Discord has been unlinked from **{user['subscription_name']}**.\n"
                        f"The license key is now free to use with another account.",
            color=0x00FF00,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="View your linked account info")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        user = await db.get_user(str(interaction.user.id))
        if not user:
            embed = discord.Embed(
                title="Not Linked",
                description="You haven't linked your account yet.\n"
                            "Use `/active <license_key>` or link via the desktop tool.",
                color=0xFF6600,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        linked_via = "OAuth2" if user["linked"] else "Manual"
        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Profile",
            color=level_to_color(user["level"]),
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="License Key", value=f"`{user['license_key'][:16]}...`", inline=False)
        embed.add_field(name="Role", value=level_to_name(user["level"]), inline=True)
        embed.add_field(name="Level", value=str(user["level"]), inline=True)
        embed.add_field(name="Subscription", value=user["subscription_name"], inline=True)
        embed.add_field(name="Linked Via", value=linked_via, inline=True)
        if user["registered_at"]:
            embed.add_field(name="Since", value=user["registered_at"][:10], inline=True)
        if user["expires_at"]:
            embed.add_field(name="Expires", value=user["expires_at"][:10], inline=True)
        embed.add_field(name="Last Login", value=user["last_login"][:19] if user["last_login"] else "Never", inline=False)
        embed.set_footer(text="Titan Manager Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AuthCog(bot))
