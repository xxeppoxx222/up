import requests
import json
import os
import time
import base64
import hashlib
from datetime import datetime
import sys
import subprocess
import uuid

class KeyAuthError(Exception):
    pass

class KeyAuthApp:
    def __init__(self, name, ownerid, secret, version):
        self.name = name
        self.ownerid = ownerid
        self.secret = secret
        self.version = version
        self.sessionid = None
        self.user_data = None
        self.api_url = "https://keyauth.win/api/1.2/"
        self._hwid = self._generate_hwid()

    def _generate_hwid(self):
        try:
            system_uuid = subprocess.check_output(
                'wmic csproduct get uuid', shell=True, timeout=5
            ).decode('utf-8').split('\n')[1].strip()
            combined = f"{system_uuid}-{uuid.getnode()}"
            return hashlib.sha256(combined.encode()).hexdigest()
        except:
            fallback = f"{uuid.getnode()}-{os.environ.get('COMPUTERNAME', 'unknown')}"
            return hashlib.sha256(fallback.encode()).hexdigest()

    def _request(self, payload):
        try:
            resp = requests.post(self.api_url, data=payload, timeout=15)
            return resp.json()
        except requests.exceptions.Timeout:
            raise KeyAuthError("Connection timed out. Check your internet.")
        except requests.exceptions.ConnectionError:
            raise KeyAuthError("Failed to connect to KeyAuth servers.")
        except Exception as e:
            raise KeyAuthError(f"KeyAuth communication error: {e}")

    def init(self):
        data = self._request({
            "type": "init",
            "name": self.name,
            "ownerid": self.ownerid,
            "ver": self.version,
            "hwid": self._hwid
        })
        if data.get("success"):
            self.sessionid = data.get("sessionid")
            return True
        raise KeyAuthError(data.get("message", "Initialization failed"))

    def license(self, key):
        if not self.sessionid:
            self.init()
        data = self._request({
            "type": "license",
            "key": key,
            "name": self.name,
            "ownerid": self.ownerid,
            "sessionid": self.sessionid,
            "secret": self.secret,
            "hwid": self._hwid
        })
        if data.get("success"):
            info = data.get("info", {})
            subs = info.get("subscriptions", [])
            raw_expiry = "N/A"
            if subs:
                raw_expiry = subs[0].get("expiry", "N/A")
            elif info.get("expiry"):
                raw_expiry = info["expiry"]
            expiry = raw_expiry
            if raw_expiry not in ("N/A", "") and raw_expiry is not None:
                try:
                    ts = int(raw_expiry)
                    if ts > 10000000000:
                        ts = ts // 1000
                    expiry = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M')
                except (ValueError, TypeError, OSError):
                    expiry = raw_expiry
            level = "Standard"
            if info.get("level"):
                level = info["level"]
            elif subs:
                level = subs[0].get("name", "Standard")
            self.user_data = {
                "username": info.get("username", "User"),
                "expires": expiry,
                "key": key,
                "level": level
            }
            return True
        raise KeyAuthError(data.get("message", "Invalid license key"))

keyauth_app = KeyAuthApp(
    name="Xxeppoxx222's Application",
    ownerid="citOP6ocLC",
    secret="a1daa41df6badc696802b9fad18bc76d00f4877717dc789e8bf0e7a80b8e5cff",
    version="1.0"
)

def _xor_encrypt(data, key="UMAX_SECRET_2024"):
    return base64.b64encode(bytes([ord(c) ^ ord(key[i % len(key)]) for i, c in enumerate(data)])).decode()

def _xor_decrypt(data, key="UMAX_SECRET_2024"):
    try:
        raw = base64.b64decode(data.encode())
        return ''.join(chr(b ^ ord(key[i % len(key)])) for i, b in enumerate(raw))
    except:
        return None

def save_license_key(key):
    try:
        encrypted = _xor_encrypt(key)
        with open("saved_license.json", "w") as f:
            json.dump({"key": encrypted, "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f)
    except: pass

def load_license_key():
    try:
        if os.path.exists("saved_license.json"):
            with open("saved_license.json", "r") as f:
                data = json.load(f)
                return _xor_decrypt(data.get("key", ""))
    except: pass
    return None

def clear_license_key():
    try:
        if os.path.exists("saved_license.json"): os.remove("saved_license.json")
    except: pass
