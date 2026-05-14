import aiosqlite
import os
from datetime import datetime, timedelta
from config import DATABASE_PATH

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.conn = None
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def connect(self):
        if self.conn is not None:
            return
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                discord_id TEXT PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                level INTEGER NOT NULL DEFAULT 6,
                subscription_name TEXT DEFAULT 'Tool Member',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_login TIMESTAMP,
                discord_name TEXT,
                linked INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS licenses (
                key TEXT PRIMARY KEY,
                level INTEGER NOT NULL,
                subscription_name TEXT NOT NULL,
                issued_to_discord_id TEXT,
                issued_by_discord_id TEXT,
                issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                status TEXT DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS link_codes (
                code TEXT PRIMARY KEY,
                discord_id TEXT,
                license_key TEXT,
                subscription_name TEXT,
                level INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                used INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sync_codes (
                code TEXT PRIMARY KEY,
                discord_id TEXT NOT NULL,
                license_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                used INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discord_id TEXT,
                action TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS bot_config (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()
            self.conn = None

    async def add_user(self, discord_id, license_key, level, subscription_name, expires_at=None):
        await self.connect()
        await self.conn.execute(
            "INSERT OR REPLACE INTO users (discord_id, license_key, level, subscription_name, expires_at, last_login, linked) VALUES (?, ?, ?, ?, ?, ?, 1)",
            (discord_id, license_key, level, subscription_name, expires_at, datetime.utcnow().isoformat())
        )
        await self.conn.commit()

    async def get_user(self, discord_id):
        await self.connect()
        cur = await self.conn.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
        return await cur.fetchone()

    async def get_user_by_license(self, license_key):
        await self.connect()
        cur = await self.conn.execute("SELECT * FROM users WHERE license_key = ?", (license_key,))
        return await cur.fetchone()

    async def remove_user(self, discord_id):
        await self.connect()
        await self.conn.execute("DELETE FROM users WHERE discord_id = ?", (discord_id,))
        await self.conn.commit()

    async def update_last_login(self, discord_id):
        await self.connect()
        await self.conn.execute("UPDATE users SET last_login = ? WHERE discord_id = ?",
                                (datetime.utcnow().isoformat(), discord_id))
        await self.conn.commit()

    async def update_discord_name(self, discord_id, name):
        await self.connect()
        await self.conn.execute("UPDATE users SET discord_name = ? WHERE discord_id = ?", (name, discord_id))
        await self.conn.commit()

    async def get_all_users(self):
        await self.connect()
        cur = await self.conn.execute("SELECT * FROM users ORDER BY level ASC, registered_at DESC")
        return await cur.fetchall()

    async def add_license(self, key, level, subscription_name, issued_by=None, expires_at=None):
        await self.connect()
        await self.conn.execute(
            "INSERT OR REPLACE INTO licenses (key, level, subscription_name, issued_by_discord_id, expires_at) VALUES (?, ?, ?, ?, ?)",
            (key, level, subscription_name, issued_by, expires_at)
        )
        await self.conn.commit()

    async def get_license(self, key):
        await self.connect()
        cur = await self.conn.execute("SELECT * FROM licenses WHERE key = ?", (key,))
        return await cur.fetchone()

    async def update_license_status(self, key, status):
        await self.connect()
        await self.conn.execute("UPDATE licenses SET status = ? WHERE key = ?", (status, key))
        await self.conn.commit()

    async def get_all_licenses(self):
        await self.connect()
        cur = await self.conn.execute("SELECT * FROM licenses ORDER BY issued_at DESC")
        return await cur.fetchall()

    async def link_user(self, discord_id, license_key, level, subscription_name):
        await self.connect()
        user = await self.get_user(discord_id)
        if user:
            await self.conn.execute(
                "UPDATE users SET license_key = ?, level = ?, subscription_name = ?, linked = 1, last_login = ? WHERE discord_id = ?",
                (license_key, level, subscription_name, datetime.utcnow().isoformat(), discord_id)
            )
        else:
            await self.add_user(discord_id, license_key, level, subscription_name)
        await self.conn.commit()

    async def create_link_code(self, code, license_key, subscription_name, level):
        await self.connect()
        await self.conn.execute(
            "INSERT INTO link_codes (code, license_key, subscription_name, level, expires_at) VALUES (?, ?, ?, ?, ?)",
            (code, license_key, subscription_name, level, (datetime.utcnow() + timedelta(minutes=5)).isoformat())
        )
        await self.conn.commit()

    async def get_link_code(self, code):
        await self.connect()
        cur = await self.conn.execute("SELECT * FROM link_codes WHERE code = ?", (code,))
        return await cur.fetchone()

    async def use_link_code(self, code, discord_id):
        await self.connect()
        await self.conn.execute("UPDATE link_codes SET used = 1, discord_id = ? WHERE code = ?", (discord_id, code))
        await self.conn.commit()

    async def create_sync_code(self, code, discord_id):
        await self.connect()
        await self.conn.execute(
            "INSERT INTO sync_codes (code, discord_id, expires_at) VALUES (?, ?, ?)",
            (code, discord_id, (datetime.utcnow() + timedelta(minutes=5)).isoformat())
        )
        await self.conn.commit()

    async def get_sync_code(self, code):
        await self.connect()
        cur = await self.conn.execute("SELECT * FROM sync_codes WHERE code = ?", (code,))
        return await cur.fetchone()

    async def claim_sync_code(self, code, license_key, discord_id):
        await self.connect()
        await self.conn.execute(
            "UPDATE sync_codes SET used = 1, license_key = ? WHERE code = ?",
            (license_key, code)
        )
        await self.conn.commit()

    async def add_log(self, discord_id, action, details=""):
        await self.connect()
        await self.conn.execute(
            "INSERT INTO logs (discord_id, action, details) VALUES (?, ?, ?)",
            (discord_id, action, details)
        )
        await self.conn.commit()

    async def get_logs(self, limit=50):
        await self.connect()
        cur = await self.conn.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        return await cur.fetchall()

    async def get_config(self, key):
        await self.connect()
        cur = await self.conn.execute("SELECT value FROM bot_config WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else None

    async def set_config(self, key, value):
        await self.connect()
        await self.conn.execute("INSERT OR REPLACE INTO bot_config (key, value) VALUES (?, ?)", (key, value))
        await self.conn.commit()
