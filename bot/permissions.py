import discord
from discord import app_commands
from config import LEVEL_NAMES, LEVEL_COLORS

SUB_MAP = {
    "owner": 1,
    "founder": 2,
    "high staff": 3,
    "mid staff": 4,
    "tool staff": 5,
    "tool member": 6,
}

def subscription_to_level(sub_name):
    return SUB_MAP.get(sub_name.lower().strip(), 6)

def level_to_name(level):
    return LEVEL_NAMES.get(level, f"Level {level}")

def level_to_color(level):
    return LEVEL_COLORS.get(level, 0x99AAB5)

def check_level(required_level):
    async def predicate(interaction: discord.Interaction):
        bot = interaction.client
        db = bot.db
        user = await db.get_user(str(interaction.user.id))
        if not user:
            embed = discord.Embed(
                title="Account Not Linked",
                description=(
                    "You need to link your Discord to use commands.\n\n"
                    "**Option 1:** Have a license key?\n"
                    "Use `/active <license_key>`\n\n"
                    "**Option 2:** Using the desktop tool?\n"
                    "Open the tool → Config tab → **LINK DISCORD**\n"
                    "Authorize in your browser — done!"
                ),
                color=0xFF6600,
            )
            embed.set_footer(text="Titan Manager Bot")
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
            return False

        user_level = user["level"]
        if user_level > required_level:
            embed = discord.Embed(
                title="Insufficient Permissions",
                description=f"Your level `{level_to_name(user_level)}` cannot use this command.\n"
                            f"Required: `{level_to_name(required_level)}` or higher.",
                color=0xFF0000,
            )
            try:
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                await interaction.followup.send(embed=embed, ephemeral=True)
            return False

        from datetime import datetime
        expiry = user["expires_at"]
        if expiry:
            try:
                exp = datetime.fromisoformat(expiry)
                if exp < datetime.utcnow():
                    embed = discord.Embed(
                        title="License Expired",
                        description="Your license has expired. Contact an admin to renew.",
                        color=0xFF0000,
                    )
                    try:
                        await interaction.response.send_message(embed=embed, ephemeral=True)
                    except:
                        await interaction.followup.send(embed=embed, ephemeral=True)
                    return False
            except ValueError:
                pass

        return True
    return app_commands.check(predicate)

def owner_only():
    return check_level(1)
def founder_plus():
    return check_level(2)
def high_staff_plus():
    return check_level(3)
def mid_staff_plus():
    return check_level(4)
def tool_staff_plus():
    return check_level(5)
def member_plus():
    return check_level(6)
