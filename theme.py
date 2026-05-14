import tkinter as tk
import json
import os
from tkinter import font as tkfont

def resolve_font(preferred, size, weight="normal"):
    try:
        families = [f.lower() for f in tkfont.families()]
        if preferred.lower() in families:
            return (preferred, size, weight)
    except:
        pass
    return ("Segoe UI", size, weight)

THEME_KEYS = ["bg_main", "bg_sidebar", "bg_card", "accent_primary", "accent_secondary",
              "accent_tertiary", "text_main", "text_dim", "success", "error", "warning"]

class ThemeManager:
    def __init__(self):
        self.themes = {}
        self.current_theme_name = "Cyber Neon"
        self.callbacks = []
        self._init_premium_themes()
        self.load_user_preference()

    def _init_premium_themes(self):
        self.themes["Cyber Neon"] = {
            "bg_main": "#050508", "bg_sidebar": "#0D0D14", "bg_card": "#14141F",
            "accent_primary": "#00F5FF", "accent_secondary": "#8A2BE2", "accent_tertiary": "#FF007F",
            "text_main": "#F0F0F5", "text_dim": "#707080", "success": "#00FF9F", "error": "#FF2A6D", "warning": "#FFE600"
        }
        self.themes["Royal Gold"] = {
            "bg_main": "#0F0F0F", "bg_sidebar": "#1A1A1A", "bg_card": "#242424",
            "accent_primary": "#FFD700", "accent_secondary": "#C5A021", "accent_tertiary": "#FF4500",
            "text_main": "#FFFFFF", "text_dim": "#A0A0A0", "success": "#DAA520", "error": "#B22222", "warning": "#FFD700"
        }
        self.themes["Midnight Amethyst"] = {
            "bg_main": "#0A0510", "bg_sidebar": "#140A1F", "bg_card": "#1E0F2E",
            "accent_primary": "#D500F9", "accent_secondary": "#7B1FA2", "accent_tertiary": "#00E5FF",
            "text_main": "#F5E0FF", "text_dim": "#A080B0", "success": "#00E676", "error": "#FF1744", "warning": "#FFEA00"
        }
        self.themes["Emerald Pulse"] = {
            "bg_main": "#05100A", "bg_sidebar": "#0A1F14", "bg_card": "#0F2E1E",
            "accent_primary": "#00E676", "accent_secondary": "#00C853", "accent_tertiary": "#64FFDA",
            "text_main": "#E0FFE0", "text_dim": "#80B090", "success": "#B9F6CA", "error": "#FF5252", "warning": "#FFD600"
        }
        self.themes["Inferno Red"] = {
            "bg_main": "#100505", "bg_sidebar": "#1F0A0A", "bg_card": "#2E0F0F",
            "accent_primary": "#FF1744", "accent_secondary": "#D50000", "accent_tertiary": "#FFD600",
            "text_main": "#FFE0E0", "text_dim": "#B08080", "success": "#00E676", "error": "#FF1744", "warning": "#FFFF00"
        }
        self.themes["Ocean Deep"] = {
            "bg_main": "#020B14", "bg_sidebar": "#06182B", "bg_card": "#0A2240",
            "accent_primary": "#00B4FF", "accent_secondary": "#1E90FF", "accent_tertiary": "#40E0D0",
            "text_main": "#E0F0FF", "text_dim": "#7090B0", "success": "#00FF87", "error": "#FF4444", "warning": "#FFB347"
        }
        self.themes["Cherry Blossom"] = {
            "bg_main": "#1A0A12", "bg_sidebar": "#2D0F1E", "bg_card": "#3D1528",
            "accent_primary": "#FF69B4", "accent_secondary": "#FF1493", "accent_tertiary": "#FFD700",
            "text_main": "#FFE8F0", "text_dim": "#C08090", "success": "#7FFF00", "error": "#FF0040", "warning": "#FFA500"
        }
        self.themes["Arctic Frost"] = {
            "bg_main": "#0A0A12", "bg_sidebar": "#12121F", "bg_card": "#1A1A2E",
            "accent_primary": "#00FFFF", "accent_secondary": "#7FFFD4", "accent_tertiary": "#E0FFFF",
            "text_main": "#F0FFFF", "text_dim": "#88AACC", "success": "#00FA9A", "error": "#FF6B6B", "warning": "#FFD700"
        }
        self.themes["Neo Tokyo"] = {
            "bg_main": "#0A0015", "bg_sidebar": "#150025", "bg_card": "#200035",
            "accent_primary": "#FF00FF", "accent_secondary": "#00FFFF", "accent_tertiary": "#FFFF00",
            "text_main": "#F0E0FF", "text_dim": "#9060B0", "success": "#00FF95", "error": "#FF003C", "warning": "#FFD700"
        }
        self.themes["Solarized Dark"] = {
            "bg_main": "#002B36", "bg_sidebar": "#073642", "bg_card": "#093A46",
            "accent_primary": "#268BD2", "accent_secondary": "#2AA198", "accent_tertiary": "#CB4B16",
            "text_main": "#93A1A1", "text_dim": "#657B83", "success": "#859900", "error": "#DC322F", "warning": "#B58900"
        }
        self.load_custom_theme()

    def load_custom_theme(self):
        try:
            if os.path.exists("custom_theme.json"):
                with open("custom_theme.json", "r") as f:
                    data = json.load(f)
                    if all(k in data for k in THEME_KEYS):
                        self.themes["Custom Design"] = data
        except: pass

    def save_custom_theme(self, colors):
        self.themes["Custom Design"] = colors
        try:
            with open("custom_theme.json", "w") as f: json.dump(colors, f)
        except: pass
        self.set_theme("Custom Design")

    def get_color(self, key):
        theme = self.themes.get(self.current_theme_name, self.themes["Cyber Neon"])
        return theme.get(key, "#FFFFFF")

    def set_theme(self, theme_name):
        if theme_name in self.themes:
            self.current_theme_name = theme_name
            self.save_user_preference()
            for callback in self.callbacks:
                try: callback()
                except: pass
            return True
        return False

    def register_callback(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def save_user_preference(self):
        try:
            with open("theme_config.json", "w") as f:
                json.dump({"current_theme": self.current_theme_name}, f)
        except: pass

    def load_user_preference(self):
        try:
            if os.path.exists("theme_config.json"):
                with open("theme_config.json", "r") as f:
                    config = json.load(f)
                    theme_name = config.get("current_theme")
                    if theme_name in self.themes:
                        self.current_theme_name = theme_name
        except: pass

theme_manager = ThemeManager()

def get_colors():
    return {
        "BG_MAIN": theme_manager.get_color("bg_main"),
        "BG_SIDEBAR": theme_manager.get_color("bg_sidebar"),
        "BG_CARD": theme_manager.get_color("bg_card"),
        "ACCENT_PRIMARY": theme_manager.get_color("accent_primary"),
        "ACCENT_SECONDARY": theme_manager.get_color("accent_secondary"),
        "ACCENT_TERTIARY": theme_manager.get_color("accent_tertiary"),
        "TEXT_MAIN": theme_manager.get_color("text_main"),
        "TEXT_DIM": theme_manager.get_color("text_dim"),
        "SUCCESS": theme_manager.get_color("success"),
        "ERROR": theme_manager.get_color("error"),
        "WARNING": theme_manager.get_color("warning")
    }

class CyberButton(tk.Canvas):
    def __init__(self, parent, text, command=None, color=None, width=160, height=45, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent['bg'], highlightthickness=0, **kwargs)
        self.command = command
        self.color_key = color if isinstance(color, str) and not color.startswith("#") else None
        self.fixed_color = color if isinstance(color, str) and color.startswith("#") else None
        self.text = text
        self.width = width
        self.height = height
        self._update_colors()
        self.bind("<Enter>", lambda e: self._draw(True))
        self.bind("<Leave>", lambda e: self._draw(False))
        self.bind("<Button-1>", lambda e: self._draw(True, True))
        self.bind("<ButtonRelease-1>", self._on_release)
        theme_manager.register_callback(self.update_theme)
        self._draw(False)

    def _update_colors(self):
        colors = get_colors()
        if self.fixed_color:
            self.color = self.fixed_color
        elif self.color_key:
            self.color = theme_manager.get_color(self.color_key)
        else:
            self.color = colors["ACCENT_PRIMARY"]
        self.bg_card = colors["BG_CARD"]

    def update_theme(self):
        self._update_colors()
        if self.master and self.master.winfo_exists():
            try:
                self.configure(bg=self.master['bg'])
            except:
                pass
            self._draw(False)

    def _draw(self, hovered, pressed=False):
        self.delete("all")
        r = 12
        offset = 3 if pressed else 0
        if hovered and not pressed:
            self.create_rounded_rect(2, 2, self.width-2, self.height-2, r, fill=self.bg_card, outline=self.color, width=2)
        self.create_rounded_rect(4+offset, 4+offset, self.width-offset, self.height-offset, r, fill="#000000")
        self.create_rounded_rect(offset, offset, self.width-4-offset, self.height-4-offset, r, fill=self.color)
        self.create_text((self.width-4)/2, (self.height-4)/2, text=self.text, fill="white", font=("Segoe UI", 9, "bold"))

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def _on_release(self, e):
        self._draw(True)
        if self.command:
            self.command()

def sync_global_colors():
    global BG_MAIN, BG_SIDEBAR, BG_CARD, ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY
    global TEXT_MAIN, TEXT_DIM, SUCCESS, ERROR, WARNING
    c = get_colors()
    BG_MAIN, BG_SIDEBAR, BG_CARD = c["BG_MAIN"], c["BG_SIDEBAR"], c["BG_CARD"]
    ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY = c["ACCENT_PRIMARY"], c["ACCENT_SECONDARY"], c["ACCENT_TERTIARY"]
    TEXT_MAIN, TEXT_DIM = c["TEXT_MAIN"], c["TEXT_DIM"]
    SUCCESS, ERROR, WARNING = c["SUCCESS"], c["ERROR"], c["WARNING"]

sync_global_colors()
