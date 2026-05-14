import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog, colorchooser
import json
import threading
import asyncio
import os
import discord
import requests
import random
import io
import time
import base64
import webbrowser
import sys
from datetime import datetime
import re
from PIL import Image, ImageTk, ImageDraw
import concurrent.futures

from auth import keyauth_app, KeyAuthError, save_license_key, load_license_key, clear_license_key
from theme import (theme_manager, get_colors, sync_global_colors, CyberButton, resolve_font, BG_MAIN, BG_SIDEBAR, BG_CARD, ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, TEXT_MAIN, TEXT_DIM, SUCCESS, ERROR, WARNING)

class LoginPanel:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("UMAX AUTH SYSTEM v8.2")
        self.root.geometry("500x650")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, False)
        keyauth_app.init()
        theme_manager.register_callback(self.update_theme)
        self.build_ui()

    def update_theme(self):
        sync_global_colors()
        self.root.configure(bg=BG_MAIN)
        for child in self.root.winfo_children(): self._update_recursive(child)

    def _update_recursive(self, widget):
        try:
            if isinstance(widget, tk.Frame):
                widget.configure(bg=BG_MAIN)
                for child in widget.winfo_children(): self._update_recursive(child)
            elif isinstance(widget, tk.Label):
                if widget.cget("text") == "UMAX MANAGER": widget.configure(bg=BG_MAIN, fg=ACCENT_SECONDARY)
                elif widget.cget("text") == "LICENSE KEY": widget.configure(bg=BG_MAIN, fg=ACCENT_PRIMARY)
                elif widget.cget("fg") == TEXT_DIM: widget.configure(bg=BG_MAIN, fg=TEXT_DIM)
                else: widget.configure(bg=BG_MAIN, fg=TEXT_MAIN)
            elif isinstance(widget, tk.Entry):
                widget.configure(bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_SECONDARY)
        except: pass

    def build_ui(self):
        frame = tk.Frame(self.root, bg=BG_MAIN, padx=40, pady=40)
        frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        tk.Label(frame, text="UMAX MANAGER", font=resolve_font("Orbitron", 24, "bold"), bg=BG_MAIN, fg=ACCENT_SECONDARY).pack(pady=(0, 10))
        tk.Label(frame, text="KEYAUTH PROTECTED", font=("Segoe UI", 10, "bold"), bg=BG_MAIN, fg=TEXT_DIM).pack(pady=(0, 40))
        tk.Label(frame, text="LICENSE KEY", bg=BG_MAIN, fg=ACCENT_PRIMARY, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.key_entry = tk.Entry(frame, bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_SECONDARY, relief="flat", font=("Consolas", 12), show="*")
        self.key_entry.pack(fill=tk.X, pady=(5, 2), ipady=12)
        tk.Frame(frame, height=2, bg=ACCENT_PRIMARY).pack(fill=tk.X, pady=(0, 30))
        self.status_lbl = tk.Label(frame, text="KeyAuth Server: Online", bg=BG_MAIN, fg=TEXT_DIM, font=("Segoe UI", 9))
        self.status_lbl.pack(pady=10)
        CyberButton(frame, "LOGIN VIA KEYAUTH", self.authorize, "accent_primary", width=320, height=50).pack(pady=10)
        CyberButton(frame, "INSTALL DEPENDENCIES", self.install_deps, "accent_tertiary", width=320, height=45).pack(pady=5)
        CyberButton(frame, "PURCHASE ACCESS", lambda: webbrowser.open("https://keyauth.win"), "bg_sidebar", width=320, height=45).pack(pady=5)

    def install_deps(self):
        libs = ["discord.py-self", "Pillow", "requests"]
        self.status_lbl.config(text="Installing Libraries... Please wait", fg=WARNING)
        self.root.update()
        def run_install():
            try:
                for lib in libs: subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                self.root.after(0, lambda: messagebox.showinfo("Success", "All libraries installed successfully!"))
                self.root.after(0, lambda: self.status_lbl.config(text="Libraries Ready!", fg=SUCCESS))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to install: {str(e)}"))
                self.root.after(0, lambda: self.status_lbl.config(text="Installation Failed", fg=ERROR))
        threading.Thread(target=run_install, daemon=True).start()

    def save_recent_license(self, key):
        try:
            recent = []
            if os.path.exists("recent_licenses.json"):
                with open("recent_licenses.json", "r") as f: recent = json.load(f)
            entry = {"key": f"{key[:10]}...", "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "full_key": key}
            recent.insert(0, entry); recent = recent[:5]
            with open("recent_licenses.json", "w") as f: json.dump(recent, f)
        except: pass

    def authorize(self):
        key = self.key_entry.get().strip()
        if not key: messagebox.showerror("Auth Error", "Please enter your license key."); return
        self.status_lbl.config(text="Contacting KeyAuth Servers...", fg=WARNING); self.root.update()
        try:
            if keyauth_app.license(key):
                save_license_key(key); self.save_recent_license(key); self.status_lbl.config(text="License Verified!", fg=SUCCESS); self.root.update(); time.sleep(1); self.on_success()
        except KeyAuthError as e:
            self.status_lbl.config(text=str(e), fg=ERROR)
            messagebox.showerror("Access Denied", str(e))
        except Exception as e:
            self.status_lbl.config(text=f"Auth Error: {e}", fg=ERROR)
            messagebox.showerror("Auth Error", f"Unexpected error: {e}")

class TitanManagerV8_2:
    def __init__(self, root):
        self.root = root
        self.root.title("UMAX MANAGER v8.2 - LICENSE ACTIVE")
        self.root.geometry("1550x950")
        self.root.minsize(1200, 700)
        self.root.configure(bg=BG_MAIN)
        self.accounts_file, self.proxies_file, self.trigger_file = "discord_accounts.json", "proxies.txt", "triggers.txt"
        self.voice_originals = {}
        self.accounts = self.load_data(self.accounts_file, [])
        self.proxies, self.triggers = self.load_proxies(), self.load_triggers()
        self.use_proxy = tk.BooleanVar(value=False)
        self.avatars_cache = {}
        self.scheduler_tasks = {}
        self.scheduler_running = False
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_table())
        self.webhook_url = ""
        self.webhook_enabled = tk.BooleanVar(value=False)
        self.license_key = load_license_key() or ""
        self.bot_url = tk.StringVar(value="http://localhost:5000")
        self.bot_status_lbl = None
        self.setup_styles(); self.build_ui(); self.refresh_table()

    def load_data(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f: return json.load(f)
            except: return default
        return default

    def load_proxies(self):
        if os.path.exists(self.proxies_file):
            with open(self.proxies_file, "r", encoding="utf-8") as f: return [l.strip() for l in f if l.strip()]
        return []

    def load_triggers(self):
        defaults = ["hello", "discord", "neon"]
        if os.path.exists(self.trigger_file):
            with open(self.trigger_file, "r", encoding="utf-8") as f:
                loaded = [l.strip() for l in f if l.strip()]
                if loaded:
                    return loaded
        try:
            with open(self.trigger_file, "w", encoding="utf-8") as f:
                f.write("\n".join(defaults))
        except: pass
        return defaults

    def save_accounts(self):
        with open(self.accounts_file, "w", encoding="utf-8") as f: json.dump(self.accounts, f, indent=4)

    def save_triggers(self):
        with open(self.trigger_file, "w", encoding="utf-8") as f: f.write("\n".join(self.triggers))

    def setup_styles(self):
        theme_manager.register_callback(self.apply_theme_to_ui); self.apply_theme_to_ui()

    def apply_theme_to_ui(self):
        sync_global_colors()
        style = ttk.Style(); style.theme_use("clam")
        style.configure("TNotebook", background=BG_MAIN, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_SIDEBAR, foreground=TEXT_DIM, padding=[25, 12], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", ACCENT_PRIMARY)], foreground=[("selected", "white")])
        style.configure("Sub.TNotebook", background=BG_MAIN, borderwidth=0)
        style.configure("Sub.TNotebook.Tab", background=BG_CARD, foreground=TEXT_DIM, padding=[15, 8], font=("Segoe UI", 9, "bold"))
        style.map("Sub.TNotebook.Tab", background=[("selected", ACCENT_SECONDARY)], foreground=[("selected", "black")])
        style.configure("Treeview", background=BG_CARD, foreground=TEXT_MAIN, fieldbackground=BG_CARD, rowheight=45, font=("Segoe UI", 10), borderwidth=0)
        style.configure("Treeview.Heading", background=BG_SIDEBAR, foreground=ACCENT_PRIMARY, font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Treeview", background=[("selected", ACCENT_PRIMARY)], foreground=[("selected", "white")])
        style.configure("TScrollbar", background=BG_CARD, troughcolor=BG_MAIN, bordercolor=BG_MAIN, arrowcolor=ACCENT_PRIMARY, gripcount=0)
        style.configure("TRadiobutton", background=BG_MAIN, foreground=TEXT_MAIN, indicatorbackground=BG_CARD, indicatordiameter=12)
        style.map("TRadiobutton", background=[("active", BG_CARD)])
        style.configure("TCheckbutton", background=BG_MAIN, foreground=TEXT_MAIN, indicatorbackground=BG_CARD)
        style.map("TCheckbutton", background=[("active", BG_CARD)])
        style.configure("TEntry", fieldbackground=BG_CARD, foreground=TEXT_MAIN, bordercolor=BG_SIDEBAR)
        style.configure("TFrame", background=BG_MAIN)
        style.configure("TLabelframe", background=BG_MAIN, foreground=ACCENT_SECONDARY, bordercolor=BG_SIDEBAR)
        self.root.configure(bg=BG_MAIN)
        if hasattr(self, 'main_content'): self.main_content.configure(bg=BG_MAIN)
        if hasattr(self, 'sidebar'): self.sidebar.configure(bg=BG_SIDEBAR)
        self._update_children_theme(self.root)

    def _update_children_theme(self, parent):
        for child in parent.winfo_children():
            try:
                cls = child.__class__
                if cls == tk.Frame or cls == tk.LabelFrame:
                    if child == getattr(self, 'sidebar', None):
                        child.configure(bg=BG_SIDEBAR)
                    else:
                        child.configure(bg=BG_MAIN)
                    self._update_children_theme(child)
                elif cls == tk.Label:
                    fg = child.cget("fg")
                    accent_colors = {ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_TERTIARY, SUCCESS, ERROR, WARNING}
                    if fg not in accent_colors:
                        child.configure(bg=child.master.cget("bg"), fg=TEXT_MAIN)
                    else:
                        child.configure(bg=child.master.cget("bg"))
                elif cls in (tk.Entry, tk.Text, scrolledtext.ScrolledText):
                    child.configure(bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_SECONDARY)
                elif cls == tk.Listbox:
                    child.configure(bg=BG_CARD, fg=TEXT_MAIN)
                elif cls == tk.Checkbutton:
                    child.configure(bg=child.master.cget("bg"), fg=TEXT_MAIN, selectcolor=BG_SIDEBAR)
                elif cls == tk.Canvas:
                    child.configure(bg=child.master.cget("bg"))
                elif cls == ttk.Combobox:
                    style = ttk.Style()
                    style.configure("TCombobox", fieldbackground=BG_CARD, foreground=TEXT_MAIN, arrowcolor=ACCENT_PRIMARY)
            except: pass

    def _build_license_card(self):
        tk.Label(self.sidebar, text="LICENSE DASHBOARD", bg=BG_SIDEBAR, fg=ACCENT_SECONDARY, font=("Segoe UI", 8, "bold")).pack(pady=(20, 5), padx=30, anchor=tk.W)
        self.license_card = tk.Frame(self.sidebar, bg=BG_CARD, padx=20, pady=15, highlightthickness=1, highlightbackground=ACCENT_SECONDARY)
        self.license_card.pack(fill=tk.X, padx=25, pady=(0, 10))
        u_data = keyauth_app.user_data or {"key": "N/A", "expires": "N/A", "level": "N/A"}
        self._license_labels = {}
        for k, v, c in [("key", f"{u_data['key'][:15]}...", ACCENT_SECONDARY), ("expires", u_data['expires'], SUCCESS), ("level", u_data['level'], ACCENT_TERTIARY)]:
            f = tk.Frame(self.license_card, bg=BG_CARD); f.pack(fill=tk.X, pady=2)
            tk.Label(f, text=k.upper() + ":", font=("Segoe UI", 7, "bold"), bg=BG_CARD, fg=TEXT_DIM).pack(side=tk.LEFT)
            lbl = tk.Label(f, text=v, font=("Consolas", 8, "bold"), bg=BG_CARD, fg=c)
            lbl.pack(side=tk.LEFT, padx=5)
            self._license_labels[k] = lbl
        CyberButton(self.license_card, "LOGOUT", self.logout, ERROR, width=280, height=30).pack(pady=(10, 0))

    def refresh_license_card(self):
        if not hasattr(self, 'license_card') or not self.license_card.winfo_exists():
            return
        u_data = keyauth_app.user_data
        if not u_data:
            return
        if 'key' in self._license_labels:
            self._license_labels['key'].config(text=f"{u_data.get('key', 'N/A')[:15]}...")
        if 'expires' in self._license_labels:
            self._license_labels['expires'].config(text=u_data.get('expires', 'N/A'))
        if 'level' in self._license_labels:
            self._license_labels['level'].config(text=u_data.get('level', 'N/A'))

    def build_ui(self):
        tk.Frame(self.root, height=2, bg=ACCENT_SECONDARY).pack(fill=tk.X)
        self.sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=340); self.sidebar.pack(side=tk.LEFT, fill=tk.Y); self.sidebar.pack_propagate(False)
        
        theme_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR, padx=20, pady=10); theme_frame.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(theme_frame, text="SYSTEM THEME", bg=BG_SIDEBAR, fg=ACCENT_SECONDARY, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.theme_var = tk.StringVar(value=theme_manager.current_theme_name)
        self.theme_combo = ttk.Combobox(theme_frame, textvariable=self.theme_var, values=list(theme_manager.themes.keys()), state="readonly")
        self.theme_combo.pack(fill=tk.X, pady=5); self.theme_combo.bind("<<ComboboxSelected>>", lambda e: theme_manager.set_theme(self.theme_var.get()))
        theme_manager.register_callback(lambda: self.theme_combo.configure(values=list(theme_manager.themes.keys())))

        self._build_license_card()

        tk.Label(self.sidebar, text="RECENT LOGINS", bg=BG_SIDEBAR, fg=WARNING, font=("Segoe UI", 8, "bold")).pack(pady=(15, 5), padx=30, anchor=tk.W)
        self.recent_f = tk.Frame(self.sidebar, bg=BG_CARD, padx=15, pady=10, highlightthickness=1, highlightbackground=BG_SIDEBAR); self.recent_f.pack(fill=tk.X, padx=25)
        try:
            if os.path.exists("recent_licenses.json"):
                with open("recent_licenses.json", "r") as f:
                    for r in json.load(f):
                        rf = tk.Frame(self.recent_f, bg=BG_CARD); rf.pack(fill=tk.X, pady=2)
                        tk.Label(rf, text=r['key'], font=("Consolas", 7), bg=BG_CARD, fg=TEXT_MAIN).pack(side=tk.LEFT)
                        tk.Label(rf, text=r['date'], font=("Segoe UI", 6), bg=BG_CARD, fg=TEXT_DIM).pack(side=tk.RIGHT)
            else: tk.Label(self.recent_f, text="No recent logins", font=("Segoe UI", 7, "italic"), bg=BG_CARD, fg=TEXT_DIM).pack()
        except: pass

        tk.Label(self.sidebar, text="ACCOUNT PROFILE", bg=BG_SIDEBAR, fg=ACCENT_PRIMARY, font=("Segoe UI", 8, "bold")).pack(pady=(10, 5), padx=30, anchor=tk.W)
        self.profile_card = tk.Frame(self.sidebar, bg=BG_CARD, padx=20, pady=20, highlightthickness=1, highlightbackground=ACCENT_PRIMARY); self.profile_card.pack(fill=tk.X, padx=25)
        self.avatar_canvas = tk.Canvas(self.profile_card, width=100, height=100, bg=BG_CARD, highlightthickness=0); self.avatar_canvas.pack(pady=5); self._draw_placeholder_avatar()
        self.user_name_lbl = tk.Label(self.profile_card, text="UMAX MASTER", font=("Segoe UI", 12, "bold"), bg=BG_CARD, fg=TEXT_MAIN); self.user_name_lbl.pack()
        tk.Label(self.profile_card, text="● KeyAuth Verified", font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=SUCCESS).pack()

        tk.Label(self.sidebar, text="QUICK STATUS", bg=BG_SIDEBAR, fg=ACCENT_SECONDARY, font=("Segoe UI", 8, "bold")).pack(pady=(15, 5), padx=30, anchor=tk.W)
        qs_frame = tk.Frame(self.sidebar, bg=BG_SIDEBAR); qs_frame.pack(fill=tk.X, padx=25)
        for t, c, s in [("ONLINE", SUCCESS, "online"), ("IDLE", WARNING, "idle"), ("DND", ERROR, "dnd")]:
            CyberButton(qs_frame, t, lambda st=s: self.svc_change_presence(st), c, width=90, height=35).pack(side=tk.LEFT, padx=2)

        self.main_content = tk.Frame(self.root, bg=BG_MAIN); self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=30, pady=20)
        self.tabs = ttk.Notebook(self.main_content); self.tabs.pack(fill=tk.BOTH, expand=True)
        self.tab_dash = tk.Frame(self.tabs, bg=BG_MAIN); self.tabs.add(self.tab_dash, text=" ⚡ DASHBOARD ")
        self.tab_social = tk.Frame(self.tabs, bg=BG_MAIN); self.tabs.add(self.tab_social, text=" 🌐 SOCIAL HUB ")
        self.tab_auto = tk.Frame(self.tabs, bg=BG_MAIN); self.tabs.add(self.tab_auto, text=" 🤖 AUTO-REACTION ")
        self.tab_config = tk.Frame(self.tabs, bg=BG_MAIN); self.tabs.add(self.tab_config, text=" ⚙️ CONFIG ")
        self.tab_customize = tk.Frame(self.tabs, bg=BG_MAIN); self.tabs.add(self.tab_customize, text=" 🎨 CUSTOMIZE ")
        self.tab_scheduler = tk.Frame(self.tabs, bg=BG_MAIN); self.tabs.add(self.tab_scheduler, text=" ⏰ SCHEDULER ")
        self.tab_logs = tk.Frame(self.tabs, bg=BG_MAIN); self.tabs.add(self.tab_logs, text=" 📟 CONSOLE ")
        self._build_dashboard(); self._build_social_hub(); self._build_auto_reaction(); self._build_config(); self._build_customize(); self._build_scheduler(); self._build_logs()

    def _build_dashboard(self):
        controls = tk.Frame(self.tab_dash, bg=BG_MAIN, pady=10); controls.pack(fill=tk.X)
        CyberButton(controls, "STEALTH SYNC", self.svc_check, ACCENT_SECONDARY, width=140).pack(side=tk.LEFT, padx=5)
        CyberButton(controls, "VIEW GUILDS", self.svc_view_guilds, ACCENT_TERTIARY, width=140).pack(side=tk.LEFT, padx=5)
        CyberButton(controls, "ANALYZE", self.svc_detailed_check, SUCCESS, width=120).pack(side=tk.LEFT, padx=5)
        CyberButton(controls, "EXPORT", self.export_accounts, ACCENT_PRIMARY, width=120).pack(side=tk.RIGHT, padx=5)
        CyberButton(controls, "DELETE", self.delete_selected, ERROR, width=120).pack(side=tk.RIGHT, padx=5)
        search_frame = tk.Frame(self.tab_dash, bg=BG_MAIN); search_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(search_frame, text="🔍 SEARCH:", bg=BG_MAIN, fg=TEXT_DIM, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        tk.Entry(search_frame, textvariable=self.search_var, bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_SECONDARY, relief="flat", font=("Segoe UI", 10)).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        cols = ("id", "user", "token", "status", "presence")
        self.tree = ttk.Treeview(self.tab_dash, columns=cols, show="headings")
        for col in cols: self.tree.heading(col, text=col.upper()); self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill=tk.BOTH, expand=True); self.tree.bind("<<TreeviewSelect>>", self.on_select); self.tree.bind("<Control-a>", lambda e: self.tree.selection_set(self.tree.get_children())); self.tree.bind("<Double-1>", self._show_account_details)

    def _build_social_hub(self):
        self.social_tabs = ttk.Notebook(self.tab_social, style="Sub.TNotebook"); self.social_tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.page_gen = tk.Frame(self.social_tabs, bg=BG_MAIN); self.social_tabs.add(self.page_gen, text=" GENERAL SERVICES ")
        self.page_dm = tk.Frame(self.social_tabs, bg=BG_MAIN); self.social_tabs.add(self.page_dm, text=" DM MASTER ")
        self.page_id = tk.Frame(self.social_tabs, bg=BG_MAIN); self.social_tabs.add(self.page_id, text=" IDENTITY SERVICES ")
        self._build_gen_grid(); self._build_dm_grid(); self._build_id_grid()

    def _build_dm_grid(self):
        grid = tk.Frame(self.page_dm, bg=BG_MAIN, pady=20); grid.pack(expand=True)
        svcs = [("DM SPAMMER", self.svc_dm_spammer, ERROR), ("DM CLEARER", self.svc_dm_clearer, ACCENT_SECONDARY), ("DM BROADCAST", self.svc_dm_broadcast_advanced, SUCCESS)]
        for i, (t, c, cl) in enumerate(svcs):
            card = tk.Frame(grid, bg=BG_CARD, padx=25, pady=25, highlightthickness=1, highlightbackground=BG_SIDEBAR); card.grid(row=0, column=i, padx=15, pady=15)
            tk.Label(card, text=t, font=("Segoe UI", 12, "bold"), bg=BG_CARD, fg=cl).pack(); CyberButton(card, "ACTIVATE", c, cl, width=200).pack(pady=(10, 0))

    def _build_gen_grid(self):
        grid = tk.Frame(self.page_gen, bg=BG_MAIN, pady=20); grid.pack(expand=True)
        svcs = [("FRIEND CLEANER", self.svc_remove_all_friends, ERROR), ("REQUEST BLOCKER", self.svc_reject_all_requests, ACCENT_TERTIARY), ("MASS JOIN", self.svc_join, ACCENT_SECONDARY), ("MASS LEAVE", self.svc_mass_leave, WARNING), ("SERVER PURGE", self.svc_leave_all, ERROR), ("ADD FRIEND", self.svc_friend, SUCCESS)]
        for i, (t, c, cl) in enumerate(svcs):
            card = tk.Frame(grid, bg=BG_CARD, padx=20, pady=20, highlightthickness=1, highlightbackground=BG_SIDEBAR); card.grid(row=i//3, column=i%3, padx=10, pady=10)
            tk.Label(card, text=t, font=("Segoe UI", 11, "bold"), bg=BG_CARD, fg=cl).pack(); CyberButton(card, "EXECUTE", c, cl, width=180, height=35).pack(pady=(5, 0))

    def _build_id_grid(self):
        grid = tk.Frame(self.page_id, bg=BG_MAIN, pady=20); grid.pack(expand=True)
        svcs = [("24/7 ONLINE", self.svc_24_7_online, SUCCESS), ("STREAMING", self.svc_streaming, ACCENT_PRIMARY), ("VOICE 24/7", self.svc_voice_247, ACCENT_TERTIARY), ("BULK NAMES", self.svc_bulk_names, ACCENT_SECONDARY), ("AVATAR SYNC", self.svc_bulk_avatars, ACCENT_TERTIARY), ("BIO UPDATE", self.svc_bulk_bios, WARNING), ("HYPE SQUAD", self.svc_hypesquad, TEXT_DIM), ("STOP VOICE", self.svc_stop_voice, ERROR)]
        for i, (t, c, cl) in enumerate(svcs):
            card = tk.Frame(grid, bg=BG_CARD, padx=20, pady=20, highlightthickness=1, highlightbackground=BG_SIDEBAR); card.grid(row=i//3, column=i%3, padx=10, pady=10)
            tk.Label(card, text=t, font=("Segoe UI", 11, "bold"), bg=BG_CARD, fg=cl).pack(); CyberButton(card, "ACTIVATE" if t != "STOP VOICE" else "DISCONNECT", c, cl, width=180, height=35).pack(pady=(10, 0))

    def _build_auto_reaction(self):
        container = tk.Frame(self.tab_auto, bg=BG_MAIN, pady=20); container.pack(fill=tk.BOTH, expand=True)
        ctrl = tk.Frame(container, bg=BG_MAIN, padx=20); ctrl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(ctrl, text="ADVANCED AUTO-REACTION", font=("Segoe UI", 14, "bold"), bg=BG_MAIN, fg=ACCENT_SECONDARY).pack(anchor=tk.W, pady=10)
        modes = [("MODE 1: SMART MONITOR", self.svc_ar_smart_monitor, "accent_primary"), ("MODE 2: CHANNEL FIXED", self.svc_ar_channel_fixed, "accent_secondary"), ("MODE 3: TRIGGER SYNC", self.svc_ar_smart_monitor, "accent_tertiary")]
        for t, c, cl in modes:
            f = tk.Frame(ctrl, bg=BG_CARD, padx=15, pady=15, highlightthickness=1, highlightbackground=BG_SIDEBAR); f.pack(fill=tk.X, pady=5)
            tk.Label(f, text=t, font=("Segoe UI", 10, "bold"), bg=BG_CARD, fg=theme_manager.get_color(cl)).pack(side=tk.LEFT); CyberButton(f, "START", c, cl, width=120, height=35).pack(side=tk.RIGHT)
        trig = tk.Frame(container, bg=BG_MAIN, width=400, padx=20); trig.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(trig, text="KEYWORD TRIGGERS", font=("Segoe UI", 12, "bold"), bg=BG_MAIN, fg=WARNING).pack(pady=10)
        self.trig_list = tk.Listbox(trig, bg=BG_CARD, fg=TEXT_MAIN, borderwidth=0, font=("Consolas", 10)); self.trig_list.pack(fill=tk.BOTH, expand=True)
        for t in self.triggers: self.trig_list.insert(tk.END, t)
        btn_f = tk.Frame(trig, bg=BG_MAIN); btn_f.pack(fill=tk.X, pady=10)
        CyberButton(btn_f, "ADD", self.add_trigger, SUCCESS, width=80, height=30).pack(side=tk.LEFT, padx=2)
        CyberButton(btn_f, "REMOVE", self.remove_trigger, ERROR, width=80, height=30).pack(side=tk.LEFT, padx=2)

    def _build_customize(self):
        container = tk.Frame(self.tab_customize, bg=BG_MAIN, pady=20); container.pack(fill=tk.BOTH, expand=True)
        tk.Label(container, text="THEME CUSTOMIZATION ENGINE", font=resolve_font("Orbitron", 16, "bold"), bg=BG_MAIN, fg=ACCENT_PRIMARY).pack(pady=(0, 20))
        self.custom_grid = tk.Frame(container, bg=BG_MAIN); self.custom_grid.pack(expand=True)
        self.custom_colors = theme_manager.themes.get(theme_manager.current_theme_name, theme_manager.themes["Cyber Neon"]).copy()
        self.color_btns = {}
        color_keys = [("Main Background", "bg_main"), ("Sidebar Color", "bg_sidebar"), ("Card Color", "bg_card"), ("Primary Accent", "accent_primary"), ("Secondary Accent", "accent_secondary"), ("Tertiary Accent", "accent_tertiary"), ("Main Text", "text_main"), ("Dim Text", "text_dim"), ("Success Color", "success")]
        for i, (label, key) in enumerate(color_keys):
            row, col = i // 3, i % 3
            card = tk.Frame(self.custom_grid, bg=BG_CARD, padx=15, pady=15, highlightthickness=1, highlightbackground=BG_SIDEBAR); card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            tk.Label(card, text=label.upper(), font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=TEXT_DIM).pack(anchor=tk.W)
            btn = tk.Button(card, bg=self.custom_colors[key], width=15, height=1, relief="flat", command=lambda k=key: self._pick_color(k)); btn.pack(pady=5)
            self.color_btns[key] = btn
        btn_f = tk.Frame(container, bg=BG_MAIN); btn_f.pack(pady=30)
        CyberButton(btn_f, "SAVE & APPLY CUSTOM THEME", self._apply_custom_theme, SUCCESS, width=300).pack(side=tk.LEFT, padx=10)
        CyberButton(btn_f, "RESET TO DEFAULT", lambda: theme_manager.set_theme("Cyber Neon"), ERROR, width=200).pack(side=tk.LEFT, padx=10)
        theme_manager.register_callback(self._sync_customize_tab)

    def _build_scheduler(self):
        container = tk.Frame(self.tab_scheduler, bg=BG_MAIN, pady=20); container.pack(fill=tk.BOTH, expand=True, padx=20)
        tk.Label(container, text="TASK SCHEDULER", font=("Segoe UI", 14, "bold"), bg=BG_MAIN, fg=ACCENT_PRIMARY).pack(pady=(0, 15))
        list_frame = tk.Frame(container, bg=BG_CARD, padx=10, pady=10, highlightthickness=1, highlightbackground=BG_SIDEBAR)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.sched_listbox = tk.Listbox(list_frame, bg=BG_CARD, fg=TEXT_MAIN, borderwidth=0, font=("Consolas", 10), selectbackground=ACCENT_PRIMARY)
        self.sched_listbox.pack(fill=tk.BOTH, expand=True)
        ctrl_frame = tk.Frame(container, bg=BG_MAIN, padx=20); ctrl_frame.pack(side=tk.RIGHT, fill=tk.Y)
        btns_info = [
            ("ADD TASK", self._sched_add_task, SUCCESS),
            ("REMOVE", self._sched_remove_task, ERROR),
            ("START ALL", self._sched_start_all, ACCENT_PRIMARY),
            ("STOP ALL", self._sched_stop_all, ACCENT_TERTIARY),
        ]
        for t, c, cl in btns_info:
            CyberButton(ctrl_frame, t, c, cl, width=160, height=40).pack(pady=8)

    def _sched_add_task(self):
        dialog = tk.Toplevel(self.root); dialog.title("Add Scheduled Task"); dialog.geometry("500x500"); dialog.configure(bg=BG_CARD)
        tk.Label(dialog, text="NEW SCHEDULED TASK", font=("Segoe UI", 12, "bold"), bg=BG_CARD, fg=ACCENT_PRIMARY).pack(pady=15)
        tk.Label(dialog, text="Task Type:", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 9, "bold")).pack()
        task_var = tk.StringVar(value="24/7 ONLINE")
        task_options = ["24/7 ONLINE", "STREAMING", "DM SPAM", "VOICE 24/7"]
        task_combo = ttk.Combobox(dialog, textvariable=task_var, values=task_options, state="readonly")
        task_combo.pack(pady=5)
        tk.Label(dialog, text="Interval (minutes):", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 9, "bold")).pack()
        interval_entry = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat", font=("Consolas", 11))
        interval_entry.insert(0, "60"); interval_entry.pack(pady=5, ipady=6)

        params_frame = tk.LabelFrame(dialog, text=" TASK PARAMETERS ", bg=BG_CARD, fg=ACCENT_SECONDARY, font=("Segoe UI", 9, "bold"), padx=15, pady=15)
        params_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        param_widgets = {}

        param_defs = {
            "24/7 ONLINE": [("Status", "status", ttk.Combobox)],
            "STREAMING": [("Stream Text", "text", tk.Entry), ("Stream URL (optional)", "url", tk.Entry)],
            "DM SPAM": [("Target User ID", "target_id", tk.Entry), ("Message", "message", tk.Entry), ("Count", "count", tk.Entry)],
            "VOICE 24/7": [("Voice Channel ID", "vc_id", tk.Entry), ("Server ID", "guild_id", tk.Entry), ("Nickname (optional)", "nick", tk.Entry)],
        }

        param_values = {}

        def rebuild_params(*_):
            for w in params_frame.winfo_children(): w.destroy()
            param_widgets.clear(); param_values.clear()
            ttype = task_var.get()
            for label, key, wtype in param_defs.get(ttype, []):
                f = tk.Frame(params_frame, bg=BG_CARD); f.pack(fill=tk.X, pady=4)
                tk.Label(f, text=label, bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 8, "bold")).pack(anchor=tk.W)
                if wtype == ttk.Combobox:
                    widget = ttk.Combobox(f, values=["online", "idle", "dnd", "streaming"], state="readonly")
                    widget.set("online")
                    widget.pack(fill=tk.X, ipady=3)
                else:
                    entry = tk.Entry(f, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat", font=("Consolas", 11))
                    entry.pack(fill=tk.X, ipady=5)
                    if key == "count": entry.insert(0, "5")
                    if key == "url": entry.insert(0, "https://twitch.tv/discord")
                    widget = entry
                param_widgets[key] = widget
            if not param_defs.get(ttype):
                tk.Label(params_frame, text="No parameters needed", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 9, "italic")).pack(pady=20)

        task_combo.bind("<<ComboboxSelected>>", rebuild_params)
        rebuild_params()

        def confirm():
            ttype = task_var.get()
            try: interval = float(interval_entry.get().strip()) * 60
            except: messagebox.showerror("Error", "Invalid interval"); return
            params = {}
            for key, entry in param_widgets.items():
                val = entry.get().strip()
                if not val and key in ("target_id", "message"):
                    messagebox.showerror("Error", f"'{key}' is required"); return
                params[key] = val
            tid = len(self.scheduler_tasks) + 1
            desc = f"[{tid}] {ttype} every {int(interval//60)}m"
            if params.get("target_id"): desc += f" -> {params['target_id']}"
            if params.get("vc_id"): desc += f" -> VC:{params['vc_id']}"
            self.scheduler_tasks[tid] = {"type": ttype, "interval": interval, "params": params, "running": False, "last_run": 0}
            self.sched_listbox.insert(tk.END, desc)
            dialog.destroy()
            self.log(f"Scheduled: {ttype} every {int(interval//60)}m", "success")
        CyberButton(dialog, "CONFIRM", confirm, SUCCESS, width=180).pack(pady=15)

    def _sched_remove_task(self):
        sel = self.sched_listbox.curselection()
        if not sel: return
        text = self.sched_listbox.get(sel[0])
        tid = int(text.split('[')[1].split(']')[0])
        self.scheduler_tasks.pop(tid, None)
        self.sched_listbox.delete(sel[0])
        self.log(f"Removed task {tid}", "warn")

    def _sched_start_all(self):
        if not self.scheduler_tasks:
            messagebox.showinfo("No Tasks", "Add tasks first."); return
        self.scheduler_running = True
        self.log("Scheduler started", "success")
        threading.Thread(target=self._scheduler_loop, daemon=True).start()

    def _sched_stop_all(self):
        self.scheduler_running = False
        for tid in self.scheduler_tasks:
            self.scheduler_tasks[tid]["running"] = False
        self.log("Scheduler stopped", "warn")

    def _scheduler_loop(self):
        while self.scheduler_running:
            now = time.time()
            for tid, task in list(self.scheduler_tasks.items()):
                if not self.scheduler_running: break
                if now - task["last_run"] >= task["interval"]:
                    task["last_run"] = now
                    threading.Thread(target=self._sched_execute, args=(tid, task), daemon=True).start()
            time.sleep(10)

    def _sched_execute(self, tid, task):
        self.root.after(0, lambda: self.log(f"Executing task [{tid}]: {task['type']}", "task"))
        ttype = task["type"]
        params = task.get("params", {})

        if ttype == "24/7 ONLINE":
            status = params.get("status", "online")
            async def task_online(client, st):
                sm = {"online": discord.Status.online, "idle": discord.Status.idle, "dnd": discord.Status.dnd}
                await client.change_presence(status=sm.get(st, discord.Status.online))
                self.log(f"Scheduler: 24/7 {st}", "success")
                while True: await asyncio.sleep(3600)
            for idx, acc in self.get_targets():
                self.run_task(acc['token'], task_online, status)

        elif ttype == "STREAMING":
            text = params.get("text", "Live Now")
            url = params.get("url", "")
            async def task_stream(client, t, u):
                await client.change_presence(activity=discord.Activity(name=t, url=u or "https://twitch.tv/discord", type=discord.ActivityType.streaming))
                self.log(f"Scheduler: streaming '{t}'", "success")
                while True: await asyncio.sleep(3600)
            for idx, acc in self.get_targets():
                self.run_task(acc['token'], task_stream, text, url)

        elif ttype == "DM SPAM":
            target_id = params.get("target_id", "")
            message = params.get("message", "⏰ Scheduled message from UMAX Scheduler")
            count = int(params.get("count", "3"))
            if not target_id:
                self.log("DM spam skipped: no target ID", "error"); return
            async def spam_task(client, uid, msg, cnt):
                user = await client.fetch_user(int(uid))
                for i in range(cnt):
                    try: await user.send(msg); self.log(f"DM [{i+1}/{cnt}] to {user}", "success"); await asyncio.sleep(1)
                    except: self.log(f"DM [{i+1}/{cnt}] failed", "error")
            for idx, acc in self.get_targets():
                self.run_task(acc['token'], spam_task, target_id, message, count)

        elif ttype == "VOICE 24/7":
            vc_id = params.get("vc_id", "")
            guild_id = params.get("guild_id", "")
            nick = params.get("nick", "")
            if not vc_id or not guild_id:
                self.log("Voice 24/7 skipped: missing VC or Guild ID", "error"); return
            async def voice_task(client, v, g, nk):
                guild = await client.fetch_guild(int(g))
                channel = await guild.fetch_channel(int(v))
                if nk:
                    member = await guild.fetch_member(client.user.id)
                    await member.edit(nick=nk)
                await guild.change_voice_state(channel=channel, self_mute=True, self_deaf=False)
                self.log(f"Scheduler: voice connected to {channel.name}", "success")
                while True:
                    await asyncio.sleep(30)
                    me = guild.get_member(client.user.id)
                    if not me or not me.voice or me.voice.channel != channel:
                        await guild.change_voice_state(channel=channel, self_mute=True, self_deaf=False)
            for idx, acc in self.get_targets():
                self.run_task(acc['token'], voice_task, vc_id, guild_id, nick)

    def _pick_color(self, key):
        color = colorchooser.askcolor(initialcolor=self.custom_colors[key])[1]
        if color:
            self.custom_colors[key] = color
            if key in self.color_btns:
                self.color_btns[key].configure(bg=color)

    def _sync_customize_tab(self):
        if not hasattr(self, 'color_btns') or not self.color_btns:
            return
        current = theme_manager.themes.get(theme_manager.current_theme_name)
        if current and theme_manager.current_theme_name != "Custom Design":
            self.custom_colors = current.copy()
            for k, btn in self.color_btns.items():
                if k in self.custom_colors:
                    btn.configure(bg=self.custom_colors[k])

    def _apply_custom_theme(self):
        theme_manager.save_custom_theme(self.custom_colors); self.log("Custom theme applied!", "success")
        if hasattr(self, 'theme_var'): self.theme_var.set("Custom Design")

    def _build_config(self):
        container = tk.Frame(self.tab_config, bg=BG_MAIN, pady=20); container.pack(fill=tk.BOTH, expand=True)
        add_box = tk.LabelFrame(container, text=" IDENTITY UPLOAD ", bg=BG_MAIN, fg=ACCENT_SECONDARY, font=("Segoe UI", 10, "bold"), padx=25, pady=25); add_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        self.token_input = self._create_modern_entry(add_box, "ACCESS TOKEN")
        CyberButton(add_box, "IMPORT TOKEN", self.add_account, "accent_primary", width=280).pack(pady=5)
        CyberButton(add_box, "BATCH IMPORT", self.import_tokens_from_file, "accent_tertiary", width=280).pack(pady=5)
        proxy_box = tk.LabelFrame(container, text=" NETWORK SHIELD ", bg=BG_MAIN, fg=ACCENT_SECONDARY, font=("Segoe UI", 10, "bold"), padx=25, pady=25); proxy_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        tk.Checkbutton(proxy_box, text="Enable Proxy Tunneling", variable=self.use_proxy, bg=BG_MAIN, fg=TEXT_MAIN, selectcolor=BG_SIDEBAR).pack(anchor=tk.W)
        self.proxy_lbl = tk.Label(proxy_box, text=f"Proxies Loaded: {len(self.proxies)}", bg=BG_MAIN, fg=TEXT_DIM, pady=15); self.proxy_lbl.pack(anchor=tk.W)
        CyberButton(proxy_box, "FILTER PROXIES", self.import_and_check_proxies, "#4F545C", width=280).pack(pady=5)
        CyberButton(proxy_box, "GENERATE PROXIES", self.generate_proxies, WARNING, width=280).pack(pady=5)
        self.proxy_progress = ttk.Progressbar(proxy_box, orient="horizontal", mode="determinate", length=280); self.proxy_progress.pack(pady=15)

        right_frame = tk.Frame(container, bg=BG_MAIN); right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(0, 10))

        webhook_box = tk.LabelFrame(right_frame, text=" WEBHOOK LOGGING ", bg=BG_MAIN, fg=ACCENT_SECONDARY, font=("Segoe UI", 10, "bold"), padx=25, pady=25); webhook_box.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        tk.Label(webhook_box, text="Webhook URL", bg=BG_MAIN, fg=TEXT_DIM, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(5, 2))
        self.webhook_entry = tk.Entry(webhook_box, bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_SECONDARY, relief="flat", font=("Consolas", 11)); self.webhook_entry.pack(fill=tk.X, ipady=8)
        self.webhook_entry.insert(0, self.webhook_url)
        tk.Checkbutton(webhook_box, text="Enable Webhook Logging", variable=self.webhook_enabled, bg=BG_MAIN, fg=TEXT_MAIN, selectcolor=BG_SIDEBAR).pack(anchor=tk.W, pady=5)
        self.webhook_status_lbl = tk.Label(webhook_box, text="Not Verified", bg=BG_MAIN, fg=ERROR, font=("Segoe UI", 8, "bold")); self.webhook_status_lbl.pack(anchor=tk.W, pady=2)
        CyberButton(webhook_box, "TEST WEBHOOK", self._test_webhook, ACCENT_TERTIARY, width=280).pack(pady=5)

        discord_box = tk.LabelFrame(right_frame, text=" DISCORD LINK ", bg=BG_MAIN, fg=ACCENT_SECONDARY, font=("Segoe UI", 10, "bold"), padx=25, pady=25); discord_box.pack(fill=tk.BOTH, expand=True)
        tk.Label(discord_box, text="Bot URL", bg=BG_MAIN, fg=TEXT_DIM, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(5, 2))
        self.bot_url_entry = tk.Entry(discord_box, bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_SECONDARY, relief="flat", font=("Consolas", 11)); self.bot_url_entry.pack(fill=tk.X, ipady=8)
        self.bot_url_entry.insert(0, self.bot_url.get())
        self.bot_url_entry.bind("<KeyRelease>", lambda e: self.bot_url.set(self.bot_url_entry.get()))
        tk.Label(discord_box, text=f"License: {self.license_key[:16]}...", bg=BG_MAIN, fg=TEXT_DIM, font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=5)
        self.bot_status_lbl = tk.Label(discord_box, text="Not Linked", bg=BG_MAIN, fg=ERROR, font=("Segoe UI", 8, "bold")); self.bot_status_lbl.pack(anchor=tk.W, pady=2)
        CyberButton(discord_box, "LINK DISCORD", self._link_to_bot, ACCENT_PRIMARY, width=280).pack(pady=5)

        sep = tk.Frame(discord_box, height=1, bg=TEXT_DIM); sep.pack(fill=tk.X, pady=15)
        tk.Label(discord_box, text="Sync Code (from Discord `/sync`)", bg=BG_MAIN, fg=TEXT_DIM, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        self.sync_code_entry = tk.Entry(discord_box, bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_SECONDARY, relief="flat", font=("Consolas", 16, "bold"), justify=tk.CENTER); self.sync_code_entry.pack(fill=tk.X, ipady=8, pady=(5, 10))
        CyberButton(discord_box, "CLAIM CODE", self._claim_sync_code, ACCENT_TERTIARY, width=280).pack(pady=(0, 5))

    def _build_logs(self):
        self.stats = {"success": 0, "error": 0}
        stats_frame = tk.Frame(self.tab_logs, bg=BG_SIDEBAR, height=30); stats_frame.pack(fill=tk.X)
        tk.Label(stats_frame, text="LIVE SYSTEM MONITOR", font=("Segoe UI", 8, "bold"), bg=BG_SIDEBAR, fg=TEXT_DIM).pack(side=tk.LEFT, padx=20)
        self.stats_lbl = tk.Label(stats_frame, text="S: 0 | E: 0", font=("Consolas", 9, "bold"), bg=BG_SIDEBAR, fg=SUCCESS); self.stats_lbl.pack(side=tk.RIGHT, padx=20)
        self.log_box = scrolledtext.ScrolledText(self.tab_logs, bg="#050508", fg=SUCCESS, font=("Consolas", 11), borderwidth=0, padx=20, pady=20); self.log_box.pack(fill=tk.BOTH, expand=True)
        self.log("UMAX v8.2 - ADVANCED LOGGING SYSTEM ACTIVE", "auth")

    def _create_modern_entry(self, parent, label, **kwargs):
        tk.Label(parent, text=label, bg=BG_MAIN, fg=TEXT_DIM, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(15, 5))
        entry = tk.Entry(parent, bg=BG_CARD, fg=TEXT_MAIN, insertbackground=ACCENT_SECONDARY, relief="flat", font=("Segoe UI", 11), **kwargs); entry.pack(fill=tk.X, pady=(0, 2), ipady=10)
        tk.Frame(parent, height=2, bg=ACCENT_SECONDARY).pack(fill=tk.X, pady=(0, 15)); return entry

    def _draw_placeholder_avatar(self):
        self.avatar_canvas.delete("all"); self.avatar_canvas.create_oval(5, 5, 95, 95, fill=BG_SIDEBAR, outline=ACCENT_PRIMARY, width=3); self.avatar_canvas.create_text(50, 50, text="?", fill=ACCENT_PRIMARY, font=("Segoe UI", 30, "bold"))

    def log(self, msg, type="info"):
        now, time_short = datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%H:%M:%S")
        log_map = {"success": {"icon": "✅", "color": SUCCESS}, "error": {"icon": "❌", "color": ERROR}, "warn": {"icon": "⚠️", "color": WARNING}, "info": {"icon": "ℹ️", "color": TEXT_MAIN}, "auth": {"icon": "🔐", "color": ACCENT_SECONDARY}, "task": {"icon": "⚙️", "color": ACCENT_PRIMARY}}
        config = log_map.get(type, log_map["info"])
        if hasattr(self, 'stats'):
            if type == "success": self.stats['success'] += 1
            elif type == "error": self.stats['error'] += 1
        try:
            with open("umax_system_logs.txt", "a", encoding="utf-8") as f: f.write(f"[{now}] [{type.upper()}] {msg}\n")
        except: pass
        if hasattr(self, 'webhook_enabled') and self.webhook_enabled.get() and self.webhook_url:
            self._send_webhook(msg)
        def _ui_update():
            if hasattr(self, 'stats'): self._update_stats_display()
            self.log_box.insert(tk.END, f"[{time_short}] ", "time")
            self.log_box.insert(tk.END, f"{config['icon']} {msg}\n", type)
            self.log_box.tag_config("time", foreground=TEXT_DIM)
            self.log_box.tag_config(type, foreground=config['color'])
            self.log_box.see(tk.END)
        try:
            self.root.after(0, _ui_update)
        except:
            pass

    def _update_stats_display(self):
        if hasattr(self, 'stats_lbl'): self.stats_lbl.config(text=f"S: {self.stats['success']} | E: {self.stats['error']}")

    def refresh_table(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        query = self.search_var.get().lower().strip()
        for idx, acc in enumerate(self.accounts):
            if query and query not in acc.get('user', '').lower() and query not in acc.get('token', '').lower():
                continue
            t_disp = f"{acc['token'][:15]}..." if acc.get('token') else "---"
            self.tree.insert("", tk.END, values=(idx+1, acc.get('user', 'Unknown'), t_disp, acc.get('status', 'Ready'), acc.get('presence', 'Offline')))

    def _filter_table(self):
        query = self.search_var.get().lower().strip()
        for i in self.tree.get_children():
            self.tree.delete(i)
        for idx, acc in enumerate(self.accounts):
            if not query or query in acc.get('user', '').lower() or query in acc.get('token', '').lower():
                t_disp = f"{acc['token'][:15]}..." if acc.get('token') else "---"
                self.tree.insert("", tk.END, values=(idx+1, acc.get('user', 'Unknown'), t_disp, acc.get('status', 'Ready'), acc.get('presence', 'Offline')))

    def on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        idx = int(self.tree.item(sel[0])['values'][0]) - 1; acc = self.accounts[idx]
        self.user_name_lbl.config(text=acc.get('user', 'UMAX').upper())
        if acc.get('avatar_url'): threading.Thread(target=self.load_avatar, args=(acc['avatar_url'],), daemon=True).start()
        else: self._draw_placeholder_avatar()

    def load_avatar(self, url):
        try:
            if url in self.avatars_cache: img = self.avatars_cache[url]
            else:
                r = requests.get(url, timeout=5); raw_img = Image.open(io.BytesIO(r.content)).convert("RGBA").resize((90, 90), Image.Resampling.LANCZOS)
                mask = Image.new('L', (90, 90), 0); ImageDraw.Draw(mask).ellipse((0, 0, 90, 90), fill=255)
                output = Image.new('RGBA', (90, 90), (0,0,0,0)); output.paste(raw_img, (0,0), mask); img = ImageTk.PhotoImage(output); self.avatars_cache[url] = img
            self.root.after(0, lambda: self._update_avatar_ui(img))
        except: self.root.after(0, self._draw_placeholder_avatar)

    def _update_avatar_ui(self, img):
        self.avatar_canvas.delete("all"); self.avatar_canvas.create_image(50, 50, image=img); self.avatar_canvas.create_oval(5, 5, 95, 95, outline=ACCENT_SECONDARY, width=4)

    def get_proxy(self):
        if self.use_proxy.get() and self.proxies: p = random.choice(self.proxies); return {"http": f"http://{p}", "https": f"http://{p}"}
        return None

    def run_task(self, token, coro, *args):
        token = token.strip().replace('"', '').replace("'", "").replace('\n', '').replace('\r', '')
        self.log(f"🔍 Token preview: {token[:25]}... (len={len(token)})", "info")
        def worker():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                client = discord.Client(bot=False)
            except Exception as client_err:
                self.log(f"❌ Client creation failed: {client_err}", "error")
                try: loop.close()
                except: pass
                return

            async def safe_runner():
                try:
                    await client.start(token)
                except Exception as e:
                    self.log(f"❌ Login Failed: {e}", "error")
                finally:
                    if not client.is_closed():
                        await client.close()

            @client.event
            async def on_ready():
                try:
                    self.log(f"✅ Logged into [{client.user}]", "success")
                    for acc in self.accounts:
                        if acc['token'] == token:
                            acc['user'] = str(client.user)
                            break
                    self.root.after(0, self.refresh_table)
                    await coro(client, *args)
                except Exception as e:
                    self.log(f"❌ Task Error: {type(e).__name__}: {e}", "error")
                finally:
                    try:
                        await client.close()
                    except:
                        pass
                    loop.call_soon_threadsafe(loop.stop)

            try:
                loop.run_until_complete(safe_runner())
            finally:
                try: loop.close()
                except: pass
        threading.Thread(target=worker, daemon=True).start()

    def svc_dm_broadcast_advanced(self):
        dialog = tk.Toplevel(self.root); dialog.title("UMAX Broadcast"); dialog.geometry("450x550"); dialog.configure(bg=BG_CARD)
        tk.Label(dialog, text="SECURE BROADCAST", font=("Segoe UI", 12, "bold"), bg=BG_CARD, fg=ACCENT_SECONDARY).pack(pady=15)
        target_var = tk.StringVar(value="friends")
        for t, v in [("Friends List", "friends"), ("Active Private DMs", "all_dms"), ("Server Members (SCRAPE)", "server")]: ttk.Radiobutton(dialog, text=t, variable=target_var, value=v).pack()
        tk.Label(dialog, text="Server ID:", bg=BG_CARD, fg=TEXT_MAIN).pack(pady=(10,0)); sid_entry = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat"); sid_entry.pack(pady=5)
        tk.Label(dialog, text="Broadcast Message:", bg=BG_CARD, fg=TEXT_MAIN).pack(); msg_text = tk.Text(dialog, height=5, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat"); msg_text.pack(padx=20, pady=5)
        tk.Label(dialog, text="Delay (Seconds):", bg=BG_CARD, fg=TEXT_MAIN).pack(); delay_entry = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat"); delay_entry.insert(0, "5"); delay_entry.pack(pady=5)
        def start():
            t_type, sid, msg, delay = target_var.get(), sid_entry.get().strip(), msg_text.get("1.0", tk.END).strip(), float(delay_entry.get().strip())
            dialog.destroy(); self._execute_broadcast(t_type, sid, msg, delay)
        CyberButton(dialog, "EXECUTE CAMPAIGN", start, SUCCESS, width=220).pack(pady=20)

    def _execute_broadcast(self, t_type, sid, msg, delay):
        async def task(client, t_type, sid, msg, delay):
            targets = []
            try:
                if t_type == "friends":
                    targets = [r.user for r in client.relationships if hasattr(r, 'type') and r.type == discord.RelationshipType.friend]
                elif t_type == "all_dms":
                    r = self.handle_request("GET", "https://discord.com/api/v9/users/@me/channels", client.http.token)
                    if not isinstance(r, dict) and r.status_code == 200:
                        for dm in r.json():
                            if dm['type'] == 1:
                                try: targets.append(await client.fetch_user(int(dm['recipients'][0]['id'])))
                                except: pass
                elif t_type == "server" and sid:
                    guild = client.get_guild(int(sid)) or await client.fetch_guild(int(sid))
                    if guild:
                        async for member in guild.fetch_members(limit=None):
                            if not member.bot: targets.append(member)
                self.log(f"Found {len(targets)} targets. Starting...", "warn")
                sent = 0
                for user in targets:
                    if user.id == client.user.id: continue
                    try: await user.send(msg); sent += 1; self.log(f"Sent to {user}", "success"); await asyncio.sleep(delay)
                    except: self.log(f"Failed to send to {user}", "error")
                self.log(f"Broadcast complete: {sent}/{len(targets)} sent", "success")
            except Exception as e: self.log(f"Broadcast Error: {type(e).__name__}: {e}", "error")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task, t_type, sid, msg, delay)

    def svc_ar_smart_monitor(self):
        default_emo = simpledialog.askstring("Smart AR", "Default Emoji (optional):")
        async def task(client, def_e):
            monitored_channels = set()
            self.log(f"[{client.user}] Smart AR Active.", "success")
            async def on_message(message):
                content = message.content.lower()
                if any(t in content for t in self.triggers) or "@everyone" in content or "@here" in content:
                    if message.channel.id not in monitored_channels:
                        monitored_channels.add(message.channel.id); self.log(f"Monitoring: {message.channel.name}", "warn")
                    if def_e:
                        for e in def_e.split():
                            try: await message.add_reaction(e)
                            except: pass
            async def on_reaction_add(reaction, user):
                if reaction.message.channel.id in monitored_channels and user.id != client.user.id:
                    try: await reaction.message.add_reaction(reaction.emoji); self.log(f"Copied {reaction.emoji}", "success")
                    except: pass
            client.add_listener(on_message, 'on_message')
            client.add_listener(on_reaction_add, 'on_reaction_add')
            while True: await asyncio.sleep(3600)
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task, default_emo)

    def svc_ar_channel_fixed(self):
        cid, emo = simpledialog.askstring("Channel AR", "Channel ID:"), simpledialog.askstring("Channel AR", "Default Emoji:")
        if not cid: return
        async def task(client, c_id, def_e):
            target_id = int(c_id)
            async def on_message(message):
                if message.channel.id == target_id and def_e:
                    for e in def_e.split():
                        try: await message.add_reaction(e)
                        except: pass
            async def on_reaction_add(reaction, user):
                if reaction.message.channel.id == target_id and user.id != client.user.id:
                    try: await reaction.message.add_reaction(reaction.emoji)
                    except: pass
            client.add_listener(on_message, 'on_message')
            client.add_listener(on_reaction_add, 'on_reaction_add')
            while True: await asyncio.sleep(3600)
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task, cid, emo)

    def svc_check(self):
        async def task(client, idx):
            acc = self.accounts[idx]
            acc.setdefault('notes', '')
            r = self.handle_request("GET", "https://discord.com/api/v9/users/@me", client.http.token)
            if not isinstance(r, dict) and r.status_code == 200:
                data = r.json(); acc.update({'user': data['username'], 'avatar_url': f"https://cdn.discordapp.com/avatars/{data['id']}/{data['avatar']}.png" if data.get('avatar') else "", 'presence': "Online", 'status': "Active"})
                self.root.after(0, self.refresh_table); self.log(f"Verified: {data['username']}", "success")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task, idx)

    def svc_detailed_check(self):
        targets = self.get_targets()
        if not targets:
            messagebox.showinfo("No Targets", "Select accounts or add some first.")
            return
        results = {}
        def worker():
            for idx, acc in targets:
                token = acc['token'].strip().replace('"', '').replace("'", "").replace('\n', '').replace('\r', '')
                me = self.handle_request("GET", "https://discord.com/api/v9/users/@me", token)
                sub = self.handle_request("GET", "https://discord.com/api/v9/users/@me/billing/subscriptions", token)
                info = {}
                if not isinstance(me, dict) and me.status_code == 200:
                    d = me.json()
                    info['username'] = f"{d.get('username', '?')}#{d.get('discriminator', '0')}"
                    info['id'] = d.get('id', '?')
                    info['email'] = d.get('email', 'N/A')
                    info['verified'] = d.get('verified', False)
                    info['phone'] = d.get('phone', 'N/A')
                    info['nitro'] = d.get('premium_type', 0)
                    nitro_map = {0: "None", 1: "Nitro Classic", 2: "Nitro", 3: "Nitro Basic"}
                    info['nitro_type'] = nitro_map.get(info['nitro'], f"Unknown({info['nitro']})")
                    created_ts = ((int(d['id']) >> 22) + 1420070400000) / 1000
                    info['created'] = datetime.fromtimestamp(created_ts).strftime("%Y-%m-%d %H:%M:%S")
                    info['avatar'] = d.get('avatar', '?')
                    info['flags'] = d.get('flags', 0)
                    info['locale'] = d.get('locale', '?')
                    info['bot'] = d.get('bot', False)
                else:
                    info['error'] = "Failed to fetch user info"
                if not isinstance(sub, dict) and sub.status_code == 200:
                    subs = sub.json()
                    info['subscriptions'] = len(subs)
                    info['sub_details'] = [s.get('plan_id', '?') for s in subs] if subs else []
                else:
                    info['subscriptions'] = 0
                    info['sub_details'] = []
                results[idx] = info
            self.root.after(0, lambda: self._show_detailed_check_dialog(results))
        threading.Thread(target=worker, daemon=True).start()

    def _show_detailed_check_dialog(self, results):
        dialog = tk.Toplevel(self.root)
        dialog.title("UMAX Detailed Analysis")
        dialog.geometry("900x600")
        dialog.configure(bg=BG_CARD)
        tk.Label(dialog, text="TOKEN ANALYSIS REPORT", font=("Segoe UI", 14, "bold"), bg=BG_CARD, fg=ACCENT_PRIMARY).pack(pady=15)
        text_w = scrolledtext.ScrolledText(dialog, bg=BG_MAIN, fg=TEXT_MAIN, font=("Consolas", 10), borderwidth=0, padx=15, pady=15)
        text_w.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        for idx, info in results.items():
            acc = self.accounts[idx]
            text_w.insert(tk.END, f"{'='*60}\n", "header")
            text_w.insert(tk.END, f"TOKEN: {acc.get('token', '')[:20]}...\n", "header")
            text_w.tag_config("header", foreground=ACCENT_SECONDARY, font=("Consolas", 10, "bold"))
            if 'error' in info:
                text_w.insert(tk.END, f"ERROR: {info['error']}\n\n", "error")
                text_w.tag_config("error", foreground=ERROR)
                continue
            for label, key in [("Username", "username"), ("User ID", "id"), ("Email", "email"),
                                ("Verified", "verified"), ("Phone", "phone"), ("Nitro", "nitro_type"),
                                ("Created", "created"), ("Avatar Hash", "avatar"),
                                ("Flags", "flags"), ("Locale", "locale"), ("Bot", "bot")]:
                val = info.get(key, 'N/A')
                color = SUCCESS if val is True else (ERROR if val is False else TEXT_MAIN)
                text_w.insert(tk.END, f"  {label}: ", "label")
                text_w.tag_config("label", foreground=TEXT_DIM)
                text_w.insert(tk.END, f"{val}\n", "val")
                text_w.tag_config("val", foreground=color)
            text_w.insert(tk.END, f"  Subscriptions: {info.get('subscriptions', 0)}\n", "label")
            if info.get('sub_details'):
                text_w.insert(tk.END, f"  Plans: {', '.join(info['sub_details'])}\n", "val")
            text_w.insert(tk.END, "\n")
        CyberButton(dialog, "CLOSE", dialog.destroy, ERROR, width=160).pack(pady=10)

    def _show_account_details(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(self.tree.item(sel[0])['values'][0]) - 1
        acc = self.accounts[idx]
        dialog = tk.Toplevel(self.root)
        dialog.title("Account Details")
        dialog.geometry("500x400")
        dialog.configure(bg=BG_CARD)
        tk.Label(dialog, text="ACCOUNT DETAILS", font=("Segoe UI", 14, "bold"), bg=BG_CARD, fg=ACCENT_PRIMARY).pack(pady=10)
        tk.Frame(dialog, height=2, bg=ACCENT_SECONDARY).pack(fill=tk.X, padx=20)
        info_frame = tk.Frame(dialog, bg=BG_CARD, padx=20, pady=10); info_frame.pack(fill=tk.X)
        details = [("Username", acc.get('user', 'Unknown')), ("Token", f"{acc.get('token', '')[:20]}..."), ("Status", acc.get('status', 'Ready')), ("Presence", acc.get('presence', 'Offline')), ("Account ID", acc.get('id', 'N/A'))]
        for label, value in details:
            row = tk.Frame(info_frame, bg=BG_CARD); row.pack(fill=tk.X, pady=1)
            tk.Label(row, text=label + ":", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_DIM, width=12, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=value, font=("Consolas", 9), bg=BG_CARD, fg=TEXT_MAIN).pack(side=tk.LEFT, padx=5)
        tk.Frame(dialog, height=2, bg=BG_SIDEBAR).pack(fill=tk.X, padx=20, pady=5)
        tk.Label(dialog, text="NOTES", font=("Segoe UI", 10, "bold"), bg=BG_CARD, fg=ACCENT_SECONDARY).pack(anchor=tk.W, padx=20)
        notes_text = scrolledtext.ScrolledText(dialog, bg=BG_MAIN, fg=TEXT_MAIN, font=("Consolas", 10), borderwidth=0, height=6, padx=10, pady=10)
        notes_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        notes_text.insert("1.0", acc.get('notes', ''))
        def save_notes():
            acc['notes'] = notes_text.get("1.0", tk.END).strip()
            self.save_accounts()
        dialog.protocol("WM_DELETE_WINDOW", lambda: [save_notes(), dialog.destroy()])
        btn_frame = tk.Frame(dialog, bg=BG_CARD, pady=10); btn_frame.pack(fill=tk.X)
        CyberButton(btn_frame, "COPY TOKEN", lambda: [self.root.clipboard_clear(), self.root.clipboard_append(acc.get('token', '')), self.log("Token copied to clipboard", "success")], SUCCESS, width=140).pack(side=tk.LEFT, padx=10)
        CyberButton(btn_frame, "SAVE & CLOSE", lambda: [save_notes(), dialog.destroy()], ACCENT_PRIMARY, width=140).pack(side=tk.RIGHT, padx=10)

    def svc_view_guilds(self):
        targets = self.get_targets()
        if not targets:
            messagebox.showinfo("No Targets", "Select accounts or add some first.")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("UMAX Guild Viewer")
        dialog.geometry("900x600")
        dialog.configure(bg=BG_CARD)
        tk.Label(dialog, text="SERVER LIST — GUILD VIEWER", font=("Segoe UI", 14, "bold"), bg=BG_CARD, fg=ACCENT_PRIMARY).pack(pady=15)
        
        outer = tk.Frame(dialog, bg=BG_CARD, padx=20, pady=10)
        outer.pack(fill=tk.BOTH, expand=True)
        
        tree = ttk.Treeview(outer, columns=("account", "id", "name", "members", "boost", "owner"), show="headings", height=20)
        for col, w in [("account", 180), ("id", 120), ("name", 250), ("members", 80), ("boost", 80), ("owner", 120)]:
            tree.heading(col, text=col.upper())
            tree.column(col, width=w, anchor="center")
        
        vsb = ttk.Scrollbar(outer, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        status_lbl = tk.Label(dialog, text="Fetching guilds...", bg=BG_CARD, fg=TEXT_DIM)
        status_lbl.pack(pady=5)
        all_rows = []
        progress_lbl = tk.Label(dialog, text="", bg=BG_CARD, fg=ACCENT_PRIMARY)
        progress_lbl.pack(pady=2)

        def fetch_one(token, acc_name):
            rows = []
            async def task(client):
                nonlocal rows
                for g in client.guilds:
                    try:
                        boost = "None"
                        if g.premium_tier:
                            boost = f"T{g.premium_tier}"
                        owner = "Yes" if g.owner_id == client.user.id else "No"
                        rows.append((acc_name, str(g.id), g.name, str(g.member_count), boost, owner))
                    except:
                        pass
            self.run_task(token, task)
            start = time.time()
            while time.time() - start < 15:
                if rows:
                    break
                time.sleep(0.5)
            return rows

        def fetch_all():
            for i, (idx, acc) in enumerate(targets):
                name = acc.get('user', 'Unknown')
                dialog.after(0, lambda n=name, c=i+1: status_lbl.config(text=f"Fetching [{c}/{len(targets)}]: {n}") if status_lbl.winfo_exists() else None)
                result = fetch_one(acc['token'], name)
                all_rows.extend(result)
                dialog.after(0, lambda c=i+1: progress_lbl.config(text=f"✅ {c}/{len(targets)} accounts done") if progress_lbl.winfo_exists() else None)
            def update_ui():
                if not dialog.winfo_exists(): return
                tree.delete(*tree.get_children())
                for row in all_rows:
                    tree.insert("", tk.END, values=row)
                status_lbl.config(text=f"Loaded {len(all_rows)} guilds from {len(targets)} accounts")
                progress_lbl.config(text="Done", fg=SUCCESS)
            dialog.after(0, update_ui)
        
        threading.Thread(target=fetch_all, daemon=True).start()
    
    def svc_quick_name(self):
        name = simpledialog.askstring("Name", "New Name:")
        if name:
            self.log(f"Changing name to: {name}...", "info")
            self._bulk_id_update(lambda c, n: self.handle_request("PATCH", "https://discord.com/api/v9/users/@me", c.http.token, json_data={"global_name":n}), name)

    def svc_quick_bio(self):
        bio = simpledialog.askstring("Bio", "New Bio:")
        if bio:
            self.log(f"Changing bio...", "info")
            self._bulk_id_update(lambda c, b: self.handle_request("PATCH", "https://discord.com/api/v9/users/@me", c.http.token, json_data={"bio":b}), bio)

    def svc_quick_avatar(self):
        path = filedialog.askopenfilename()
        if path:
            self.log(f"Changing avatar...", "info")
            with open(path, "rb") as f: avatar_data = f.read()
            self._bulk_id_update(lambda c, a: c.user.edit(avatar=a), avatar_data)

    def _bulk_id_update(self, func, val):
        async def task(client, v):
            try:
                result = func(client, v)
                if asyncio.iscoroutine(result): await result
                self.log(f"Update Success", "success")
            except Exception as e: self.log(f"Update Error: {e}", "error")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task, val)

    def svc_change_presence(self, st):
        async def task(client, s):
            sm = {"online": discord.Status.online, "idle": discord.Status.idle, "dnd": discord.Status.dnd}
            await client.change_presence(status=sm.get(s, discord.Status.online))
            self.log(f"Presence set to {s}", "success")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task, st)

    def svc_dm_spammer(self):
        tid, msg, cnt = simpledialog.askstring("Spam", "User ID:"), simpledialog.askstring("Spam", "Message:"), simpledialog.askinteger("Spam", "Count:")
        if tid and msg:
            async def task(client, t, m, c):
                u = await client.fetch_user(int(t))
                for i in range(c):
                    try: await u.send(m); self.log(f"Spam {i+1}/{c} to {u}", "success"); await asyncio.sleep(1)
                    except: self.log(f"Spam {i+1}/{c} failed", "error")
            for idx, acc in self.get_targets(): self.run_task(acc['token'], task, tid, msg, cnt)

    def svc_dm_clearer(self):
        if not messagebox.askyesno("Confirm", "Clear ALL DM channels?"): return
        async def task(client):
            r = self.handle_request("GET", "https://discord.com/api/v9/users/@me/channels", client.http.token)
            if not isinstance(r, dict) and r.status_code == 200:
                count = 0
                for dm in r.json():
                    res = self.handle_request("DELETE", f"https://discord.com/api/v9/channels/{dm['id']}", client.http.token)
                    if not isinstance(res, dict): count += 1
                    time.sleep(0.5)
                self.log(f"Cleared {count} DM channels", "success")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task)

    def svc_remove_all_friends(self):
        if not messagebox.askyesno("Confirm", "Remove ALL friends?"): return
        async def task(client):
            count = 0
            friends = [r for r in client.relationships if hasattr(r, 'type') and r.type == discord.RelationshipType.friend]
            for r in friends:
                try:
                    await r.delete()
                    count += 1
                    await asyncio.sleep(0.5)
                except Exception as e:
                    self.log(f"Failed to remove friend: {e}", "error")
            self.log(f"Removed {count} friends", "success")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task)

    def svc_reject_all_requests(self):
        if not messagebox.askyesno("Confirm", "Reject ALL pending requests?"): return
        async def task(client):
            count = 0
            for r in list(client.relationships):
                if r.type in (discord.RelationshipType.incoming_request, discord.RelationshipType.outgoing_request):
                    try:
                        await r.delete()
                        count += 1
                        await asyncio.sleep(0.5)
                    except: pass
            self.log(f"Rejected {count} requests", "success")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task)

    def svc_join(self):
        import threading as _th
        link = simpledialog.askstring("Join", "Invite Link:")
        if link:
            code = link.split("/")[-1]
            async def task(client, cd):
                try:
                    resp = self.handle_request("POST", f"https://discord.com/api/v9/invites/{cd}", client.http.token, json_data={})
                    if not isinstance(resp, dict) and resp.status_code == 200:
                        data = resp.json(); self.log(f"✅ Joined: {data.get('guild', {}).get('name', 'Unknown')}", "success"); return
                    webbrowser.open(link)
                    self.log(f"⚠️ Captcha — browser opened, join manually then confirm", "warn")
                    ev = _th.Event()
                    self.root.after(0, lambda: [messagebox.showinfo("Captcha", "Join in the browser.\nPress OK after joining."), ev.set()])
                    ev.wait()
                    retry = self.handle_request("POST", f"https://discord.com/api/v9/invites/{cd}", client.http.token, json_data={})
                    if not isinstance(retry, dict) and retry.status_code == 200:
                        data = retry.json(); self.log(f"✅ Joined after manual solve", "success")
                    else: self.log(f"❌ Still blocked — try again later", "error")
                except Exception as e: self.log(f"Join error: {e}", "error")
            for idx, acc in self.get_targets(): self.run_task(acc['token'], task, code)

    def svc_leave_all(self):
        if not messagebox.askyesno("Confirm", "Leave ALL servers?"): return
        async def task(client):
            count = 0
            for g in list(client.guilds):
                try: await g.leave(); count += 1; self.log(f"Left: {g.name}", "success"); await asyncio.sleep(1)
                except: pass
            self.log(f"Left {count} servers total", "success")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task)

    def svc_mass_leave(self):
        gid = simpledialog.askstring("Leave", "Server ID:")
        if gid:
            if not messagebox.askyesno("Confirm", f"Leave server {gid}?"): return
            async def task(client, g_id):
                guild = client.get_guild(int(g_id))
                if guild: await guild.leave(); self.log(f"Left server: {guild.name}", "success")
                else: self.log(f"Server {g_id} not found", "error")
            for idx, acc in self.get_targets(): self.run_task(acc['token'], task, gid)

    def svc_friend(self):
        target = simpledialog.askstring("Friend", "User ID:")
        if target:
            async def task(client, t):
                u = await client.fetch_user(int(t)); await u.send_friend_request()
                self.log(f"Friend request sent to {u}", "success")
            for idx, acc in self.get_targets(): self.run_task(acc['token'], task, target)

    def svc_24_7_online(self):
        async def task(client):
            await client.change_presence(status=discord.Status.online)
            self.log("24/7 Online mode activated", "success")
            while True: await asyncio.sleep(3600)
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task)

    def svc_streaming(self):
        text = simpledialog.askstring("Stream", "Text:")
        if text:
            async def task(client, t):
                await client.change_presence(activity=discord.Activity(name=t, url="https://twitch.tv/discord", type=discord.ActivityType.streaming))
                self.log(f"Streaming mode: {t}", "success")
                while True: await asyncio.sleep(3600)
            for idx, acc in self.get_targets(): self.run_task(acc['token'], task, text)

    def svc_bulk_names(self):
        if os.path.exists("names.txt"):
            with open("names.txt", "r") as f: names = [l.strip() for l in f if l.strip()]
            async def task(client, n):
                r = self.handle_request("PATCH", "https://discord.com/api/v9/users/@me", client.http.token, json_data={"global_name":n})
                if not isinstance(r, dict): self.log(f"Name set to: {n}", "success")
                else: self.log(f"Name update failed", "error")
            for i, (idx, acc) in enumerate(self.get_targets()):
                if i < len(names): self.run_task(acc['token'], task, names[i]); time.sleep(3)
            self.log(f"Bulk name change started for {min(len(self.get_targets()), len(names))} accounts", "info")

    def svc_bulk_avatars(self):
        if os.path.exists("avatars"):
            imgs = [f for f in os.listdir("avatars") if f.lower().endswith(('.png', '.jpg'))]
            async def task(client, i_name):
                try:
                    with open(f"avatars/{i_name}", "rb") as f: await client.user.edit(avatar=f.read())
                    self.log(f"Avatar set to: {i_name}", "success")
                except Exception as e: self.log(f"Avatar failed: {e}", "error")
            for idx, acc in self.get_targets(): self.run_task(acc['token'], task, random.choice(imgs)); time.sleep(4)
            self.log(f"Bulk avatar change started for {len(self.get_targets())} accounts", "info")

    def svc_bulk_bios(self):
        if os.path.exists("bios.txt"):
            with open("bios.txt", "r") as f: bios = [l.strip() for l in f if l.strip()]
            async def task(client, b):
                r = self.handle_request("PATCH", "https://discord.com/api/v9/users/@me", client.http.token, json_data={"bio":b})
                if not isinstance(r, dict): self.log(f"Bio updated", "success")
                else: self.log(f"Bio update failed", "error")
            for i, (idx, acc) in enumerate(self.get_targets()):
                if i < len(bios): self.run_task(acc['token'], task, bios[i]); time.sleep(3)
            self.log(f"Bulk bio change started for {min(len(self.get_targets()), len(bios))} accounts", "info")

    def svc_hypesquad(self):
        h_id = simpledialog.askstring("HypeSquad", "House ID (1,2,3):")
        if h_id:
            houses = {"1": "Bravery", "2": "Brilliance", "3": "Balance"}
            async def task(client, h):
                r = self.handle_request("POST", "https://discord.com/api/v9/hypesquad/online", client.http.token, json_data={"house_id":int(h)})
                if not isinstance(r, dict) and r.status_code == 204:
                    self.log(f"HypeSquad set to {houses.get(h, 'Unknown')}", "success")
                else: self.log(f"HypeSquad change failed", "error")
            for idx, acc in self.get_targets(): self.run_task(acc['token'], task, h_id)

    def svc_voice_247(self):
        dialog = tk.Toplevel(self.root); dialog.title("UMAX Voice 24/7"); dialog.geometry("500x620"); dialog.configure(bg=BG_CARD)
        tk.Label(dialog, text="VOICE CHANNEL 24/7", font=("Segoe UI", 14, "bold"), bg=BG_CARD, fg=ACCENT_TERTIARY).pack(pady=15)
        frame = tk.Frame(dialog, bg=BG_CARD, padx=30); frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(frame, text="Voice Channel ID *", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(10, 2))
        vc_entry = tk.Entry(frame, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat", font=("Consolas", 11)); vc_entry.pack(fill=tk.X, ipady=8)
        tk.Label(frame, text="Server ID (Guild) *", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(10, 2))
        gid_entry = tk.Entry(frame, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat", font=("Consolas", 11)); gid_entry.pack(fill=tk.X, ipady=8)
        tk.Label(frame, text="Status", bg=BG_CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, pady=(10, 2))
        status_var = tk.StringVar(value="online")
        status_frame = tk.Frame(frame, bg=BG_CARD); status_frame.pack(fill=tk.X)
        for st in ["online", "idle", "dnd", "streaming"]: ttk.Radiobutton(status_frame, text=st.upper(), variable=status_var, value=st).pack(side=tk.LEFT, padx=5)
        tk.Label(frame, text="Stream Title (if streaming)", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(10, 2))
        title_entry = tk.Entry(frame, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat"); title_entry.insert(0, "Live Now"); title_entry.pack(fill=tk.X, ipady=6)
        tk.Label(frame, text="Stream URL (if streaming)", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(10, 2))
        url_entry = tk.Entry(frame, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat"); url_entry.insert(0, "https://twitch.tv/stream"); url_entry.pack(fill=tk.X, ipady=6)
        tk.Label(frame, text="Server Nickname (optional)", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 8)).pack(anchor=tk.W, pady=(10, 2))
        nick_entry = tk.Entry(frame, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat"); nick_entry.pack(fill=tk.X, ipady=6)
        voice_opts = tk.Frame(frame, bg=BG_CARD); voice_opts.pack(fill=tk.X, pady=(10, 0))
        mute_var = tk.BooleanVar(value=True)
        deaf_var = tk.BooleanVar(value=False)
        tk.Checkbutton(voice_opts, text="Mute Microphone", variable=mute_var, bg=BG_CARD, fg=TEXT_MAIN, selectcolor=BG_SIDEBAR).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(voice_opts, text="Deafen (cut sound)", variable=deaf_var, bg=BG_CARD, fg=TEXT_MAIN, selectcolor=BG_SIDEBAR).pack(side=tk.LEFT, padx=5)
        info_lbl = tk.Label(frame, text="* Required fields", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 7)); info_lbl.pack(pady=(10, 5))
        btn_frame = tk.Frame(dialog, bg=BG_CARD, pady=15); btn_frame.pack(fill=tk.X)
        def start():
            vc_id, g_id = vc_entry.get().strip(), gid_entry.get().strip()
            if not vc_id or not g_id: messagebox.showerror("Error", "Voice Channel ID & Server ID are required"); return
            status, title, url, nick = status_var.get(), title_entry.get().strip(), url_entry.get().strip(), nick_entry.get().strip()
            dialog.destroy(); self._execute_voice_247(vc_id, g_id, status, title, url, nick, mute_var.get(), deaf_var.get())
        CyberButton(btn_frame, "START 24/7 VOICE", start, SUCCESS, width=280, height=45).pack()

    def _execute_voice_247(self, vc_id, g_id, status, title, url, nick, mute_self=False, deaf_self=False):
        async def task(client, v_id, gid, st, ttl, u, nk, mute, deaf):
            try:
                guild = client.get_guild(int(gid))
                if not guild:
                    guild = await client.fetch_guild(int(gid))
                if not guild:
                    self.log(f"❌ Guild {gid} not found", "error"); return
                channel = guild.get_channel(int(v_id))
                if not channel:
                    channel = await guild.fetch_channel(int(v_id))
                if not channel:
                    self.log(f"❌ Voice channel {v_id} not found in guild", "error"); return
                self.voice_originals[client.http.token] = {"guild_id": gid, "vc_id": v_id}
                sm = {"online": discord.Status.online, "idle": discord.Status.idle, "dnd": discord.Status.dnd}
                if st == "streaming":
                    activity = discord.Activity(name=ttl, url=u if u else "https://twitch.tv/discord", type=discord.ActivityType.streaming)
                    await client.change_presence(activity=activity)
                else:
                    await client.change_presence(status=sm.get(st, discord.Status.online))
                if nk:
                    member = guild.get_member(client.user.id) or await guild.fetch_member(client.user.id)
                    if member:
                        self.voice_originals[client.http.token]["original_nick"] = member.nick
                        await member.edit(nick=nk)
                await guild.change_voice_state(channel=channel, self_mute=mute, self_deaf=deaf)
                for _ in range(10):
                    await asyncio.sleep(2)
                    me = guild.get_member(client.user.id)
                    if me and me.voice and me.voice.channel == channel:
                        self.log(f"✅ Voice 24/7: connected to {channel.name} in {guild.name}", "success")
                        break
                else:
                    self.log(f"❌ Failed to join voice channel", "error"); return
                while True:
                    await asyncio.sleep(30)
                    session = self.voice_originals.get(client.http.token)
                    if not session or session.get("stopped"):
                        self.log("Voice session ended by user", "warn"); break
                    me = guild.get_member(client.user.id)
                    if not me or not me.voice or me.voice.channel != channel:
                        self.log(f"⚠️ Not in voice, reconnecting...", "warn")
                        await guild.change_voice_state(channel=channel, self_mute=mute, self_deaf=deaf)
                        await asyncio.sleep(5)
            except Exception as e: self.log(f"❌ Voice 24/7 Error ({type(e).__name__}): {e}", "error")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task, vc_id, g_id, status, title, url, nick, mute_self, deaf_self)

    def svc_stop_voice(self):
        async def task(client):
            try:
                count = 0
                token = client.http.token
                saved = self.voice_originals.get(token)
                if saved: saved["stopped"] = True
                saved = self.voice_originals.pop(token, None)
                for guild in client.guilds:
                    me = guild.get_member(client.user.id)
                    if me and me.voice and me.voice.channel:
                        await guild.change_voice_state(channel=None)
                        count += 1
                        self.log(f"Left voice in: {guild.name}", "success")
                        await asyncio.sleep(1)
                if not count:
                    self.log(f"Not in any voice channel", "warn")
                if saved:
                    gid = saved.get("guild_id")
                    original_nick = saved.get("original_nick")
                    if original_nick is not None and gid:
                        self.handle_request("PATCH", f"https://discord.com/api/v9/guilds/{gid}/members/@me", token, json_data={"nick": original_nick if original_nick else None})
                        self.log("Nickname restored", "success")
                    self.handle_request("PATCH", "https://discord.com/api/v9/users/@me", token, json_data={"custom_status": None})
                await client.change_presence(status=discord.Status.online)
                self.log(f"Voice stopped, state restored", "success")
            except Exception as e: self.log(f"Stop voice error: {e}", "error")
        for idx, acc in self.get_targets(): self.run_task(acc['token'], task)

    def add_trigger(self):
        t = simpledialog.askstring("Trigger", "New Keyword:")
        if t: self.triggers.append(t.lower()); self.trig_list.insert(tk.END, t); self.save_triggers()

    def remove_trigger(self):
        sel = self.trig_list.curselection()
        if sel: val = self.trig_list.get(sel[0]); self.triggers.remove(val); self.trig_list.delete(sel[0]); self.save_triggers()

    def add_account(self):
        t = self.token_input.get().strip()
        if not t:
            messagebox.showwarning("Empty Token", "Paste a token first.")
            return
        t = re.sub(r'[\s"\']', '', t)
        if not self._validate_token(t):
            messagebox.showerror("Invalid Token", "The token doesn't look valid.\nExpected format: base64-encoded, 50+ characters.")
            if messagebox.askyesno("Force Add?", "Add anyway?"):
                pass
            else:
                return
        self.accounts.append({"user": "Pending...", "token": t, "notes": ""}); self.save_accounts(); self.refresh_table(); self.svc_check()

    def export_accounts(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")], initialfile="exported_tokens.txt")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                for acc in self.accounts:
                    f.write(acc.get('token', '') + "\n")
            self.log(f"Exported {len(self.accounts)} tokens to {path}", "success")
            messagebox.showinfo("Export Complete", f"Exported {len(self.accounts)} tokens.")
        except Exception as e:
            self.log(f"Export failed: {e}", "error")
            messagebox.showerror("Export Error", str(e))

    def delete_selected(self):
        sel = self.tree.selection()
        if sel:
            if not messagebox.askyesno("Confirm", f"Delete {len(sel)} account(s)?"): return
            indices = sorted([int(self.tree.item(i)['values'][0])-1 for i in sel], reverse=True)
            for i in indices: self.accounts.pop(i)
            self.save_accounts(); self.refresh_table()

    def import_tokens_from_file(self):
        path = filedialog.askopenfilename(title="Select Token File", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            imported = 0
            skipped = 0
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    token = re.sub(r'[\s"\']', '', line.strip())
                    if not token:
                        continue
                    parts = token.split(':')
                    if len(parts) >= 3:
                        token = parts[-1]
                    token = token.strip()
                    if self._validate_token(token):
                        if not any(a['token'] == token for a in self.accounts):
                            self.accounts.append({"user": "Pending...", "token": token, "notes": ""})
                            imported += 1
                        else:
                            skipped += 1
                    else:
                        skipped += 1
            self.save_accounts()
            self.refresh_table()
            self.log(f"Imported {imported} tokens from file ({skipped} skipped)", "success")
            messagebox.showinfo("Import Complete", f"Imported: {imported}\nSkipped: {skipped}")
        except Exception as e:
            messagebox.showerror("Import Error", str(e))
            self.log(f"Token import failed: {e}", "error")

    def import_and_check_proxies(self):
        path = filedialog.askopenfilename()
        if path:
            with open(path, "r") as f: raw = [l.strip() for l in f if l.strip()]
            self.proxy_progress['maximum'], self.proxy_progress['value'] = len(raw), 0
            
            def check_single(p):
                try:
                    proxies = {"http": f"http://{p}", "https": f"http://{p}"}
                    r = requests.get("https://discord.com/api/v9/experiments", proxies=proxies, timeout=15)
                    if r.status_code == 200:
                        return p
                except: pass
                return None
            
            import concurrent.futures
            counter = [0]
            lock = threading.Lock()
            
            def checker():
                valid = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                    futures = {executor.submit(check_single, p): p for p in raw}
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        if result:
                            valid.append(result)
                        with lock:
                            counter[0] += 1
                            c = counter[0]
                        self.root.after(0, lambda c=c: self.proxy_progress.configure(value=c))
                
                self.proxies = valid
                with open(self.proxies_file, "w") as f: f.write("\n".join(self.proxies))
                self.root.after(0, lambda: self.proxy_lbl.config(text=f"Proxies Loaded: {len(self.proxies)}"))
            threading.Thread(target=checker, daemon=True).start()

    def generate_proxies(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Proxy Generator")
        dialog.geometry("450x350")
        dialog.configure(bg=BG_CARD)
        tk.Label(dialog, text="Proxy Generator", font=("Segoe UI", 14, "bold"), bg=BG_CARD, fg=ACCENT_PRIMARY).pack(pady=10)
        tk.Label(dialog, text="Count to generate", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=20)
        count_entry = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, relief="flat", font=("Consolas", 11))
        count_entry.insert(0, "200"); count_entry.pack(fill=tk.X, padx=20, pady=5, ipady=6)
        tk.Label(dialog, text="Threads", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=20)
        thread_var = tk.StringVar(value="50")
        thread_combo = ttk.Combobox(dialog, textvariable=thread_var, values=["10", "25", "50", "100"], state="readonly")
        thread_combo.pack(fill=tk.X, padx=20, pady=5)
        status_lbl = tk.Label(dialog, text="Status: Ready", bg=BG_CARD, fg=TEXT_DIM, font=("Segoe UI", 9))
        status_lbl.pack(pady=5)
        progress = ttk.Progressbar(dialog, orient="horizontal", mode="determinate", length=400)
        progress.pack(pady=10, padx=20)
        def run_generate():
            count = int(count_entry.get().strip())
            threads = int(thread_var.get())
            status_lbl.config(text="Generating & checking proxies...", fg=WARNING)
            dialog.update()
            ranges = ["174.138", "103", "38", "45", "131", "157", "185", "197", "190", "181"]
            ports = [80, 8080, 3128, 999, 1080, 8888, 8118]
            candidates = []
            for _ in range(count):
                first = random.choice(ranges)
                if first.count('.') == 1:
                    ip = f"{first}.{random.randint(1,254)}.{random.randint(1,254)}"
                else:
                    ip = f"{first}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
                candidates.append(ip)
            valid = []
            progress['maximum'] = len(candidates)
            lock = threading.Lock()
            def check_proxy(ip):
                for port in ports:
                    try:
                        proxy_str = f"{ip}:{port}"
                        proxies = {"http": f"http://{proxy_str}", "https": f"http://{proxy_str}"}
                        r = requests.get("https://discord.com/api/v9/experiments", proxies=proxies, timeout=10)
                        if r.status_code == 200:
                            return proxy_str
                    except:
                        pass
                return None
            counter = [0]
            def worker():
                nonlocal valid
                with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
                    futures = {executor.submit(check_proxy, ip): ip for ip in candidates}
                    for future in concurrent.futures.as_completed(futures):
                        result = future.result()
                        if result:
                            valid.append(result)
                        with lock:
                            counter[0] += 1
                            c = counter[0]
                        dialog.after(0, lambda c=c: progress.configure(value=c))
                self.proxies = valid
                with open(self.proxies_file, "w") as f:
                    f.write("\n".join(self.proxies))
                dialog.after(0, lambda: status_lbl.config(text=f"Done! Valid: {len(valid)}/{count}", fg=SUCCESS))
                dialog.after(0, lambda: self.proxy_lbl.config(text=f"Proxies Loaded: {len(self.proxies)}"))
                dialog.after(0, lambda: messagebox.showinfo("Complete", f"Generated {len(valid)} valid proxies out of {count} attempts."))
                dialog.after(5000, dialog.destroy)
            threading.Thread(target=worker, daemon=True).start()
        CyberButton(dialog, "START", run_generate, SUCCESS, width=200).pack(pady=10)

    def logout(self):
        clear_license_key()
        self.log("Logged out. Returning to login screen...", "warn")
        show_login(self.root)

    def get_targets(self):
        sel = self.tree.selection()
        if not sel: return [(i, self.accounts[i]) for i in range(len(self.accounts))]
        return [(int(self.tree.item(i)['values'][0])-1, self.accounts[int(self.tree.item(i)['values'][0])-1]) for i in sel]

    def _validate_token(self, token):
        token = token.strip()
        if len(token) < 50:
            return False
        if not re.match(r'^[A-Za-z0-9._\-\~]+$', token):
            return False
        parts = token.split('.')
        if len(parts) == 3:
            return all(len(p) > 5 for p in parts)
        return True

    def _send_webhook(self, message):
        if not hasattr(self, 'webhook_enabled') or not self.webhook_enabled.get():
            return
        if not self.webhook_url:
            return
        try:
            requests.post(self.webhook_url, json={"content": message}, timeout=10)
        except:
            pass

    def _link_to_bot(self):
        if not self.license_key:
            messagebox.showerror("Error", "No license key found. Please log in again.")
            return
        base = self.bot_url.get().rstrip("/")
        oauth_url = f"{base}/auth/discord?license_key={self.license_key}"
        status_url = f"{base}/api/link-status?license_key={self.license_key}"
        self.bot_status_lbl.config(text="Opening Discord authorization...", fg=WARNING)
        import webbrowser
        webbrowser.open(oauth_url)
        def poll():
            for _ in range(120):
                time.sleep(2)
                try:
                    r = requests.get(status_url, timeout=5)
                    data = r.json()
                    if data.get("status") == "linked":
                        dname = data.get("discord_name", "Unknown")
                        self.root.after(0, lambda dn=dname: self.bot_status_lbl.config(
                            text=f"Linked: {dn}", fg=SUCCESS))
                        self.root.after(0, lambda: messagebox.showinfo("Linked!",
                            f"Discord account {dname} linked successfully!"))
                        return
                except: pass
            self.root.after(0, lambda: self.bot_status_lbl.config(text="Timed out. Try again.", fg=ERROR))
        threading.Thread(target=poll, daemon=True).start()

    def _claim_sync_code(self):
        code = self.sync_code_entry.get().strip()
        if not code:
            messagebox.showerror("Error", "Enter a sync code from Discord `/sync`")
            return
        if not self.license_key:
            messagebox.showerror("Error", "No license key found. Please log in again.")
            return
        base = self.bot_url.get().rstrip("/")
        def do_claim():
            try:
                r = requests.post(f"{base}/api/code-claim", json={
                    "code": code,
                    "license_key": self.license_key,
                }, timeout=10)
                data = r.json()
                if data.get("success"):
                    self.root.after(0, lambda: (
                        self.bot_status_lbl.config(text=f"Synced: {data.get('discord_id', '')[:8]}...", fg=SUCCESS),
                        messagebox.showinfo("Linked!", f"Tool linked to Discord!\nLevel: {data.get('subscription_name', 'N/A')}")
                    ))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Failed", data.get("message", "Unknown error")))
            except requests.exceptions.ConnectionError:
                self.root.after(0, lambda: messagebox.showerror("Error", "Cannot reach bot server"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        threading.Thread(target=do_claim, daemon=True).start()

    def _test_webhook(self):
        url = self.webhook_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Enter a webhook URL first.")
            return
        self.webhook_url = url
        try:
            r = requests.post(url, json={"content": "✅ Webhook test from UMAX Manager v8.2"}, timeout=10)
            if r.status_code in (200, 204):
                self.webhook_status_lbl.config(text="Verified", fg=SUCCESS)
                messagebox.showinfo("Success", "Webhook test message sent!")
                self.log("Webhook test successful", "success")
            else:
                self.webhook_status_lbl.config(text=f"Failed (HTTP {r.status_code})", fg=ERROR)
                messagebox.showerror("Error", f"Webhook returned status {r.status_code}")
        except Exception as e:
            self.webhook_status_lbl.config(text="Connection Error", fg=ERROR)
            messagebox.showerror("Error", str(e))

    def _discord_headers(self, token):
        props = base64.b64encode(json.dumps({"os":"Windows","browser":"Chrome","device":"","system_locale":"en-US","browser_user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36","browser_version":"125.0.0.0","os_version":"10","referrer":"","referring_domain":"","referrer_current":"","referring_domain_current":"","release_channel":"stable","client_build_number":315589,"client_event_source":None}).encode()).decode()
        return {"Authorization": token, "Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36", "x-super-properties": props, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9", "Origin": "https://discord.com", "Referer": "https://discord.com/channels/@me", "Sec-Ch-Ua": '"Not/A)Brand";v="99", "Google Chrome";v="125", "Chromium";v="125"', "Sec-Ch-Ua-Mobile": "?0", "Sec-Ch-Ua-Platform": '"Windows"'}

    def handle_request(self, method, url, token, json_data=None):
        headers = self._discord_headers(token)
        proxy = self.get_proxy()
        try:
            if method.upper() == "PATCH": r = requests.patch(url, headers=headers, json=json_data, proxies=proxy, timeout=10)
            elif method.upper() == "POST": r = requests.post(url, headers=headers, json=json_data, proxies=proxy, timeout=10)
            elif method.upper() == "GET": r = requests.get(url, headers=headers, proxies=proxy, timeout=10)
            elif method.upper() == "DELETE": r = requests.delete(url, headers=headers, proxies=proxy, timeout=10)
            if r.status_code in (400, 403) and ("captcha" in r.text.lower() or "required" in r.text.lower()):
                self.log(f"⚠️ CAPTCHA DETECTED — action blocked", "error"); return {"error": "captcha_detected", "text": r.text[:200]}
            return r
        except Exception as e: return {"error": "request_failed", "details": str(e)}

def start_app(root):
    for widget in root.winfo_children(): widget.destroy()
    TitanManagerV8_2(root)

def show_login(root):
    for widget in root.winfo_children(): widget.destroy()
    keyauth_app.user_data = None
    LoginPanel(root, lambda: start_app(root))
