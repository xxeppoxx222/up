import os
import discord
from discord.ext import commands
import asyncio
import logging
import secrets
from datetime import datetime, timedelta
import aiohttp
from aiohttp import web

os.makedirs("data", exist_ok=True)

from config import (
    DISCORD_TOKEN, HTTP_PORT, OAUTH2_CLIENT_ID, OAUTH2_CLIENT_SECRET,
    OAUTH2_REDIRECT_URI, OAUTH2_SCOPES, LEVEL_NAMES, LEVEL_COLORS,
)
from database import Database
from keyauth_client import KeyAuthClient
from permissions import level_to_name, level_to_color

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('data/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

SUCCESS_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Linked!</title>
<style>
body {{ background: #0d0d1a; color: #fff; font-family: 'Segoe UI',sans-serif; display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center }}
.card {{ background:#1a1a2e;padding:40px;border-radius:16px;border:1px solid #e6b800;max-width:400px }}
.check {{ font-size:64px;color:#00ff88;margin-bottom:10px }}
.role {{ color:#e6b800;font-weight:bold;font-size:18px }}
.discord {{ color:#5865F2;font-weight:bold }}
</style></head><body>
<div class="card">
<div class="check">&#10003;</div>
<h2>Linked Successfully!</h2>
<p>Discord: <span class="discord">{discord_name}</span></p>
<p>Role: <span class="role">{role}</span></p>
<p style="color:#888;font-size:13px;margin-top:20px">You can close this tab and return to the tool.</p>
</div></body></html>"""

ERROR_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Error</title>
<style>
body {{ background:#0d0d1a;color:#fff;font-family:'Segoe UI',sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center }}
.card {{ background:#1a1a2e;padding:40px;border-radius:16px;border:1px solid #ff4444;max-width:400px }}
.err {{ font-size:64px;color:#ff4444;margin-bottom:10px }}
</style></head><body>
<div class="card">
<div class="err">&#10007;</div>
<h2>{title}</h2>
<p style="color:#aaa">{message}</p>
</div></body></html>"""

class TitanBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="/",
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.watching, name="Titan Manager"),
        )
        self.db = Database()
        self.keyauth = KeyAuthClient()
        self.start_time = datetime.utcnow()
        self.uptime_str = "0d 0h 0m"
        self.oauth_sessions = {}
        self._oauth_lock = asyncio.Lock()
        self.http_runner = None

    async def setup_hook(self):
        log.info("Loading cogs...")
        for cog in ("cogs.auth_cog", "cogs.admin_cog", "cogs.staff_cog", "cogs.user_cog"):
            try:
                await self.load_extension(cog)
                log.info(f"Loaded {cog}")
            except Exception as e:
                log.error(f"Failed to load {cog}: {e}")

        log.info("Syncing commands...")
        await self.tree.sync()
        log.info(f"Synced {len(self.tree.get_commands())} commands")

        await self._start_http()

    async def _start_http(self):
        log.info("Starting HTTP server on port %d...", HTTP_PORT)
        try:
            app = web.Application()
            app.router.add_get("/auth/discord", self.handle_oauth_begin)
            app.router.add_get("/auth/callback", self.handle_oauth_callback)
            app.router.add_get("/api/link-status", self.handle_link_status)
            app.router.add_post("/api/code-claim", self.handle_code_claim)
            app.router.add_get("/api/health", self.handle_health)
            app.router.add_get("/", self.handle_root)
            self.http_runner = web.AppRunner(app)
            await self.http_runner.setup()
            site = web.TCPSite(self.http_runner, "0.0.0.0", HTTP_PORT)
            await site.start()
            log.info("HTTP server running on 0.0.0.0:%d", HTTP_PORT)
        except Exception as e:
            log.warning("Failed to start HTTP server: %s", e)

    async def on_ready(self):
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.start_time = datetime.utcnow()

    async def close(self):
        if self.http_runner:
            try:
                await self.http_runner.cleanup()
            except: pass
        await self.keyauth.close()
        await super().close()

    async def handle_root(self, request):
        return web.Response(text="Titan Manager Bot is running.", content_type="text/plain")

    async def handle_health(self, request):
        uptime = datetime.utcnow() - self.start_time
        self.uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds // 60) % 60}m"
        return web.json_response({
            "status": "ok",
            "uptime": self.uptime_str,
            "commands": len(self.tree.get_commands()),
            "oauth_sessions": len(self.oauth_sessions),
        })

    async def handle_oauth_begin(self, request):
        license_key = request.query.get("license_key", "").strip()
        if not license_key:
            return web.Response(text=ERROR_HTML.format(title="Missing License", message="No license key provided."),
                                content_type="text/html", status=400)

        if not OAUTH2_CLIENT_ID or not OAUTH2_CLIENT_SECRET:
            return web.Response(
                text=ERROR_HTML.format(title="OAuth2 Not Configured",
                                       message="Bot owner must set OAUTH2_CLIENT_ID and OAUTH2_CLIENT_SECRET in config.py"),
                content_type="text/html", status=500)

        session_id = secrets.token_urlsafe(32)
        async with self._oauth_lock:
            self.oauth_sessions[session_id] = {
                "license_key": license_key,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "discord_id": None,
                "discord_name": None,
            }

        self._clean_old_sessions()

        oauth_url = (
            f"https://discord.com/api/oauth2/authorize"
            f"?client_id={OAUTH2_CLIENT_ID}"
            f"&redirect_uri={OAUTH2_REDIRECT_URI}"
            f"&response_type=code"
            f"&scope={OAUTH2_SCOPES}"
            f"&state={session_id}"
        )
        raise web.HTTPFound(location=oauth_url)

    async def handle_oauth_callback(self, request):
        code = request.query.get("code", "")
        state = request.query.get("state", "")

        if not code or not state:
            return web.Response(
                text=ERROR_HTML.format(title="Invalid Request", message="Missing code or state parameter."),
                content_type="text/html", status=400)

        async with self._oauth_lock:
            session = self.oauth_sessions.get(state)
            if not session:
                return web.Response(
                    text=ERROR_HTML.format(title="Session Expired",
                                           message="This linking session expired or is invalid. Go back to the tool and try again."),
                    content_type="text/html", status=400)

        license_key = session["license_key"]

        try:
            async with aiohttp.ClientSession() as sess:
                token_data = await sess.post(
                    "https://discord.com/api/oauth2/token",
                    data={
                        "client_id": OAUTH2_CLIENT_ID,
                        "client_secret": OAUTH2_CLIENT_SECRET,
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": OAUTH2_REDIRECT_URI,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                token_json = await token_data.json()
                if "access_token" not in token_json:
                    log.error(f"OAuth token error: {token_json}")
                    return web.Response(
                        text=ERROR_HTML.format(title="Authorization Failed",
                                               message="Discord did not return an access token. Try again."),
                        content_type="text/html", status=400)

                access_token = token_json["access_token"]
                user_resp = await sess.get(
                    "https://discord.com/api/users/@me",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                user_data = await user_resp.json()
                discord_id = str(user_data["id"])
                discord_name = f"{user_data['username']}#{user_data.get('discriminator', '0')}"

            existing = await self.db.get_user(discord_id)
            if existing:
                return web.Response(
                    text=ERROR_HTML.format(title="Already Linked",
                                           message=f"**{discord_name}** is already linked to a license. Contact an admin to unlink."),
                    content_type="text/html", status=400)

            lic = await self.db.get_license(license_key)
            if lic:
                level, sub_name = lic["level"], lic["subscription_name"]
            else:
                level, sub_name = 6, "Tool Member"
                await self.db.add_license(license_key, level, sub_name)

            await self.db.link_user(discord_id, license_key, level, sub_name)
            await self.db.update_discord_name(discord_id, discord_name)
            await self.db.add_log(discord_id, "oauth_link",
                                  f"Linked via OAuth2: {sub_name} (key: {license_key[:12]}...)")

            async with self._oauth_lock:
                session["status"] = "linked"
                session["discord_id"] = discord_id
                session["discord_name"] = discord_name

            role_name = level_to_name(level)
            html = SUCCESS_HTML.format(discord_name=discord_name, role=role_name)
            return web.Response(text=html, content_type="text/html")

        except Exception as e:
            log.exception("OAuth callback error")
            return web.Response(
                text=ERROR_HTML.format(title="Error", message=f"An error occurred: {str(e)}"),
                content_type="text/html", status=500)

    async def handle_link_status(self, request):
        license_key = request.query.get("license_key", "").strip()
        if not license_key:
            return web.json_response({"success": False, "message": "Missing license_key"}, status=400)

        user = await self.db.get_user_by_license(license_key)
        if user:
            return web.json_response({
                "success": True,
                "status": "linked",
                "discord_id": user["discord_id"],
                "discord_name": user["discord_name"] or "Unknown",
                "level": user["level"],
                "subscription_name": user["subscription_name"],
            })

        async with self._oauth_lock:
            for sid, sess in self.oauth_sessions.items():
                if sess["license_key"] == license_key and sess["status"] == "linked":
                    return web.json_response({
                        "success": True,
                        "status": "linked",
                        "discord_id": sess["discord_id"],
                        "discord_name": sess["discord_name"] or "Unknown",
                        "level": 0,
                    })

        return web.json_response({"success": True, "status": "pending"})

    async def handle_code_claim(self, request):
        try:
            data = await request.json()
        except:
            return web.json_response({"success": False, "message": "Invalid JSON"}, status=400)

        code = data.get("code", "").strip().upper()
        license_key = data.get("license_key", "").strip()
        if not code or not license_key:
            return web.json_response({"success": False, "message": "Missing code or license_key"}, status=400)

        sync = await self.db.get_sync_code(code)
        if not sync:
            return web.json_response({"success": False, "message": "Invalid code"}, status=400)

        if sync["used"]:
            return web.json_response({"success": False, "message": "Code already used"}, status=400)

        from datetime import datetime
        exp = datetime.fromisoformat(sync["expires_at"])
        if exp < datetime.utcnow():
            return web.json_response({"success": False, "message": "Code expired"}, status=400)

        discord_id = sync["discord_id"]

        lic = await self.db.get_license(license_key)
        if lic:
            level, sub_name = lic["level"], lic["subscription_name"]
        else:
            level, sub_name = 6, "Tool Member"
            await self.db.add_license(license_key, level, sub_name)

        await self.db.link_user(discord_id, license_key, level, sub_name)
        await self.db.claim_sync_code(code, license_key, discord_id)
        await self.db.add_log(discord_id, "sync_claim",
                              f"Claimed via sync code: {sub_name} ({license_key[:12]}...)")

        return web.json_response({
            "success": True,
            "message": f"Linked as {level_to_name(level)}",
            "discord_id": discord_id,
            "level": level,
            "subscription_name": sub_name,
        })

    def _clean_old_sessions(self):
        now = datetime.utcnow()
        expired = [k for k, v in self.oauth_sessions.items()
                   if v["status"] == "pending" and (now - v["created_at"]).total_seconds() > 300]
        for k in expired:
            self.oauth_sessions.pop(k, None)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        log.error(f"Command error: {error}")

async def main():
    bot = TitanBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
