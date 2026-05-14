import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from config import LEVEL_NAMES, LEVEL_COLORS
from permissions import high_staff_plus, mid_staff_plus, level_to_name, level_to_color

class StaffCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stats", description="View bot statistics (Mid Staff+)")
    @mid_staff_plus()
    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        users = await db.get_all_users()
        licenses = await db.get_all_licenses()

        online = sum(1 for u in users)
        active_licenses = sum(1 for l in licenses if l["status"] == "active")
        by_level = {}
        for u in users:
            lvl = u["level"]
            by_level[lvl] = by_level.get(lvl, 0) + 1

        embed = discord.Embed(
            title="Bot Statistics",
            color=0x1E90FF,
        )
        embed.add_field(name="Total Users", value=str(len(users)), inline=True)
        embed.add_field(name="Active Licenses", value=str(active_licenses), inline=True)
        embed.add_field(name="Total Licenses", value=str(len(licenses)), inline=True)
        embed.add_field(name="Uptime", value=self.bot.uptime_str if hasattr(self.bot, 'uptime_str') else "N/A", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)

        breakdown = "\n".join(
            f"{level_to_name(lvl)}: {count}"
            for lvl, count in sorted(by_level.items())
        )
        embed.add_field(name="Users by Level", value=breakdown or "None", inline=False)
        embed.set_footer(text="Titan Manager Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="broadcast", description="Send an announcement to all registered users (High Staff+)")
    @high_staff_plus()
    @app_commands.describe(message="The announcement message to send")
    async def broadcast(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        users = await db.get_all_users()
        sent = 0
        failed = 0

        embed = discord.Embed(
            title="Announcement",
            description=message,
            color=0xFFD700,
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="Titan Manager Bot")

        for user in users:
            try:
                member = await self.bot.fetch_user(int(user["discord_id"]))
                await member.send(embed=embed)
                sent += 1
            except:
                failed += 1

        await db.add_log(str(interaction.user.id), "broadcast",
                         f"Sent to {sent} users ({failed} failed): {message[:50]}...")

        result = discord.Embed(
            title="Broadcast Complete",
            description=f"\u2705 Sent to **{sent}** users\n"
                        f"\u274C Failed: **{failed}** users",
            color=0x00FF00,
        )
        await interaction.followup.send(embed=result, ephemeral=True)

    @app_commands.command(name="devices", description="View connected tool devices (Mid Staff+)")
    @mid_staff_plus()
    async def devices(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        users = await db.get_all_users()

        if not users:
            embed = discord.Embed(title="No Devices", description="No linked tool devices found.", color=0xFFAA00)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        lines = []
        for u in users[:25]:
            linked = "\u2705" if u["linked"] else "\u274C"
            name = u["discord_name"] or f"<@{u['discord_id']}>"
            lines.append(f"{linked} {name} | {level_to_name(u['level'])} | {u['last_login'][:10] if u['last_login'] else 'Never'}")

        embed = discord.Embed(
            title=f"Devices ({len(users)})",
            description="\n".join(lines),
            color=0x1E90FF,
        )
        embed.add_field(name="Online", value=f"{sum(1 for u in users if u['linked'])}", inline=True)
        embed.add_field(name="Offline", value=f"{sum(1 for u in users if not u['linked'])}", inline=True)
        if len(users) > 25:
            embed.set_footer(text=f"Showing 25 of {len(users)} devices")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="logs", description="View recent bot logs (High Staff+)")
    @high_staff_plus()
    @app_commands.describe(limit="Number of log entries to show (default 20)")
    async def logs(self, interaction: discord.Interaction, limit: int = 20):
        await interaction.response.defer(ephemeral=True)
        db = self.bot.db
        logs = await db.get_logs(min(limit, 100))

        if not logs:
            embed = discord.Embed(title="No Logs", description="No log entries found.", color=0xFFAA00)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        lines = []
        for log in logs[:25]:
            ts = log["timestamp"][:19] if log["timestamp"] else "N/A"
            uid = log["discord_id"] or "N/A"
            action = log["action"]
            details = (log["details"] or "")[:30]
            lines.append(f"`{ts}` <@{uid}> **{action}** {details}")

        embed = discord.Embed(
            title=f"Recent Logs ({len(logs)})",
            description="\n".join(lines),
            color=0x1E90FF,
        )
        embed.set_footer(text="Titan Manager Bot")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StaffCog(bot))
