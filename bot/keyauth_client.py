import aiohttp
import hashlib
import platform
import uuid
from config import KEYAUTH_API_URL, KEYAUTH_OWNER_ID, KEYAUTH_APP_NAME, KEYAUTH_SECRET, KEYAUTH_VERSION

class KeyAuthClient:
    def __init__(self):
        self.session_id = None
        self.session = None

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    def _build_enckey(self):
        return hashlib.sha256(f"{KEYAUTH_APP_NAME}{KEYAUTH_OWNER_ID}{KEYAUTH_SECRET}".encode()).hexdigest()

    def _build_iv(self):
        return hashlib.sha256(f"{KEYAUTH_OWNER_ID}{KEYAUTH_APP_NAME}".encode()).hexdigest()[:16]

    async def init(self):
        await self._ensure_session()
        enckey = self._build_enckey()
        payload = {
            "type": "init",
            "ownerid": KEYAUTH_OWNER_ID,
            "appname": KEYAUTH_APP_NAME,
            "version": KEYAUTH_VERSION,
            "hash": enckey,
        }
        async with self.session.post(KEYAUTH_API_URL, data=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json()
            if data.get("success"):
                self.session_id = data["sessionid"]
            return data

    async def verify_license(self, license_key):
        await self._ensure_session()
        if not self.session_id:
            init_data = await self.init()
            if not init_data.get("success"):
                return {"success": False, "message": "Failed to initialize KeyAuth"}

        payload = {
            "type": "license",
            "key": license_key,
            "hwid": hashlib.sha256(f"DISCORD_BOT_{KEYAUTH_OWNER_ID}".encode()).hexdigest(),
            "sessionid": self.session_id,
            "ownerid": KEYAUTH_OWNER_ID,
            "appname": KEYAUTH_APP_NAME,
        }
        async with self.session.post(KEYAUTH_API_URL, data=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            data = await resp.json()
            return data

    async def get_subscription_info(self, license_key):
        data = await self.verify_license(license_key)
        if data.get("success") and "info" in data:
            info = data["info"]
            subs = info.get("subscriptions", [])
            if subs:
                sub = subs[0]
                return {
                    "success": True,
                    "subscription": sub.get("subscription", "Tool Member"),
                    "expiry": sub.get("expiry", ""),
                }
        return {"success": False, "message": data.get("message", "Invalid license")}
