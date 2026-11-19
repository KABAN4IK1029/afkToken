# -*- coding: utf-8 -*-
"""Afk token - AFK-бот для Fortnite с системой ключей. Создатель: @kk4ose"""
import json
import os
import queue
import sys
import threading
import time
import webbrowser
from datetime import datetime, timezone

if sys.stdout is None:  # запуск без консоли (.exe)
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = sys.stdout

import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

import bot_core
import license_client as lic

APP_NAME = "Afk token"
# ВЕРСИЯ ПРОГРАММЫ. При каждом новом релизе на GitHub увеличивай её
# и ставь такую же версию при публикации в админке (например 1.3)
APP_VERSION = "1.7.6"
BETA = False  # релизная сборка
lic.APP_VERSION = APP_VERSION  # версия уходит на сервер ключей (видна в админке)
TG_NICK = "@kk4ose"
STARVELL_URL = "https://starvell.com/offers/0fc3f238-0ce6-4a13-98e8-262b6ad640c9"
try:
    from edition import FREE_EDITION  # True = бесплатная версия (2 функции + VIP по ключу)
except Exception:
    FREE_EDITION = False

# ---------- цвета: сакура + немного фиолетового ----------
BG = "#16111d"
SIDEBAR = "#1d1626"
CARD = "#251c31"
CARD2 = "#30253f"
BORDER = "#3d2e52"
ACCENT = "#f29cc4"      # сакура
ACCENT_H = "#e97fb0"
ACCENT_D = "#7d55b5"    # фиолетовый
BTN_TXT = "#2a1424"     # текст на розовых кнопках
LINK_H = "#ffc4dd"
TEXT = "#f6edf6"
MUTED = "#ab9bbb"
GREEN = "#4ade80"
RED = "#f87171"
YELLOW = "#fbbf24"
FONT = "Segoe UI"  # стандартный шрифт Windows: нормальная кириллица, читается легко
GOLD = "#f2c14e"
ULTRA = "#7dd3fc"   # цвет Ultimate
PREM = ("premium", "ultimate")   # уровни, которым открыты Premium-функции

# темы оформления (Premium): название, акцент, акцент-hover, второй цвет, текст на кнопках
THEMES = {
    "sakura": ("Сакура", "#f29cc4", "#e97fb0", "#7d55b5", "#2a1424"),
    "neon": ("Неон", "#4de1ff", "#2cc7ea", "#2b5fa8", "#06212b"),
    "lava": ("Лава", "#ff8a4c", "#f26d2a", "#a8402b", "#2b1206"),
    "mint": ("Мята", "#5ee6a8", "#3fd391", "#2f8a68", "#062b1b"),
    "gold": ("Золото", "#f2c14e", "#e6ac22", "#9a6b16", "#2b1f06"),
}


# кнопки-пульт в Telegram (Premium)
TG_BUTTONS = {"📊 Статус": "/status", "🖥 Скрин": "/screen", "▶ Старт": "/start", "⏹ Стоп": "/stop",
              "⏸ Пауза": "/pause", "📦 Сундуки вкл/выкл": "/chests", "🔄 Перезапуск игры": "/restart",
              "🎯 Цель": "/goal", "🌙 Выкл ПК через 1 ч": "/off60", "❌ Отменить выключение": "/offcancel"}
TG_MENU_ROWS = [["📊 Статус", "🖥 Скрин"], ["▶ Старт", "⏸ Пауза", "⏹ Стоп"],
                ["📦 Сундуки вкл/выкл", "🔄 Перезапуск игры"], ["🎯 Цель"],
                ["🌙 Выкл ПК через 1 ч", "❌ Отменить выключение"]]

VIP_LIST = ["Выход в лобби и новые катки всю ночь", "«Играть снова» без лишнего лобби",
            "Скип наград и окон", "Перезапуск игры при вылетах", "Анти-AFK, чтобы не кикнуло",
            "Сундуки: бегает и открывает сам", "Награды и отчёты в Telegram + команды",
            "Экономия: гасит монитор, режет FPS"]
PREMIUM_LIST = [("📱", "Пульт в Telegram", "Кнопки: старт/стоп, скрин, сундуки, перезапуск игры, выключить ПК, авто-скрины"),
                ("🎯", "Фарм под цель", "Ставишь цель (катки, награды, сундуки или Пиратский токен), бот фармит до неё и сам выключается"),
                ("📊", "Статистика и графики", "Катки, награды и сундуки по дням, график за неделю, отчёт-картинка в Telegram"),
                ("🗓", "Расписание", "Например с 23:00 до 07:00 или пока ты на парах. Бот сам включится и выключится"),
                ("🪂", "Точка высадки", "Прыгает в начале, середине или в конце маршрута. В конце меньше людей и больше лута"),
                ("🌙", "Ночной режим 2.0", "Минимальная графика на время фарма (потом вернёт), ждёт при пропаже интернета"),
                ("💾", "Свои профили", "Сохраняй свои наборы настроек и переключай в 1 клик"),
                ("🛡", "Анти-кик «как человек»", "Стрейфы, прыжки, присед и повороты вместо однообразного W"),
                ("🎨", "Темы и значок ♛", "5 тем оформления и золотой ник со значком ♛ в общем чате"),
                ("🚀", "Приоритет", "Поддержка вне очереди и новые функции первыми")]


def apply_theme(name):
    global ACCENT, ACCENT_H, ACCENT_D, BTN_TXT
    ACCENT, ACCENT_H, ACCENT_D, BTN_TXT = (THEMES.get(name) or THEMES["sakura"])[1:]

SETTINGS_FILE = os.path.join(lic.app_dir(), "settings.json")
DAILY_FILE = os.path.join(lic.app_dir(), "daily_stats.json")
LOG_DIR = os.path.join(lic.app_dir(), "logs")
ASSETS = os.path.join(getattr(sys, "_MEIPASS", lic.app_dir()), "assets")
_img_cache = {}


def asset_img(name, size):
    """Картинка из папки assets (CTkImage) или None, если её нет."""
    key = (name, size)
    if key in _img_cache:
        return _img_cache[key]
    try:
        from PIL import Image
        im = Image.open(os.path.join(ASSETS, name))
        _img_cache[key] = ctk.CTkImage(light_image=im, dark_image=im, size=size)
    except Exception:
        _img_cache[key] = None
    return _img_cache[key]


def F(size=13, bold=False):
    return ctk.CTkFont(family=FONT, size=size, weight="bold" if bold else "normal")


def load_settings():
    s = dict(bot_core.DEFAULTS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            s.update({k: v for k, v in json.load(f).items() if k in s})
    except Exception:
        pass
    return s


def save_settings(s):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def ver_tuple(v):
    import re as _re
    return tuple(int(x) for x in _re.findall(r"\d+", v or "")[:4]) or (0,)


def check_update():
    """Последний релиз с сервера: (версия, текст, ссылка на zip) или None."""
    rel = lic.latest_release()
    if rel and ver_tuple(rel.get("version")) > ver_tuple(APP_VERSION):
        return rel["version"], rel.get("notes") or "", rel.get("file_url") or ""
    return None


# ---------- автообновление ----------
UPDATER_PY = r"""
import ctypes, os, shutil, subprocess, sys, time, traceback
pid, src, dst, tmp = int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
log = os.path.join(dst, "logs", "update.log")

def w(m):
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + m + "\n")
    except Exception:
        pass

try:
    w("update start: " + src + " -> " + dst)
    h = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if h:
        ctypes.windll.kernel32.WaitForSingleObject(h, 60000)
        ctypes.windll.kernel32.CloseHandle(h)
    time.sleep(1.5)
    for attempt in range(15):
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True)
            break
        except Exception as e:
            w("copy retry %d: %s" % (attempt, e))
            time.sleep(1)
    else:
        raise RuntimeError("files are busy, copy failed")
    w("files copied")
    bat = os.path.join(dst, "start.bat")
    if os.path.exists(bat):
        os.startfile(bat)
    else:
        subprocess.Popen([sys.executable, os.path.join(dst, "afk_token.py")], cwd=dst)
    w("restarted")
except Exception:
    w("ERROR " + traceback.format_exc())
finally:
    shutil.rmtree(os.path.join(tmp, "new"), ignore_errors=True)
"""

# ---------- обновление exe-сборки (без Python на машине покупателя) ----------
# exe не может перезаписать сам себя на ходу, поэтому отдельный .bat ждёт закрытия
# программы, копирует новые файлы поверх папки и запускает AfkToken.exe снова.
UPDATER_BAT = r"""@echo off
rem Afk token exe-update.  %1=PID  %2=SRC(новые файлы)  %3=DST(папка программы)
setlocal
set "PID=%~1"
set "SRC=%~2"
set "DST=%~3"
if not exist "%DST%\logs" mkdir "%DST%\logs"
set "LOG=%DST%\logs\update.log"
>>"%LOG%" echo [%date% %time%] exe-update: ждём закрытия PID %PID%
:wait
tasklist /fi "PID eq %PID%" 2>nul | findstr /i " %PID% " >nul && (ping -n 2 127.0.0.1 >nul & goto wait)
ping -n 3 127.0.0.1 >nul
robocopy "%SRC%" "%DST%" /E /IS /IT /R:20 /W:1 >>"%LOG%" 2>&1
>>"%LOG%" echo [%date% %time%] robocopy завершился с кодом %errorlevel%
start "" "%DST%\AfkToken.exe"
>>"%LOG%" echo [%date% %time%] перезапущено
endlocal
"""

# эти файлы у пользователя остаются свои
KEEP_FILES = {"settings.json", "license.json", ".installed", "edition.py", "daily_stats.json"}
KEEP_DIRS = {"logs", "__pycache__", "models"}


def download_update(url, dest, progress):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "AfkToken-updater"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(128 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            progress(done, total)


def prepare_update(zip_path, tmp, app=None):
    """Распаковывает архив и возвращает папку с новыми файлами (без личных файлов пользователя)."""
    import shutil
    import zipfile
    app = app or lic.app_dir()
    out = os.path.join(tmp, "new")
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(out)
    root = out
    items = [i for i in os.listdir(out) if not i.startswith("__MACOSX")]
    if len(items) == 1 and os.path.isdir(os.path.join(out, items[0])):
        root = os.path.join(out, items[0])
    is_exe = getattr(sys, "frozen", False)
    marker = "AfkToken.exe" if is_exe else "afk_token.py"
    if not os.path.exists(os.path.join(root, marker)):
        raise RuntimeError(f"в архиве нет {marker}, это архив другой сборки "
                           f"({'нужен exe-архив' if is_exe else 'нужен архив с исходником'})")
    for name in list(os.listdir(root)):
        p = os.path.join(root, name)
        if name in KEEP_FILES:
            os.remove(p)
        elif name in KEEP_DIRS and os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
    # пустые шаблоны не должны затирать рабочие данные сервера
    for name in ("server_config.py", "license_client.py"):
        p = os.path.join(root, name)
        if name == "server_config.py" and os.path.exists(p):
            txt = open(p, encoding="utf-8", errors="ignore").read()
            if "XXXXXXXX" in txt and os.path.exists(os.path.join(app, name)):
                os.remove(p)
    # изменились библиотеки -> start.bat поставит их заново
    try:
        new_req = open(os.path.join(root, "requirements.txt"), encoding="utf-8").read()
        old_req = open(os.path.join(app, "requirements.txt"), encoding="utf-8").read()
        if new_req.strip() != old_req.strip():
            os.remove(os.path.join(app, ".installed"))
    except Exception:
        pass
    return root


def launch_updater(src, tmp):
    """Запускает маленький установщик, который дождётся закрытия программы, заменит файлы
    и запустит её снова. В exe-сборке это .bat (Python на машине не нужен), в исходнике — Python.
    Лог: logs/update.log"""
    import subprocess
    app = lic.app_dir()
    DETACHED = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    if getattr(sys, "frozen", False):
        bat = os.path.join(tmp, "afk_update.bat")
        with open(bat, "w", encoding="utf-8") as f:
            f.write(UPDATER_BAT)
        subprocess.Popen(["cmd", "/c", bat, str(os.getpid()), src, app],
                         cwd=tmp, close_fds=True, creationflags=DETACHED)
        return
    script = os.path.join(tmp, "afk_updater.py")
    with open(script, "w", encoding="utf-8") as f:
        f.write(UPDATER_PY)
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable
    subprocess.Popen([pyw, script, str(os.getpid()), src, app, tmp], cwd=tmp, close_fds=True,
                     creationflags=DETACHED)


def can_auto_update():
    """Автообновление: exe-сборка заменяется через .bat, исходник — через start.bat."""
    if getattr(sys, "frozen", False):
        return True
    return os.path.exists(os.path.join(lic.app_dir(), "start.bat"))


def fmt_time(iso):
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone().strftime("%d.%m.%y %H:%M")
    except Exception:
        return iso[:16]


def minutes_ago(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 60
    except Exception:
        return 1e9


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title(APP_NAME + (" Free" if FREE_EDITION else "") + (f" {APP_VERSION} β" if BETA else ""))
        self.geometry("1180x740")
        self.minsize(1000, 640)
        self.configure(fg_color=BG)
        try:
            self.iconbitmap(os.path.join(ASSETS, "icon.ico"))
        except Exception:
            pass

        self.q = queue.Queue()
        self.settings = load_settings()
        self.bot = bot_core.AfkBot(self.settings, log=self._bot_log,
                                   on_state=lambda st: self.q.put(("state", st)))
        self.is_admin = False
        self.key = None
        self.vip = False
        self.tier = "free"
        self.vip_until = None
        self.shop = dict(lic.SHOP_DEFAULTS)
        self._shop_loaded = False
        self._sched_started = False
        self._sched_active = False
        self._gate_last_ok = 0.0
        self._gate_paused = False
        self._gate_emergency = False
        try:
            with open(DAILY_FILE, encoding="utf-8") as f:
                self.daily = json.load(f)
        except Exception:
            self.daily = {}
        self._last_stats = None
        self._daily_saved = 0.0
        self.update_info = None
        self.tray = None
        self.start_hidden = "--tray" in sys.argv
        self._tg_poll_started = False
        self._tg_poll_pause = False
        self.bot_state = "stopped"
        self.admin_rows = []
        self.user_rows = []
        self.cur_page = None
        self.chat_msgs = []        # последние сообщения чата
        self.chat_last_id = 0
        self.chat_nick = None
        self.chat_muted = False
        self.chat_unread = 0
        self.chat_online = 0
        self._chat_busy = False
        self._nick_editing = False
        self._chat_loop_started = False
        self._ping_started = False
        os.makedirs(LOG_DIR, exist_ok=True)

        self.root_frame = None
        self.bind_all("<Control-KeyPress>", self._ctrl_keys, add="+")
        self.bind_all("<Button-3>", self._entry_menu, add="+")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self._poll)
        threading.Thread(target=bot_core.fix_ssl, daemon=True).start()
        self.start_flow()

    # ================= служебное =================
    def _ctrl_keys(self, e):
        """Ctrl+V / C / X / A на русской раскладке (tkinter понимает их только на английской)."""
        if (e.keysym or "").lower() in ("v", "c", "x", "a"):
            return None
        w = e.widget
        ev = {86: "<<Paste>>", 67: "<<Copy>>", 88: "<<Cut>>"}.get(e.keycode)
        try:
            if ev:
                w.event_generate(ev)
                return "break"
            if e.keycode == 65:
                if w.winfo_class() == "Entry":
                    w.select_range(0, "end")
                    w.icursor("end")
                elif w.winfo_class() == "Text":
                    w.tag_add("sel", "1.0", "end")
                return "break"
        except Exception:
            pass
        return None

    def _entry_menu(self, e):
        """Правый клик по полю ввода: Вставить / Копировать / Вырезать / Выделить всё."""
        w = e.widget
        try:
            if w.winfo_class() != "Entry":
                return
        except Exception:
            return
        m = tk.Menu(self, tearoff=0, bg=CARD2, fg=TEXT, activebackground=ACCENT_D, activeforeground="#ffffff", bd=0)
        m.add_command(label="Вставить", command=lambda: w.event_generate("<<Paste>>"))
        m.add_command(label="Копировать", command=lambda: w.event_generate("<<Copy>>"))
        m.add_command(label="Вырезать", command=lambda: w.event_generate("<<Cut>>"))
        m.add_separator()
        m.add_command(label="Выделить всё", command=lambda: (w.select_range(0, "end"), w.icursor("end")))
        try:
            w.focus_set()
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def bg(self, func, callback=None, *args):
        """Выполнить func(*args) в фоне, потом callback(result) в окне."""
        def worker():
            try:
                res = func(*args)
            except Exception as e:
                res = e
            if callback:
                self.q.put(("cb", callback, res))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "cb":
                    item[1](item[2])
                elif item[0] == "log":
                    self._append_log(item[1])
                elif item[0] == "state":
                    self._set_bot_state(item[1])
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _bot_log(self, msg):
        line = time.strftime("[%H:%M:%S] ") + msg
        self.q.put(("log", line))
        try:
            path = os.path.join(LOG_DIR, "afk_token.log")
            self._log_n = getattr(self, "_log_n", 0) + 1
            if self._log_n % 200 == 1 and os.path.exists(path) and os.path.getsize(path) > 5 * 1024 * 1024:
                os.replace(path, path + ".old")     # держим максимум ~10 МБ журналов
            with open(path, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d ") + line + "\n")
        except Exception:
            pass

    def clear(self):
        if self.root_frame is not None:
            self.root_frame.destroy()
        self.root_frame = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.root_frame.pack(fill="both", expand=True)
        return self.root_frame

    def copy(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    @staticmethod
    def link(parent, text, url, size=13):
        lb = ctk.CTkLabel(parent, text=text, text_color=ACCENT, font=F(size, True),
                          cursor="hand2")
        lb.bind("<Button-1>", lambda e: webbrowser.open(url))
        lb.bind("<Enter>", lambda e: lb.configure(text_color=LINK_H))
        lb.bind("<Leave>", lambda e: lb.configure(text_color=ACCENT))
        return lb

    def logo(self, parent, sub=None):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(anchor="w")
        av = asset_img("avatar.png", (38, 38))
        if av:
            badge = ctk.CTkLabel(row, text="", image=av, width=38, height=38)
        else:
            badge = ctk.CTkLabel(row, text="A", width=34, height=34, corner_radius=10,
                                 fg_color=ACCENT, text_color=BTN_TXT, font=F(18, True))
        badge.pack(side="left")
        ctk.CTkLabel(row, text="  " + APP_NAME, text_color=TEXT, font=F(22, True)).pack(side="left")
        if sub:
            ctk.CTkLabel(box, text=sub, text_color=MUTED, font=F(12)).pack(anchor="w", padx=(50, 0))
        return box

    # ================= запуск / активация =================
    def start_flow(self):
        saved = lic.load_saved()
        if saved and saved.get("key") and lic.configured():
            f = self.clear()
            ctk.CTkLabel(f, text="Проверка ключа...", text_color=MUTED, font=F(15)).place(
                relx=0.5, rely=0.5, anchor="center")
            self.bg(lic.activate, lambda r: self._after_check(saved["key"], r), saved["key"])
        elif FREE_EDITION:
            self.show_main()
        else:
            self.show_activation()

    def _after_check(self, key, res):
        if isinstance(res, Exception):
            res = {"ok": False, "error": str(res)}
        if res.get("ok"):
            self.key = key
            self.is_admin = res.get("admin", False)
            self.vip_until = res.get("expires_at")
            self.show_main(offline=res.get("offline", False))
        elif FREE_EDITION:
            self.key = None
            self.vip_until = None
            self.show_main()
            if res.get("expired"):
                self.after(800, lambda: self.toast("VIP закончился, теперь у тебя бесплатная версия", YELLOW))
        else:
            self.show_activation(res.get("error", ""))

    def show_activation(self, error=""):
        f = self.clear()
        card = ctk.CTkFrame(f, fg_color=SIDEBAR, corner_radius=14, width=470)
        card.place(relx=0.5, rely=0.5, anchor="center")
        ban = asset_img("banner_wide.png", (470, 130))
        if ban:
            ctk.CTkLabel(card, text="", image=ban).pack()
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=34, pady=(16 if ban else 30, 30))

        self.logo(inner, "Активация Afk token").pack(anchor="w", pady=(0, 22))

        ctk.CTkLabel(inner, text="Код вашего компьютера", text_color=MUTED, font=F(12)).pack(anchor="w")
        hw = lic.get_hwid()
        hwbox = ctk.CTkFrame(inner, fg_color=CARD, corner_radius=8)
        hwbox.pack(fill="x", pady=(4, 16))
        ctk.CTkLabel(hwbox, text=hw, text_color=TEXT, font=F(20, True)).pack(side="left", padx=16, pady=14)
        cb = ctk.CTkButton(hwbox, text="Скопировать", width=100, height=30, fg_color=CARD2,
                           hover_color=BORDER, text_color=TEXT, font=F(12))
        cb.configure(command=lambda: (self.copy(hw), cb.configure(text="Скопировано")))
        cb.pack(side="right", padx=12)

        ctk.CTkLabel(inner, text="Ключ", text_color=MUTED, font=F(12)).pack(anchor="w")
        entry = ctk.CTkEntry(inner, height=44, width=400, fg_color=CARD, border_color=ACCENT,
                             text_color=TEXT, font=F(15), placeholder_text="AFK-XXXX-XXXX-XXXX-XXXX")
        entry.pack(fill="x", pady=(4, 6))
        err = ctk.CTkLabel(inner, text=error, text_color=RED, font=F(12), wraplength=400, justify="left")
        err.pack(anchor="w", pady=(0, 10))
        if not lic.configured():
            err.configure(text="Сервер ключей не настроен: впиши SUPABASE_URL и SUPABASE_KEY "
                               "в license_client.py (см. НАСТРОЙКА.txt)")

        btn = ctk.CTkButton(inner, text="Активировать", height=40, fg_color=ACCENT,
                            hover_color=ACCENT_H, text_color=BTN_TXT, font=F(14, True))

        def do_activate(*_):
            key = entry.get().strip()
            if not key:
                err.configure(text="Введи ключ")
                return
            btn.configure(state="disabled", text="Проверяю...")
            err.configure(text="")

            def done(res):
                if isinstance(res, Exception):
                    res = {"ok": False, "error": str(res)}
                if res.get("ok"):
                    self.key = key.upper()
                    self.is_admin = res.get("admin", False)
                    self.vip_until = res.get("expires_at")
                    self.show_main(offline=res.get("offline", False))
                else:
                    btn.configure(state="normal", text="Активировать")
                    err.configure(text=res.get("error", "Ошибка"))
            self.bg(lic.activate, done, key)

        btn.configure(command=do_activate)
        entry.bind("<Return>", do_activate)
        btn.pack(fill="x")

        info = ctk.CTkFrame(inner, fg_color="#1d2a24", corner_radius=8)
        info.pack(fill="x", pady=(18, 0))
        ctk.CTkLabel(info, text="Ключ навсегда, без подписки", text_color=GREEN,
                     font=F(13, True)).pack(anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(info, text="Один ключ на один компьютер. Все функции открыты.",
                     text_color=TEXT, font=F(12)).pack(anchor="w", padx=16, pady=(0, 12))

        self.link(inner, f"Нет ключа? Пиши {TG_NICK}", lic.TG_URL).pack(anchor="w", pady=(16, 2))
        ctk.CTkLabel(inner, text="Откроется Telegram. Скинь код компьютера, и тебе пришлют ключ.",
                     text_color=MUTED, font=F(11)).pack(anchor="w")

    # ================= главное окно =================
    def show_main(self, offline=False):
        # уровень только из ответа сервера (lic.last_tier), файлу лицензии не доверяем
        srv = lic.last_tier if self.key else "free"
        if not self.key or srv == "free":
            self.tier = "free"
        elif self.is_admin or srv == "ultimate":
            self.tier = "ultimate"
        elif srv in ("premium", "upgrade"):
            self.tier = "premium"
        else:
            self.tier = "vip"
        self.vip = self.tier != "free"
        self.bot.vip = self.vip
        self.bot.tier = self.tier
        apply_theme(self.settings.get("theme", "sakura") if self.tier in PREM else "sakura")
        f = self.clear()
        self.pages = {}
        self.nav_buttons = {}

        side = ctk.CTkFrame(f, fg_color=SIDEBAR, corner_radius=0, width=240)
        self.side_panel = side
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        ban = asset_img("banner_side.png", (240, 120))
        if ban:
            ctk.CTkLabel(side, text="", image=ban).pack(fill="x")
        self.logo(side).pack(anchor="w", padx=18, pady=(12 if ban else 24, 2))
        if self.tier in PREM:
            sub = (("Ultimate ⚡" if self.tier == "ultimate" else "Premium ♛") + " · навсегда"
                   + ("  ·  админ" if self.is_admin else ""))
        elif self.vip and self.vip_until:
            sub = f"VIP до {fmt_time(self.vip_until)[:8]}"
        elif self.vip:
            sub = "VIP · навсегда ∞"
        else:
            sub = "Бесплатная версия"
        ctk.CTkLabel(side, text=sub, text_color=(GOLD if self.tier in PREM else ACCENT) if self.vip else MUTED,
                     font=F(12, self.vip)).pack(anchor="w", padx=68, pady=(0, 12 if self.tier not in PREM else 16))
        self.side_shop_btn = None
        if self.tier != "ultimate":
            self.side_shop_btn = ctk.CTkButton(side, text=self._side_shop_text(), height=38, corner_radius=10,
                                               fg_color=GOLD if self.tier == "vip" and not self.vip_until else ACCENT,
                                               hover_color=ACCENT_H, text_color=BTN_TXT, font=F(13, True),
                                               command=lambda: self.show_page("shop"))
            self.side_shop_btn.pack(fill="x", padx=12, pady=(0, 14))

        nav = [("functions", "▶   Функции бота"),
               ("shop", "♛   Premium" if self.tier in PREM else "💎   Магазин"),
               ("chat", "✉   Чат"), ("referral", "♥   Рефералы"),
               ("faq", "☰   FAQ"), ("creator", "✦   Создатель")]
        if self.is_admin:
            nav.append(("admin", "⚙   Админ"))
        for name, title in nav:
            b = ctk.CTkButton(side, text=title, anchor="w", height=40, corner_radius=8,
                              fg_color="transparent", hover_color=CARD, text_color=TEXT,
                              font=F(14), command=lambda n=name: self.show_page(n))
            b.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[name] = b

        # карточка статуса внизу
        st = ctk.CTkFrame(side, fg_color=CARD, corner_radius=10)
        st.pack(side="bottom", fill="x", padx=12, pady=12)
        self.st_title = ctk.CTkLabel(st, text="●  Бот остановлен", text_color=TEXT, font=F(13, True))
        self.st_title.pack(anchor="w", padx=14, pady=(12, 0))
        self.st_sub = ctk.CTkLabel(st, text="Нажми «Запустить» и отходи от ПК",
                                   text_color=MUTED, font=F(11), wraplength=190, justify="left")
        self.st_sub.pack(anchor="w", padx=14, pady=(2, 8))
        row = ctk.CTkFrame(st, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))
        self.side_start = ctk.CTkButton(row, text="Запустить", width=95, height=32, fg_color=ACCENT,
                                        hover_color=ACCENT_H, text_color=BTN_TXT, font=F(12, True),
                                        command=self.start_bot)
        self.side_start.pack(side="left")
        self.side_stop = ctk.CTkButton(row, text="Стоп", width=80, height=32, fg_color=CARD2,
                                       hover_color=BORDER, text_color=TEXT, font=F(12),
                                       command=self.stop_bot)
        self.side_stop.pack(side="right")

        if self.vip:
            out = ctk.CTkLabel(side, text="Сменить ключ", text_color=MUTED, font=F(11), cursor="hand2")
            out.bind("<Button-1>", lambda e: self.change_key())
            out.pack(side="bottom", pady=(0, 2))
        if offline:
            ctk.CTkLabel(side, text="Нет связи с сервером: только бесплатные функции", text_color=YELLOW,
                         font=F(11)).pack(side="bottom")

        self.content = ctk.CTkFrame(f, fg_color=BG, corner_radius=0)
        self.content.pack(side="left", fill="both", expand=True)

        self.build_functions()
        self.build_shop()
        self.build_chat()
        self.build_referral()
        self.build_faq()
        self.build_creator()
        if self.is_admin:
            self.build_admin()
        self.show_page("functions")
        self._set_bot_state("running" if self.bot.running else "stopped")
        self._tick_stats()
        if self.update_info:
            self._show_update_badge()
        elif not getattr(self, "_update_checked", False):
            self._update_checked = True
            self.after(2500, lambda: self.bg(check_update, self._on_update))
        if getattr(self, "_hb_id", None):
            self.after_cancel(self._hb_id)
            self._hb_id = None
        if self.vip:
            self._hb_id = self.after(5 * 60 * 1000, self._heartbeat)
        self._init_tray()
        self._start_tg_poll()
        self._start_user_ping()
        self._start_chat_loop()
        self._chat_nav_badge()
        if not self._shop_loaded:
            self._shop_loaded = True
            self.bg(lic.get_config, self._on_shop_cfg)
        if not self._sched_started:
            self._sched_started = True
            self.after(10000, self._sched_tick)
            threading.Thread(target=self._shot_loop, daemon=True).start()
        if self.tier == "free" and not self.settings.get("shop_seen"):
            self.settings["shop_seen"] = True
            save_settings(self.settings)
            self.after(50, lambda: self.show_page("shop"))
        elif (self.tier == "vip" and not self.vip_until and not self.settings.get("premium_offer_seen")
              and not self.start_hidden):
            self.after(1500, self.open_premium_offer)
        if self.start_hidden:
            self.start_hidden = False
            self.after(200, self.withdraw)
        if self.settings.get("autorun_bot") and not self.bot.running and not getattr(self, "_autoran", False):
            self._autoran = True
            self.after(3000, self.start_bot)

    def show_page(self, name):
        self.cur_page = name
        for n, p in self.pages.items():
            p.pack_forget()
        self.pages[name].pack(fill="both", expand=True, padx=28, pady=22)
        for n, b in self.nav_buttons.items():
            b.configure(fg_color=CARD2 if n == name else "transparent",
                        text_color=ACCENT if n == name else TEXT)
        if name == "admin" and not self.admin_rows:
            self.admin_refresh()
        if name == "referral":
            self.ref_refresh()
        if name == "chat":
            self.chat_unread = 0
            self._chat_nav_badge()
            self._chat_render(scroll=True)
            self._chat_tick(force=True)
            try:
                self.chat_entry.focus_set()
            except Exception:
                pass

    def page_header(self, page, title, sub=""):
        h = ctk.CTkFrame(page, fg_color="transparent")
        h.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(h, text="❀ ", text_color=ACCENT, font=F(20)).pack(side="left")
        ctk.CTkLabel(h, text=title, text_color=TEXT, font=F(24, True)).pack(side="left")
        if sub:
            ctk.CTkLabel(h, text="   " + sub, text_color=MUTED, font=F(12)).pack(side="left", pady=(8, 0))
        return h

    def open_vip(self):
        if getattr(self, "_vip_win", None) is not None:
            try:
                self._vip_win.focus()
                return
            except Exception:
                pass
        win = ctk.CTkToplevel(self)
        self._vip_win = win
        win.title("Afk token VIP")
        win.geometry("480x600")
        win.resizable(False, False)
        win.configure(fg_color=SIDEBAR)
        win.transient(self)
        win.after(150, win.grab_set)

        def close():
            self._vip_win = None
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", close)

        ban = asset_img("banner_wide.png", (470, 130))
        if ban:
            ctk.CTkLabel(win, text="", image=ban).pack(pady=(5, 0))
        inner = ctk.CTkFrame(win, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=30, pady=16)
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(anchor="w")
        ctk.CTkLabel(row, text="Afk token ", text_color=TEXT, font=F(22, True)).pack(side="left")
        ctk.CTkLabel(row, text=" VIP ", fg_color=ACCENT, text_color=BTN_TXT, corner_radius=8,
                     font=F(16, True)).pack(side="left")
        ctk.CTkLabel(inner, text="Выход в лобби и новые катки, «Играть снова», скип наград, перезапуск "
                                 "игры, анти-AFK, сундуки, отчёты в Telegram. Ключ навсегда.",
                     text_color=MUTED, font=F(12), wraplength=410, justify="left").pack(anchor="w", pady=(6, 12))

        ctk.CTkLabel(inner, text="Код вашего компьютера", text_color=MUTED, font=F(12)).pack(anchor="w")
        hw = lic.get_hwid()
        hwbox = ctk.CTkFrame(inner, fg_color=CARD, corner_radius=8)
        hwbox.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(hwbox, text=hw, text_color=TEXT, font=F(17, True)).pack(side="left", padx=14, pady=10)
        cb = ctk.CTkButton(hwbox, text="Скопировать", width=96, height=28, fg_color=CARD2,
                           hover_color=BORDER, text_color=TEXT, font=F(12))
        cb.configure(command=lambda: (self.copy(hw), cb.configure(text="Скопировано")))
        cb.pack(side="right", padx=10)

        entry = ctk.CTkEntry(inner, height=42, fg_color=CARD, border_color=ACCENT, text_color=TEXT,
                             font=F(15), placeholder_text="AFK-XXXX-XXXX-XXXX-XXXX")
        entry.pack(fill="x")
        ref_e = ctk.CTkEntry(inner, height=34, fg_color=CARD, border_color=BORDER, text_color=TEXT,
                             font=F(13), placeholder_text="Реф-код друга (если есть), например REF-1A2B3C")
        ref_e.pack(fill="x", pady=(8, 0))
        err = ctk.CTkLabel(inner, text="" if lic.configured() else "Сервер ключей не настроен",
                           text_color=RED, font=F(12), wraplength=410, justify="left")
        err.pack(anchor="w", pady=(4, 6))
        btn = ctk.CTkButton(inner, text="Активировать VIP", height=40, fg_color=ACCENT,
                            hover_color=ACCENT_H, text_color=BTN_TXT, font=F(14, True))

        def do(*_):
            key = entry.get().strip()
            if not key:
                err.configure(text="Введи ключ")
                return
            btn.configure(state="disabled", text="Проверяю...")
            err.configure(text="")

            def done(res):
                if isinstance(res, Exception):
                    res = {"ok": False, "error": str(res)}
                if res.get("ok"):
                    self.key = key.upper()
                    self.is_admin = res.get("admin", False)
                    self.vip_until = res.get("expires_at")
                    ref = ref_e.get().strip()
                    close()
                    was_running = self.bot.running
                    self.show_main(offline=res.get("offline", False))
                    self.toast("🌸 VIP активирован, все функции открыты!", GREEN)
                    if was_running:
                        self._bot_log("VIP активирован, все функции включены")
                    if ref:
                        def ref_done(r):
                            if isinstance(r, Exception):
                                self.toast(f"Реф-код: {r}", RED)
                            elif r and r.get("ok"):
                                self.toast("Реф-код засчитан, другу +7 дней VIP 💜", GREEN)
                            else:
                                self.toast(f"Реф-код: {(r or {}).get('error', 'ошибка')}", YELLOW)
                        self.bg(lic.ref_use, ref_done, ref, self.key)
                else:
                    try:
                        btn.configure(state="normal", text="Активировать VIP")
                        err.configure(text=res.get("error", "Ошибка"))
                    except tk.TclError:
                        pass
            self.bg(lic.activate, done, key)
        btn.configure(command=do)
        entry.bind("<Return>", do)
        btn.pack(fill="x")

        self.link(inner, f"Купить Premium навсегда за {self.shop.get('price_premium', '159')} ₽",
                  self.shop.get("url_premium") or lic.TG_URL).pack(
            anchor="w", pady=(14, 2))
        self.link(inner, f"Есть вопросы? Пиши в Telegram {TG_NICK}", lic.TG_URL, 12).pack(anchor="w")

    # ================= обновления =================
    def _on_update(self, res):
        if not res or isinstance(res, Exception):
            return
        self.update_info = res
        self._show_update_badge()
        ver = res[0]
        if self.settings.get("auto_update", True) and can_auto_update() and not self.bot.running:
            self.show_update_dialog(auto=True)
        elif self.settings.get("skip_version") != ver:
            self.show_update_dialog()

    def _show_update_badge(self):
        side = getattr(self, "side_panel", None)
        if side is None:
            return
        try:
            b = ctk.CTkButton(side, text=f"⬆  Доступна версия {self.update_info[0]}", height=30,
                              corner_radius=8, fg_color=ACCENT_D, hover_color=BORDER, text_color=TEXT,
                              font=F(12, True), command=self.show_update_dialog)
            b.pack(side="bottom", fill="x", padx=12, pady=(0, 6))
        except tk.TclError:
            pass

    def show_update_dialog(self, auto=False):
        if not self.update_info:
            return
        ver, notes, url = self.update_info
        can_auto = can_auto_update() and bool(url)
        win = ctk.CTkToplevel(self)
        win.title("Обновление Afk token")
        win.geometry("480x500")
        win.resizable(False, False)
        win.configure(fg_color=SIDEBAR)
        win.transient(self)
        win.after(150, win.grab_set)
        box = ctk.CTkFrame(win, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=26, pady=22)
        ctk.CTkLabel(box, text="🌸 Доступно обновление!", text_color=ACCENT, font=F(20, True)).pack(anchor="w")
        ctk.CTkLabel(box, text=f"Твоя версия: {APP_VERSION}   →   новая: {ver}", text_color=TEXT,
                     font=F(13)).pack(anchor="w", pady=(4, 10))
        tb = ctk.CTkTextbox(box, height=190, fg_color=CARD, text_color=TEXT, font=F(12), corner_radius=8,
                            wrap="word")
        tb.pack(fill="both", expand=True)
        tb.insert("1.0", notes.strip() or "Исправления и улучшения.")
        tb.configure(state="disabled")
        status = ctk.CTkLabel(box, text="Ключ, настройки и Telegram сохранятся." if can_auto else
                              "Скачай архив, распакуй и замени файлы программы.",
                              text_color=MUTED, font=F(11), wraplength=420, justify="left")
        status.pack(anchor="w", pady=(8, 4))
        bar = ctk.CTkProgressBar(box, progress_color=ACCENT, fg_color=CARD2, height=10)
        bar.set(0)
        auto_var = tk.BooleanVar(value=bool(self.settings.get("auto_update", True)))

        def auto_toggled():
            self.settings["auto_update"] = bool(auto_var.get())
            save_settings(self.settings)
        if can_auto:
            ctk.CTkCheckBox(box, text="Обновлять автоматически", variable=auto_var, command=auto_toggled,
                            fg_color=ACCENT, hover_color=ACCENT_H, border_color=BORDER, text_color=TEXT,
                            font=F(12), checkbox_width=18, checkbox_height=18).pack(anchor="w", pady=(2, 8))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x")

        def set_status(text, color=MUTED):
            try:
                status.configure(text=text, text_color=color)
            except tk.TclError:
                pass

        def set_bar(v):
            try:
                bar.set(v)
            except tk.TclError:
                pass

        def start_update():
            if not can_auto:
                webbrowser.open(url or lic.TG_URL)
                return
            self.bot.stop()
            for b in (b_upd, b_later, b_skip):
                b.configure(state="disabled")
            bar.pack(fill="x", pady=(0, 8), before=row)
            set_status("Скачиваю обновление...")

            def progress(done, total):
                frac = done / total if total else 0
                self.q.put(("cb", lambda _: (set_bar(min(1, frac)), set_status(
                    f"Скачиваю... {done // 1024} КБ" + (f" из {total // 1024} КБ" if total else ""))), None))

            def work():
                import tempfile
                tmp = tempfile.mkdtemp(prefix="afktoken_upd_")
                zp = os.path.join(tmp, "update.zip")
                download_update(url, zp, progress)
                self.q.put(("cb", lambda _: set_status("Распаковываю..."), None))
                return prepare_update(zp, tmp), tmp

            def done(res):
                if isinstance(res, Exception):
                    set_status(f"Не получилось обновить: {res}", RED)
                    for b in (b_upd, b_later, b_skip):
                        b.configure(state="normal")
                    b_upd.configure(text="Скачать вручную", command=lambda: webbrowser.open(url))
                    return
                src, tmp = res
                set_status("Готово! Перезапускаю программу...", GREEN)
                set_bar(1)
                try:
                    launch_updater(src, tmp)
                except Exception as e:
                    set_status(f"Не удалось запустить обновление: {e}", RED)
                    return
                self.after(900, lambda: (self.destroy(), os._exit(0)))
            self.bg(work, done)

        def skip():
            self.settings["skip_version"] = ver
            save_settings(self.settings)
            win.destroy()
        b_upd = ctk.CTkButton(row, text="Обновить сейчас" if can_auto else "Скачать", width=150, height=36,
                              fg_color=ACCENT, hover_color=ACCENT_H, text_color=BTN_TXT, font=F(13, True),
                              command=start_update)
        b_upd.pack(side="left")
        b_later = ctk.CTkButton(row, text="Позже", width=90, height=36, fg_color=CARD2, hover_color=BORDER,
                                text_color=TEXT, font=F(13), command=win.destroy)
        b_later.pack(side="left", padx=8)
        b_skip = ctk.CTkButton(row, text="Пропустить версию", height=36, fg_color="transparent",
                               hover_color=CARD, text_color=MUTED, font=F(12), command=skip)
        b_skip.pack(side="right")
        if auto and can_auto:
            set_status("Автообновление начнётся через 3 секунды...")
            win.after(3000, lambda: str(b_upd.cget("state")) == "normal" and start_update())

    # ---------- админ: выпустить обновление ----------
    def adm_release(self):
        if BETA and not messagebox.askyesno(
                APP_NAME, "Это БЕТА-билд.\n\nОбновление, выпущенное отсюда, уйдёт ВСЕМ покупателям. "
                          "Выпускать релиз лучше из рабочей версии.\n\nВсё равно открыть окно выпуска?"):
            return
        win = ctk.CTkToplevel(self)
        win.title("Выпустить обновление")
        win.geometry("520x560")
        win.configure(fg_color=SIDEBAR)
        win.transient(self)
        win.after(150, win.grab_set)
        box = ctk.CTkFrame(win, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=24, pady=20)
        ctk.CTkLabel(box, text="⬆ Выпустить обновление", text_color=ACCENT, font=F(19, True)).pack(anchor="w")
        ctk.CTkLabel(box, text="1) Supabase → Storage → папка releases → Upload: загрузи zip новой версии.\n"
                               "2) Впиши версию (как APP_VERSION в afk_token.py), имя файла и что нового.\n"
                               "3) Нажми «Опубликовать», и обновление получат все.",
                     text_color=MUTED, font=F(12), wraplength=470, justify="left").pack(anchor="w", pady=(4, 12))

        def field(label, ph, init=""):
            ctk.CTkLabel(box, text=label, text_color=MUTED, font=F(12)).pack(anchor="w")
            e = ctk.CTkEntry(box, height=34, fg_color=CARD, border_color=BORDER, text_color=TEXT, font=F(13),
                             placeholder_text=ph)
            if init:
                e.insert(0, init)
            e.pack(fill="x", pady=(2, 10))
            return e
        e_ver = field("Версия", "1.1")
        e_file = field("Имя файла в Storage (или полная ссылка)", "AfkToken_v1.1.zip")
        ctk.CTkLabel(box, text="Что нового", text_color=MUTED, font=F(12)).pack(anchor="w")
        tb = ctk.CTkTextbox(box, height=150, fg_color=CARD, text_color=TEXT, font=F(12), corner_radius=8)
        tb.pack(fill="both", expand=True, pady=(2, 10))
        msg = ctk.CTkLabel(box, text="", text_color=MUTED, font=F(12), wraplength=470, justify="left")
        msg.pack(anchor="w")

        def publish():
            ver = e_ver.get().strip()
            f = e_file.get().strip()
            if not ver or not f:
                msg.configure(text="Заполни версию и имя файла", text_color=YELLOW)
                return
            url = f if f.startswith("http") else lic.storage_url(f)
            notes = tb.get("1.0", "end").strip()
            msg.configure(text="Проверяю файл и публикую...", text_color=MUTED)

            def work():
                import urllib.request
                req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AfkToken"})
                try:
                    urllib.request.urlopen(req, timeout=15).close()
                except Exception as e:
                    raise RuntimeError(f"файл не открывается по ссылке ({e}). Проверь имя файла "
                                       "и что папка releases публичная (Public bucket)")
                return lic.admin_release(ver, notes, url)

            def done(res):
                if isinstance(res, Exception):
                    msg.configure(text=f"Ошибка: {res}", text_color=RED)
                else:
                    msg.configure(text=f"Версия {ver} опубликована! Пользователи получат её при запуске.",
                                  text_color=GREEN)
            self.bg(work, done)
        ctk.CTkButton(box, text="Опубликовать", height=38, fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=BTN_TXT, font=F(14, True), command=publish).pack(fill="x", pady=(8, 0))

    def change_key(self):
        if messagebox.askyesno(APP_NAME, "Выйти и ввести другой ключ?"):
            self.bot.stop()
            lic.forget()
            self.key = None
            self.is_admin = False
            if FREE_EDITION:
                self.show_main()
            else:
                self.show_activation()

    def _heartbeat(self):
        if not self.key:
            return

        def done(res):
            if isinstance(res, dict) and not res.get("ok"):
                e = res.get("error", "")
                if res.get("expired") or "заблок" in e.lower() or "не найден" in e.lower() \
                        or "другом" in e.lower():
                    self.bot.stop()
                    self.key = None
                    self.vip_until = None
                    self.is_admin = False
                    if FREE_EDITION:
                        self.show_main()
                        self.toast(e, YELLOW)
                    else:
                        self.show_activation(e)
                    return
            self._hb_id = self.after(5 * 60 * 1000, self._heartbeat)
        self._hb_id = None
        self.bg(lic.activate, done, self.key, False)

    # ================= вкладка: функции =================
    def build_functions(self):
        page = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        self.pages["functions"] = page
        h = self.page_header(page, "Функции бота", "Fortnite · Королевская битва · Отряды")
        self.btn_pause = ctk.CTkButton(h, text="Пауза (F9)", width=110, height=36, fg_color=CARD2,
                                       hover_color=BORDER, text_color=TEXT, font=F(13),
                                       command=self.bot.toggle_pause)
        self.btn_pause.pack(side="right", padx=(8, 0))
        self.btn_stop = ctk.CTkButton(h, text="■  Стоп (F10)", width=120, height=36, fg_color=CARD2,
                                      hover_color=BORDER, text_color=TEXT, font=F(13),
                                      command=self.stop_bot)
        self.btn_stop.pack(side="right", padx=(8, 0))
        self.btn_start = ctk.CTkButton(h, text="▶  Запустить", width=140, height=36, fg_color=ACCENT,
                                       hover_color=ACCENT_H, text_color=BTN_TXT, font=F(13, True),
                                       command=self.start_bot)
        self.btn_start.pack(side="right")

        # статистика
        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 14))
        self.stat_labels = {}
        for i, (k, t) in enumerate([("time", "Время работы"), ("matches", "Каток запущено"),
                                    ("jumps", "Прыжков"), ("chests", "Сундуков"),
                                    ("rewards", "Наград забрано"), ("tokens", "Токенов 🏴‍☠️")]):
            c = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=10)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            stats.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(c, text=t, text_color=MUTED, font=F(12)).pack(anchor="w", padx=16, pady=(12, 0))
            lb = ctk.CTkLabel(c, text="0", text_color=TEXT, font=F(22, True))
            lb.pack(anchor="w", padx=16, pady=(0, 12))
            self.stat_labels[k] = lb

        # профили
        prof = ctk.CTkFrame(page, fg_color="transparent")
        prof.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(prof, text="Быстрые профили:", text_color=MUTED, font=F(13)).pack(side="left", padx=(0, 10))
        for name, title in [("token", "🏴‍☠️ Фарм токена"), ("max", "⚡ Максимум каток"), ("night", "🌙 Тихая ночь")]:
            ctk.CTkButton(prof, text=title, height=34, fg_color=CARD2, hover_color=ACCENT_D, text_color=TEXT,
                          font=F(13, True), command=lambda n=name: self.apply_profile(n)).pack(side="left", padx=(0, 8))

        # вкладки: Free / VIP / Premium
        tabrow = ctk.CTkFrame(page, fg_color="transparent")
        tabrow.pack(fill="x", pady=(2, 8))
        self.ftab_seg = ctk.CTkSegmentedButton(
            tabrow, values=["🆓  Free", "★  VIP", "♛  Premium", "⚡  Ultimate"],
            command=self._func_tab_switch, selected_color=ACCENT_D, selected_hover_color=ACCENT_D,
            unselected_color=CARD, unselected_hover_color=CARD2, fg_color=CARD, text_color=TEXT,
            font=F(14, True), height=40)
        self.ftab_seg.pack(fill="x")
        holder = ctk.CTkFrame(page, fg_color="transparent")
        holder.pack(fill="x")
        self.ftabs = {}
        for n in ("free", "vip", "premium", "ultimate"):
            fr = ctk.CTkFrame(holder, fg_color="transparent")
            self.ftabs[n] = fr
        cards = [
            ("auto_play", "Запуск катки",
             "Сам запускает Королевскую битву. После катки жмёт «Играть снова», так отряд и режим "
             "не слетают. В лобби выходит, только если этой кнопки нет. Ниже выбери режим для "
             "лобби. По умолчанию Отряды, чтобы не кидало в соло.",
             ("team_size", {"Соло": "solo", "Дуо": "duos", "Трио": "trios", "Отряды": "squads"})),
            ("auto_leave", "Выход из игры",
             "Выходит, когда вся команда погибла или матч закончился. Если матч завис, "
             "выйдет через ESC.", ("max_match_min", "Выход через ESC после, мин", 10, 120)),
            ("team_check", "Рестарт, если команда выбыла",
             "Смотрит на панель команды. Если тиммейты выбыли или их не было с самого начала, "
             "выходит и ищет новую катку, а не стоит один. Если выбили тебя, а свои ещё живы, "
             "ждёт их. В соло не работает.", None),
            ("zone_nav", "Зона и вода (компас + миникарта)",
             "Читает компас и миникарту: видит шторм и воду, бежит в безопасную зону и не лезет в "
             "воду. Поворот камеры калибрует сам в первые секунды катки.", None),
            ("sprint", "Спринт и живые движения",
             "Иногда зажимает Shift, стрейфит и меняет направление. Бегает как игрок, а не "
             "как скрипт по прямой.", None),
            ("reward_shots", "Скрин награды",
             "Выпала награда или Пиратский токен? Бот сохранит скрин в папку rewards и "
             "скинет его в Telegram, если он подключён.", None),
            ("skip_rewards", "Скип наград",
             "Забирает награды («Получить всё», «Забрать») и закрывает окна «Продолжить» / «Закрыть».",
             None),
            ("auto_restart", "Перезапуск игры при ошибках",
             "Если Fortnite вылетел или завис и бот долго ничего не нажимал, он закроет и запустит "
             "игру заново.", ("stuck_min", "Перезапуск, если нет действий, мин", 5, 120)),
            ("auto_jump", "Прыжок из автобуса",
             "Когда появляется подсказка «Прыгнуть», ждёт и прыгает пробелом.",
             ("jump_delay", "Прыгать через, сек", 0, 60)),
            ("anti_afk", "Анти-AFK",
             "Зажимает W, потом отпускает и ждёт, и так по кругу, чтобы игра не выкинула "
             "за бездействие.",
             [("afk_hold", "Держать W, сек", 1, 300),
              ("afk_pause", "Пауза между зажатиями, сек", 5, 600)]),
            ("explore", "Играть вместо меня: бег",
             "После приземления бегает по карте, перепрыгивает препятствия, обходит стены и идёт к "
             "сундукам. Сундук открывается, только когда бот ВИДИТ его и рядом подсказка «Обыскать». "
             "Сундуки находит по золотому свечению.",
             [("explore_delay", "Макс. ждать приземления, сек", 10, 180),
              ("turn_speed", "Чувствительность поворота", 100, 3000)]),
            ("auto_pause", "Умная пауза",
             "Сел за ПК и трогаешь мышь или клавиатуру? Бот сам встанет на паузу и не будет мешать. "
             "Отошёл, и через пару минут он продолжит. Свои нажатия бот не считает.",
             ("resume_min", "Продолжить, если тебя нет, мин", 1, 60)),
            ("monitor_off", "Экономия ресурсов",
             "Гасит монитор, пока бот работает и тебя нет за ПК. Можно ограничить FPS игры, тогда ПК "
             "меньше греется и шумит ночью (FPS применяется при запуске игры, потом вернётся как было).",
             ("fps_limit", "Ограничить FPS игры (0 = не трогать)", 0, 240)),
        ]
        if self.is_admin:
            cards.append(("dataset_capture", "🗂 Сбор кадров для нейросети (админ)",
                          "Во время бега сохраняет кадры в папку dataset\\images. Из них потом размечаешь и "
                          "обучаешь модель YOLO. Похожие подряд кадры пропускает. Инструкция: "
                          "НЕЙРОСЕТЬ_ИНСТРУКЦИЯ.txt.",
                          ("dataset_every", "Сохранять раз в, сек", 1, 30)))
        free_cards = [c for c in cards if c[0] in bot_core.FREE_FEATURES]
        vip_cards = [c for c in cards if c[0] not in bot_core.FREE_FEATURES
                     and c[0] not in bot_core.ULTIMATE_FEATURES]     # Ultimate — на своей вкладке
        # Free
        fr = self.ftabs["free"]
        self._tab_banner(fr, "🆓 Бесплатно навсегда", "Базовый AFK-фарм: сам запускает катки, прыгает "
                         "из автобуса и встаёт на паузу, когда ты за ПК.", None)
        g = self._grid(fr)
        for i, (key, title, desc, num) in enumerate(free_cards):
            self._func_card(g, i // 2, i % 2, key, title, desc, num)
        # VIP
        fr = self.ftabs["vip"]
        if self.vip:
            self._tab_banner(fr, "★ VIP активен", "Все функции VIP открыты. Настраивай под себя.", None)
        else:
            self._tab_banner(fr, f"♛ Открой за {self.shop.get('price_premium', '159')} ₽ в Premium",
                             "Бот играет за тебя всю ночь: выход в лобби, «Играть снова», награды, "
                             "анти-AFK, сундуки и отчёты в Telegram.", ("♛  Открыть Premium", "premium"))
        g = self._grid(fr)
        for i, (key, title, desc, num) in enumerate(vip_cards):
            self._func_card(g, i // 2, i % 2, key, title, desc, num)
        self._tg_card(fr)
        # Premium
        self.build_premium_tab(self.ftabs["premium"])
        self.build_ultimate_tab(self.ftabs["ultimate"])
        self._func_tab_switch({"free": "🆓  Free", "vip": "★  VIP", "ultimate": "⚡  Ultimate"}.get(
            self.tier, "♛  Premium") if not getattr(self, "_ftab", None) else self._ftab)
        self._settings_card(page)

        # журнал
        ctk.CTkLabel(page, text="Журнал", text_color=TEXT, font=F(16, True)).pack(anchor="w", pady=(18, 6))
        self.logbox = ctk.CTkTextbox(page, height=220, fg_color=CARD, text_color=TEXT,
                                     font=ctk.CTkFont(family="Consolas", size=12), corner_radius=10)
        self.logbox.pack(fill="x")
        self.logbox.configure(state="disabled")
        self._append_log(time.strftime("[%H:%M:%S] ") + "Готов к работе. Открой Fortnite в режиме "
                         "«Оконный без рамок» и нажми «Запустить».")

    def _func_card(self, grid, r, c, key, title, desc, num):
        card = ctk.CTkFrame(grid, fg_color=CARD, corner_radius=10)
        card.grid(row=r, column=c, sticky="nsew", padx=(0, 6) if c == 0 else (6, 0), pady=6)
        locked = not self._allowed(key)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(top, text=title, text_color=MUTED if locked else TEXT,
                     font=F(14, True)).pack(side="left")
        if locked:
            (self.ultimate_badge(top) if key in bot_core.ULTIMATE_FEATURES else
             self.premium_badge(top) if key in bot_core.PREMIUM_FEATURES else self.vip_badge(top)).pack(
                side="left", padx=8)
        var = tk.BooleanVar(value=bool(self.settings.get(key)) and not locked)

        def toggled():
            self.settings[key] = bool(var.get())
            save_settings(self.settings)
        sw = ctk.CTkSwitch(top, text="", variable=var, command=toggled, width=46,
                           progress_color=ACCENT, button_color=TEXT, button_hover_color="#ffffff",
                           fg_color=BORDER)
        sw.pack(side="right")
        if locked:
            sw.configure(state="disabled")
            for w in (card, top):
                w.bind("<Button-1>", lambda e: self.show_page("shop"))
        ctk.CTkLabel(card, text=desc, text_color=MUTED, font=F(12), wraplength=380,
                     justify="left").pack(anchor="w", padx=16, pady=(0, 12 if not num else 6))
        allopts = num if isinstance(num, list) else ([num] if num else [])
        # варианты-переключатели: (ключ, {подпись: значение})
        for skey, opts in [o for o in allopts if len(o) == 2 and isinstance(o[1], dict)]:
            back = {v: k for k, v in opts.items()}

            def seg_cmd(label, skey=skey, opts=opts):
                self.settings[skey] = opts[label]
                save_settings(self.settings)
            seg = ctk.CTkSegmentedButton(card, values=list(opts), command=seg_cmd,
                                         selected_color=ACCENT_D, selected_hover_color=ACCENT_D,
                                         unselected_color=CARD2, unselected_hover_color=BORDER,
                                         fg_color=CARD2, text_color=TEXT, font=F(12))
            seg.set(back.get(self.settings.get(skey, bot_core.DEFAULTS.get(skey)), list(opts)[-1]))
            seg.pack(anchor="w", padx=16, pady=(0, 10))
            if locked:
                seg.configure(state="disabled")
        nums = [o for o in allopts if len(o) == 4]
        for j, (nkey, ntitle, lo, hi) in enumerate(nums):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(0, 14 if j == len(nums) - 1 else 6))
            ctk.CTkLabel(row, text=ntitle, text_color=MUTED, font=F(12)).pack(side="left")
            e = ctk.CTkEntry(row, width=70, height=28, fg_color=CARD2, border_color=BORDER,
                             text_color=TEXT, font=F(13), justify="center")
            e.insert(0, str(int(float(self.settings.get(nkey, 0)))))
            e.pack(side="right")
            if locked:
                e.configure(state="disabled")

            def apply(*_, e=e, nkey=nkey, lo=lo, hi=hi):
                try:
                    v = max(lo, min(hi, int(float(e.get().replace(",", ".")))))
                except ValueError:
                    v = int(float(self.settings.get(nkey, lo)))
                e.delete(0, "end")
                e.insert(0, str(v))
                self.settings[nkey] = v
                save_settings(self.settings)
            e.bind("<Return>", apply)
            e.bind("<FocusOut>", apply)

    def premium_badge(self, parent):
        return ctk.CTkLabel(parent, text=" ♛ PREMIUM ", fg_color=GOLD, text_color="#2b1f06", corner_radius=6,
                            font=F(11, True), height=20)

    def ultimate_badge(self, parent):
        return ctk.CTkLabel(parent, text=" ⚡ ULTIMATE ", fg_color=ULTRA, text_color="#06212b", corner_radius=6,
                            font=F(11, True), height=20)

    def vip_badge(self, parent):
        return ctk.CTkLabel(parent, text=" VIP ", fg_color=ACCENT_D, text_color=TEXT, corner_radius=6,
                            font=F(11, True), height=20)

    def _tg_card(self, page):
        card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=10)
        card.pack(fill="x", pady=(6, 0))
        if not self.vip:
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=16, pady=(14, 4))
            ctk.CTkLabel(top, text="Награды и отчёты в Telegram", text_color=MUTED,
                         font=F(14, True)).pack(side="left")
            self.vip_badge(top).pack(side="left", padx=8)
            ctk.CTkLabel(card, text="Скрин и список наград, отчёты о работе бота и итог при остановке. "
                                    "прямо в Telegram.", text_color=MUTED, font=F(12),
                         wraplength=820, justify="left").pack(anchor="w", padx=16)
            ctk.CTkButton(card, text="★  Открыть VIP", height=32, fg_color=ACCENT, hover_color=ACCENT_H,
                          text_color=BTN_TXT, font=F(12, True), command=lambda: self.show_page("shop")).pack(
                anchor="w", padx=16, pady=(8, 14))
            return
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(top, text="Награды в Telegram", text_color=TEXT, font=F(14, True)).pack(side="left")
        var = tk.BooleanVar(value=bool(self.settings.get("tg_enabled")))

        def toggled():
            self.settings["tg_enabled"] = bool(var.get())
            save_settings(self.settings)
        ctk.CTkSwitch(top, text="", variable=var, command=toggled, width=46, progress_color=ACCENT,
                      button_color=TEXT, button_hover_color="#ffffff", fg_color=BORDER).pack(side="right")
        ctk.CTkLabel(card, text="Награды (скрин + что выпало), отчёты о работе и итог при остановке "
                                "приходят тебе в Telegram. Как подключить: в Telegram открой @BotFather → /newbot → "
                                "скопируй токен сюда → открой своего бота и нажми Start → "
                                "«Найти мой Chat ID».",
                     text_color=MUTED, font=F(12), wraplength=820, justify="left").pack(anchor="w", padx=16)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(row, text="Токен бота", text_color=MUTED, font=F(12), width=90,
                     anchor="w").pack(side="left")
        tok = ctk.CTkEntry(row, height=30, fg_color=CARD2, border_color=BORDER, text_color=TEXT,
                           font=F(12), show="•", placeholder_text="123456789:AA...")
        tok.pack(side="left", fill="x", expand=True)
        if self.settings.get("tg_token"):
            tok.insert(0, self.settings["tg_token"])

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(4, 4))
        ctk.CTkLabel(row2, text="Chat ID", text_color=MUTED, font=F(12), width=90,
                     anchor="w").pack(side="left")
        chat = ctk.CTkEntry(row2, height=30, width=180, fg_color=CARD2, border_color=BORDER,
                            text_color=TEXT, font=F(12))
        chat.pack(side="left")
        if self.settings.get("tg_chat"):
            chat.insert(0, self.settings["tg_chat"])
        photo_var = tk.BooleanVar(value=bool(self.settings.get("tg_photo", True)))

        def photo_toggled():
            self.settings["tg_photo"] = bool(photo_var.get())
            save_settings(self.settings)
        ctk.CTkCheckBox(row2, text="присылать скрин", variable=photo_var, command=photo_toggled,
                        fg_color=ACCENT, hover_color=ACCENT_H, border_color=BORDER, text_color=TEXT,
                        font=F(12), checkbox_width=18, checkbox_height=18).pack(side="left", padx=14)

        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x", padx=16, pady=(4, 4))

        def make_check(parent, key, text):
            v = tk.BooleanVar(value=bool(self.settings.get(key)))

            def cmd():
                self.settings[key] = bool(v.get())
                save_settings(self.settings)
            ctk.CTkCheckBox(parent, text=text, variable=v, command=cmd, fg_color=ACCENT,
                            hover_color=ACCENT_H, border_color=BORDER, text_color=TEXT, font=F(12),
                            checkbox_width=18, checkbox_height=18).pack(side="left", padx=(0, 6))
        make_check(row3, "tg_reports", "Отчёт (время, катки, сундуки, награды) каждые")
        rep_e = ctk.CTkEntry(row3, width=56, height=28, fg_color=CARD2, border_color=BORDER,
                             text_color=TEXT, font=F(12), justify="center")
        rep_e.insert(0, str(int(float(self.settings.get("report_min", 60)))))
        rep_e.pack(side="left")
        ctk.CTkLabel(row3, text="мин", text_color=MUTED, font=F(12)).pack(side="left", padx=(6, 24))

        def rep_apply(*_):
            try:
                v = max(5, min(1440, int(float(rep_e.get()))))
            except ValueError:
                v = 60
            rep_e.delete(0, "end")
            rep_e.insert(0, str(v))
            self.settings["report_min"] = v
            save_settings(self.settings)
        rep_e.bind("<Return>", rep_apply)
        rep_e.bind("<FocusOut>", rep_apply)
        make_check(row3, "tg_match", "Сообщать о каждой катке")
        row4 = ctk.CTkFrame(card, fg_color="transparent")
        row4.pack(fill="x", padx=16, pady=(4, 4))
        make_check(row4, "tg_control", "Управление из Telegram: /status /screen /start /stop /pause")
        make_check(row4, "token_alert", "🏴‍☠️ Громкое уведомление, если выпал Пиратский токен")
        make_check(row4, "fun_log", "🤖 Живые реплики бота в логе (прикол)")

        msg = ctk.CTkLabel(card, text="", text_color=MUTED, font=F(12), wraplength=820, justify="left")

        def store(*_):
            self.settings["tg_token"] = tok.get().strip()
            self.settings["tg_chat"] = chat.get().strip()
            save_settings(self.settings)
        tok.bind("<FocusOut>", store)
        chat.bind("<FocusOut>", store)

        def find_id():
            store()
            if not self.settings["tg_token"]:
                msg.configure(text="Сначала вставь токен бота", text_color=YELLOW)
                return
            msg.configure(text="Ищу...", text_color=MUTED)
            self._tg_poll_pause = True

            def done(res):
                self._tg_poll_pause = False
                if isinstance(res, Exception):
                    msg.configure(text=str(res), text_color=RED)
                    return
                cid, name = res
                chat.delete(0, "end")
                chat.insert(0, cid)
                store()
                msg.configure(text=f"Нашёл: {name} ({cid}). Нажми «Тест».", text_color=GREEN)
            import tg_notify
            self.bg(tg_notify.find_chat_id, done, self.settings["tg_token"])

        def test():
            store()
            if not (self.settings["tg_token"] and self.settings["tg_chat"]):
                msg.configure(text="Заполни токен и Chat ID", text_color=YELLOW)
                return
            msg.configure(text="Отправляю...", text_color=MUTED)

            def done(res):
                if isinstance(res, Exception):
                    msg.configure(text=str(res), text_color=RED)
                else:
                    msg.configure(text="Готово, проверь Telegram", text_color=GREEN)
            import tg_notify
            self.bg(tg_notify.send_text, done, self.settings["tg_token"], self.settings["tg_chat"],
                    "✅ Afk token подключён. Сюда будут приходить награды.")

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(6, 6))
        ctk.CTkButton(btns, text="Найти мой Chat ID", height=32, fg_color=CARD2, hover_color=BORDER,
                      text_color=TEXT, font=F(12), command=find_id).pack(side="left")
        ctk.CTkButton(btns, text="Тест", height=32, width=80, fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=BTN_TXT, font=F(12, True), command=test).pack(side="left", padx=8)
        self.link(btns, "Открыть @BotFather", "https://t.me/BotFather", 12).pack(side="left", padx=8)
        msg.pack(anchor="w", padx=16, pady=(0, 12))

    def _append_log(self, line):
        if not hasattr(self, "logbox"):
            return
        try:
            self.logbox.configure(state="normal")
            self.logbox.insert("end", line + "\n")
            if int(self.logbox.index("end-1c").split(".")[0]) > 800:
                self.logbox.delete("1.0", "200.0")
            self.logbox.see("end")
            self.logbox.configure(state="disabled")
        except Exception:
            pass

    def start_bot(self):
        if self.bot.running:
            return
        if getattr(self, "tier", "free") != "free" and not self.settings.get("explore_auto_on"):
            # платный ключ: один раз включаем «Бег», иначе бот после приземления стоит
            self.settings["explore"] = True
            self.settings["explore_auto_on"] = True
            save_settings(self.settings)
            self.bot.log("🏃 Включил «Бег»: без него бот не ходит по карте и не крутит камерой")
        # без сервера (демо) — как раньше
        if not lic.configured():
            self.bot.start()
            self._set_bot_state("loading")
            return
        self._set_bot_state("loading")
        try:
            self.st_sub.configure(text="Проверка ключа на сервере...")
        except Exception:
            pass

        def done(res):
            if isinstance(res, Exception) or not isinstance(res, dict) or res.get("reason") == "empty":
                loc = lic.local_license()      # сервер недоступен → пробуем аварийный режим
                if loc:
                    self.tier = loc["tier"]
                    self.bot.tier = self.tier
                    self.bot.vip = self.tier != "free"
                    self._gate_last_ok = 0      # старый → heartbeat сразу уйдёт в аварийный режим
                    self._gate_paused = False
                    self.bot.start()
                    self._set_bot_state("loading")
                    why = str(res) if isinstance(res, Exception) else "пустой ответ"
                    self._append_log(time.strftime("[%H:%M:%S] ") +
                                     f"🛟 Сервер не ответил ({why[:120]}), работаю в бесплатном режиме")
                    self.toast("Сервер не отвечает: пока работают только бесплатные функции", YELLOW)
                    self.after(lic.HEARTBEAT_MIN * 60000, self._gate_tick)
                    return
                self._set_bot_state("stopped")
                self.toast("Нет связи с сервером. Нужен интернет для запуска", RED)
                return
            if not res.get("ok"):
                self._set_bot_state("stopped")
                self.toast(res.get("error") or "Ключ не разрешён", RED)
                return
            self.tier = res.get("tier") or self.tier
            self.bot.tier = self.tier
            self.bot.vip = self.tier != "free"
            self._gate_last_ok = time.time()
            self._gate_paused = False
            self.bot.start()
            self._set_bot_state("loading")
            self.after(lic.HEARTBEAT_MIN * 60000, self._gate_tick)
        self.bg(lic.session, done, True)

    def _gate_tick(self):
        if not self.bot.running or not lic.configured():
            return

        def done(res):
            if isinstance(res, Exception):
                self._gate_err = str(res)[:120]
            net_err = isinstance(res, lic.NetworkError)
            result = res if isinstance(res, dict) else None
            decision = lic.gate_decide(time.time(), self._gate_last_ok, result, net_err, lic.local_license())
            if decision.startswith("tier:"):
                self._gate_last_ok = time.time()
                self._gate_emergency = False
                self.tier = decision.split(":", 1)[1]
                self.bot.tier = self.tier
                self.bot.vip = self.tier != "free"
                if self._gate_paused:           # связь вернулась — снимаем нашу паузу
                    self._gate_paused = False
                    self.bot.paused = False
                    self._append_log(time.strftime("[%H:%M:%S] ") + "🌐 Связь с сервером вернулась, продолжаю")
            elif decision.startswith("emergency:"):
                self.tier = decision.split(":", 1)[1]
                self.bot.tier = self.tier
                self.bot.vip = self.tier != "free"
                if self._gate_paused:
                    self._gate_paused = False
                    self.bot.paused = False
                if not getattr(self, "_gate_emergency", False):
                    self._gate_emergency = True
                    why = getattr(self, "_gate_err", "") or "нет ответа"
                    self._append_log(time.strftime("[%H:%M:%S] ") +
                                     f"🛟 Сервер не ответил ({why}). Аварийный режим: только бесплатные функции")
            elif decision == "stop_banned":
                self._append_log(time.strftime("[%H:%M:%S] ") + "⛔ Ключ заблокирован, останавливаю")
                self.toast("Ключ заблокирован. Напиши @kk4ose", RED)
                self.bot.stop()
                return
            elif decision == "stop_invalid":
                self._append_log(time.strftime("[%H:%M:%S] ") + "⛔ Ключ не прошёл проверку, останавливаю")
                self.toast(result.get("error") if result else "Ключ не разрешён", RED)
                self.bot.stop()
                return
            elif decision == "pause_offline":
                if not self._gate_paused:
                    self._gate_paused = True
                    self.bot.paused = True
                    self._append_log(time.strftime("[%H:%M:%S] ") + "🌐 Нет связи с сервером, жду")
            if self.bot.running:
                self.after(lic.HEARTBEAT_MIN * 60000, self._gate_tick)
        self.bg(lic.session, done, False)

    def stop_bot(self):
        self.bot.stop()

    def _set_bot_state(self, st):
        if st != self.bot_state and st in ("running", "stopped"):
            save_settings(self.settings)
        self.bot_state = st
        if not hasattr(self, "st_title"):
            return
        try:
            texts = {
                "stopped": ("●  Бот остановлен", MUTED, "Нажми «Запустить» и отходи от ПК"),
                "loading": ("●  Загрузка...", YELLOW, "Загружаю распознавание текста"),
                "running": ("●  Бот работает", GREEN, "F9 пауза, F10 стоп"),
                "paused": ("●  Пауза", YELLOW, "F9 продолжить"),
            }
            t, col, sub = texts.get(st, texts["stopped"])
            self.st_title.configure(text=t, text_color=col)
            self.st_sub.configure(text=sub)
            busy = st in ("loading", "running", "paused")
            for b in (self.side_start, self.btn_start):
                b.configure(state="disabled" if busy else "normal")
            self.btn_pause.configure(text="Продолжить (F9)" if st == "paused" else "Пауза (F9)")
        except tk.TclError:
            pass

    def _tick_stats(self):
        if not hasattr(self, "stat_labels"):
            return
        try:
            s = self.bot.stats
            if s["started"]:
                sec = int(time.time() - s["started"])
                self.stat_labels["time"].configure(text=f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}")
            else:
                self.stat_labels["time"].configure(text="—")
            for k in ("matches", "jumps", "chests", "rewards", "tokens"):
                self.stat_labels[k].configure(text=str(s[k]))
            self._daily_tick()
            if getattr(self, "goal_lb", None) is not None:
                cur, need = self.bot.goal_progress() if self.bot.running else (0, self.bot.goal_progress()[1])
                t = self.settings.get("goal_type", "matches")
                self.goal_lb.configure(text=("Прогресс: ждём токен" if t == "token" and cur < 1 else
                                             f"Прогресс: {min(cur, need)} / {need}") if self.bot.running
                                       else "Прогресс появится после запуска бота")
        except tk.TclError:
            return
        self.after(1000, self._tick_stats)

    # ================= вкладка: рефералы =================
    def build_referral(self):
        page = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        self.pages["referral"] = page
        self.page_header(page, "Реферальная система", "зови друзей и получай VIP")

        hero = ctk.CTkFrame(page, fg_color=ACCENT_D, corner_radius=14)
        hero.pack(fill="x")
        ctk.CTkLabel(hero, text="Пригласи друга, который купит VIP,", text_color=TEXT,
                     font=F(20, True)).pack(anchor="w", padx=24, pady=(20, 0))
        ctk.CTkLabel(hero, text="получи VIP на 7 дней бесплатно 🎁", text_color="#ffd6e8",
                     font=F(20, True)).pack(anchor="w", padx=24)
        ctk.CTkLabel(hero, text="За каждого следующего ещё +7 дней. Дни складываются.",
                     text_color="#e9dcf7", font=F(13)).pack(anchor="w", padx=24, pady=(6, 20))

        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.pack(fill="x", pady=12)
        self.ref_stat = {}
        for i, (k, t, col) in enumerate([("invited", "Друзей купили VIP", TEXT),
                                         ("pending", "Ждут награды", ACCENT),
                                         ("rewarded", "Награды получены", GREEN)]):
            c = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=10)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            stats.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(c, text=t, text_color=MUTED, font=F(12)).pack(anchor="w", padx=16, pady=(12, 0))
            lb = ctk.CTkLabel(c, text="—", text_color=col, font=F(24, True))
            lb.pack(anchor="w", padx=16, pady=(0, 12))
            self.ref_stat[k] = lb

        card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=12)
        card.pack(fill="x")
        ctk.CTkLabel(card, text="Твой реф-код", text_color=MUTED, font=F(12)).pack(anchor="w", padx=18, pady=(16, 0))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(2, 8))
        self.ref_code_lb = ctk.CTkLabel(row, text="загрузка...", text_color=ACCENT, font=F(26, True))
        self.ref_code_lb.pack(side="left")
        self.ref_copy_code = ctk.CTkButton(row, text="Скопировать код", width=140, height=32, fg_color=CARD2,
                                           hover_color=BORDER, text_color=TEXT, font=F(12), state="disabled")
        self.ref_copy_code.pack(side="right")
        ctk.CTkLabel(card, text="Твоя реф-ссылка (отправь другу)", text_color=MUTED,
                     font=F(12)).pack(anchor="w", padx=18)
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=18, pady=(2, 16))
        self.ref_link_e = ctk.CTkEntry(row2, height=34, fg_color=CARD2, border_color=BORDER, text_color=TEXT,
                                       font=F(12))
        self.ref_link_e.pack(side="left", fill="x", expand=True)
        self.ref_copy_link = ctk.CTkButton(row2, text="Скопировать ссылку", width=160, height=34,
                                           fg_color=ACCENT, hover_color=ACCENT_H, text_color=BTN_TXT,
                                           font=F(12, True), state="disabled")
        self.ref_copy_link.pack(side="right", padx=(8, 0))

        act = ctk.CTkFrame(page, fg_color="transparent")
        act.pack(fill="x", pady=12)
        self.ref_claim_btn = ctk.CTkButton(act, text="🎁  Забрать VIP", height=42, width=200, fg_color=ACCENT,
                                           hover_color=ACCENT_H, text_color=BTN_TXT, font=F(14, True),
                                           state="disabled", command=self.ref_claim)
        self.ref_claim_btn.pack(side="left")
        ctk.CTkButton(act, text="⟳  Обновить", height=42, width=120, fg_color=CARD2, hover_color=BORDER,
                      text_color=TEXT, font=F(13), command=self.ref_refresh).pack(side="left", padx=10)
        self.ref_msg = ctk.CTkLabel(act, text="", text_color=MUTED, font=F(12), wraplength=420, justify="left")
        self.ref_msg.pack(side="left", padx=6)

        ctk.CTkLabel(page, text="Как это работает", text_color=TEXT, font=F(16, True)).pack(anchor="w", pady=(10, 6))
        for i, (t, d) in enumerate([
                ("Скопируй ссылку и отправь другу", "По ссылке он попадёт в Telegram к продавцу, а твой "
                 "реф-код уже будет в сообщении."),
                ("Друг покупает VIP", "Через Telegram @kk4ose или Starvell. При активации ключа он вводит "
                 "твой реф-код в поле «Реф-код друга»."),
                ("Ты забираешь награду", "Тут появится «Ждут награды: 1». Нажми «Забрать VIP», и "
                 "получишь 7 дней VIP сразу, без перезапуска.")], 1):
            c = ctk.CTkFrame(page, fg_color=CARD, corner_radius=10)
            c.pack(fill="x", pady=4)
            ctk.CTkLabel(c, text=str(i), width=32, height=32, corner_radius=16, fg_color=ACCENT_D, text_color=TEXT,
                         font=F(14, True)).pack(side="left", padx=14, pady=12, anchor="n")
            box = ctk.CTkFrame(c, fg_color="transparent")
            box.pack(side="left", fill="x", expand=True, pady=10, padx=(0, 14))
            ctk.CTkLabel(box, text=t, text_color=TEXT, font=F(14, True)).pack(anchor="w")
            ctk.CTkLabel(box, text=d, text_color=MUTED, font=F(12), wraplength=700,
                         justify="left").pack(anchor="w")
        ctk.CTkLabel(page, text="Засчитываются только друзья, купившие VIP навсегда. Свой код использовать "
                                "нельзя, один купленный ключ = одно приглашение.",
                     text_color=MUTED, font=F(11), wraplength=780, justify="left").pack(anchor="w", pady=(8, 0))

    def ref_refresh(self):
        if not hasattr(self, "ref_code_lb"):
            return
        if not lic.configured():
            self.ref_msg.configure(text="Сервер не настроен", text_color=RED)
            return
        self.ref_msg.configure(text="Загрузка...", text_color=MUTED)

        def done(res):
            try:
                if isinstance(res, Exception) or not res:
                    self.ref_msg.configure(text=f"Нет связи с сервером: {res}", text_color=RED)
                    return
                code = res.get("code", "")
                from urllib.parse import quote
                link = lic.TG_URL + "?text=" + quote(f"Привет! Хочу купить VIP Afk token. Мой реф-код: {code}")
                self.ref_code_lb.configure(text=code)
                self.ref_link_e.configure(state="normal")
                self.ref_link_e.delete(0, "end")
                self.ref_link_e.insert(0, link)
                self.ref_copy_code.configure(state="normal", command=lambda: (
                    self.copy(code), self.toast("Реф-код скопирован", GREEN)))
                self.ref_copy_link.configure(state="normal", command=lambda: (
                    self.copy(link), self.toast("Ссылка скопирована, скинь её другу 💜", GREEN)))
                for k in ("invited", "pending", "rewarded"):
                    self.ref_stat[k].configure(text=str(res.get(k, 0)))
                pending = int(res.get("pending", 0))
                self.ref_claim_btn.configure(
                    state="normal" if pending else "disabled",
                    text=f"🎁  Забрать VIP на {7 * pending} дн." if pending else "🎁  Забрать VIP")
                self.ref_msg.configure(text="" if pending else "Пока друзей с VIP нет. Скинь ссылку 🙂",
                                       text_color=MUTED)
            except tk.TclError:
                pass
        self.bg(lic.ref_me, done)

    def ref_claim(self):
        self.ref_claim_btn.configure(state="disabled", text="Начисляю...")

        def done(res):
            if isinstance(res, Exception) or not res or not res.get("ok"):
                err = res if isinstance(res, Exception) else (res or {}).get("error", "ошибка")
                self.toast(f"Не получилось: {err}", YELLOW)
                self.ref_refresh()
                return
            key = res["key"]

            def activated(r):
                if isinstance(r, dict) and r.get("ok"):
                    self.key = key
                    self.vip_until = r.get("expires_at")
                    self.show_main()
                    self.show_page("referral")
                    self.toast(f"🎁 +{res.get('days', 7)} дней VIP! Все функции открыты", GREEN)
                else:
                    self.toast("VIP начислен, но не включился. Перезапусти программу", YELLOW)
            self.bg(lic.activate, activated, key)
        self.bg(lic.ref_claim, done)

    # ================= профили =================
    PROFILES = {
        "token": dict(auto_play=True, auto_leave=True, skip_rewards=True, auto_restart=True, auto_jump=True,
                      jump_delay=8, explore=True, anti_afk=False, launch_mode="replay", token_alert=True),
        "max": dict(auto_play=True, auto_leave=True, skip_rewards=True, auto_restart=True, auto_jump=True,
                    jump_delay=3, explore=False, anti_afk=True, launch_mode="replay", max_match_min=25),
        "night": dict(auto_play=True, auto_leave=True, skip_rewards=True, auto_restart=True, auto_jump=True,
                      jump_delay=8, explore=True, anti_afk=False, launch_mode="replay", monitor_off=True,
                      fps_limit=30, tg_reports=True, report_min=60, auto_pause=True, token_alert=True),
    }
    PROFILE_NAMES = {"token": "Фарм токена", "max": "Максимум каток", "night": "Тихая ночь"}

    def apply_profile(self, name):
        self.settings.update(self.PROFILES[name])
        save_settings(self.settings)
        self.show_main()
        self.show_page("functions")
        extra = "" if self.vip else " (VIP-функции включатся после активации VIP)"
        self.toast(f"Профиль «{self.PROFILE_NAMES[name]}» применён{extra}", GREEN)

    # ================= управление из Telegram =================
    def _start_tg_poll(self):
        if getattr(self, "_tg_poll_started", False):
            return
        self._tg_poll_started = True
        self._tg_poll_pause = False
        threading.Thread(target=self._tg_poll_loop, daemon=True).start()

    def _tg_poll_loop(self):
        import tg_notify
        offset, cur_tok = None, None
        while True:
            s = self.settings
            tok, chat = s.get("tg_token", ""), str(s.get("tg_chat", ""))
            if (self._tg_poll_pause or not tok or not chat or not s.get("tg_control", True)
                    or not self.bot.on("tg_enabled")):
                time.sleep(5)
                continue
            try:
                if tok != cur_tok:  # новый токен - пропускаем старые сообщения
                    ups = tg_notify.get_updates(tok, -1, 0)
                    offset = ups[-1]["update_id"] + 1 if ups else None
                    cur_tok = tok
                    try:
                        tg_notify.set_commands(tok)
                    except Exception:
                        pass
                    continue
                for u in tg_notify.get_updates(tok, offset, 25):
                    offset = u["update_id"] + 1
                    m = u.get("message") or {}
                    if str((m.get("chat") or {}).get("id")) != chat:
                        continue
                    txt = (m.get("text") or "").strip()
                    cmd = None
                    if txt.startswith("/"):
                        cmd = txt.split()[0].split("@")[0].lower()
                    elif txt in TG_BUTTONS:
                        cmd = TG_BUTTONS[txt]
                    if cmd:
                        self.q.put(("cb", lambda _, c=cmd: self.tg_command(c), None))
            except Exception:
                time.sleep(15)

    def tg_reply(self, text=None, photo=None):
        import tg_notify
        s = self.settings

        def send():
            try:
                if photo:
                    tg_notify.send_photo(s["tg_token"], s["tg_chat"], photo, text or "")
                else:
                    tg_notify.send_text(s["tg_token"], s["tg_chat"], text)
            except Exception:
                pass
        threading.Thread(target=send, daemon=True).start()

    def tg_menu(self, text="📱 Пульт Afk token"):
        import tg_notify
        s = self.settings

        def send():
            try:
                tg_notify.send_menu(s["tg_token"], s["tg_chat"], text, TG_MENU_ROWS)
            except Exception:
                pass
        threading.Thread(target=send, daemon=True).start()

    def tg_command(self, cmd):
        b = self.bot
        state = ("⏸ на паузе" if b.paused else "▶ работает") if b.running else "⏹ остановлен"
        prem_cmds = ("/menu", "/chests", "/restart", "/off60", "/offcancel", "/goal")
        if cmd in prem_cmds and not b.on("tg_menu"):
            self.tg_reply("♛ Кнопки-пульт, перезапуск игры, выключение ПК и цель есть в Premium.\n"
                          "Открой вкладку «Магазин» в программе.")
            return
        if cmd == "/menu":
            self.tg_menu("📱 Пульт Afk token, жми кнопки внизу 👇")
        elif cmd == "/chests":
            self.settings["explore"] = not self.settings.get("explore")
            save_settings(self.settings)
            self.tg_reply("📦 Сундуки: " + ("включены" if self.settings["explore"] else "выключены"))
        elif cmd == "/restart":
            self.tg_reply("🔄 Перезапускаю Fortnite...")

            def restart():
                b.kill_fortnite()
                b.stats["restarts"] += 1
                if b.running and b.on("auto_restart"):
                    return                      # бот сам увидит, что игры нет, и запустит её
                time.sleep(20)
                try:
                    os.startfile(bot_core.LAUNCH_URL)
                except Exception as e:
                    self.tg_reply(f"Не удалось запустить Fortnite: {e}")
            threading.Thread(target=restart, daemon=True).start()
        elif cmd == "/off60":
            os.system("shutdown /s /t 3600")
            self.tg_reply("🌙 ПК выключится через час. Передумал? Жми «❌ Отменить выключение»")
        elif cmd == "/offcancel":
            os.system("shutdown /a")
            self.tg_reply("❌ Выключение ПК отменено")
        elif cmd == "/goal":
            cur, need = b.goal_progress()
            t = self.settings.get("goal_type", "matches")
            if not self.settings.get("goal_on"):
                self.tg_reply("🎯 Цель не включена (Функции Premium → Фарм под цель)")
            else:
                what = "Пиратский токен" if t == "token" else f"{bot_core.GOAL_NAMES.get(t, '').capitalize()}: {need}"
                self.tg_reply(f"🎯 Цель: {what}\nПрогресс: {cur if b.running else 0} / {need}")
        elif cmd == "/status":
            self.tg_reply(b.report_text(f"📊 Afk token: {state}"))
        elif cmd == "/start":
            if b.running:
                self.tg_reply("Бот уже работает ▶")
            else:
                self.start_bot()
                self.tg_reply("▶ Запускаю бота...")
        elif cmd == "/stop":
            if b.running:
                self.stop_bot()
                self.tg_reply("⏹ Останавливаю бота")
            else:
                self.tg_reply("Бот и так остановлен")
        elif cmd == "/pause":
            if b.running:
                b.toggle_pause()
                self.tg_reply("⏸ Пауза" if b.paused else "▶ Продолжаю")
            else:
                self.tg_reply("Бот остановлен, сначала /start")
        elif cmd == "/screen":
            def shot():
                try:
                    return bot_core.AfkBot.screenshot_jpg()
                except Exception as e:
                    return e

            def done(res):
                if isinstance(res, Exception) or not res:
                    self.tg_reply(f"Не удалось сделать скрин: {res}")
                else:
                    self.tg_reply(f"🖥 Экран · {time.strftime('%H:%M:%S')} · бот {state}", photo=res)
            self.bg(shot, done)
        else:
            extra = ("\n\n♛ Premium:\n/menu  кнопки-пульт\n/chests  сундуки вкл/выкл\n/restart  перезапуск игры\n"
                     "/off60  выключить ПК через час\n/offcancel  отменить выключение\n/goal  прогресс цели")
            self.tg_reply("🤖 Команды Afk token:\n/status  статус и статистика\n/screen  скрин экрана\n"
                          "/start  запустить бота\n/stop  остановить\n/pause  пауза / продолжить" + extra)

    # ================= вкладка: FAQ =================
    def build_faq(self):
        page = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        self.pages["faq"] = page
        self.page_header(page, "FAQ", "ответы на частые вопросы")
        sections = [
            ("🚀  Как запустить", [
                ("Что нужно перед первым запуском?",
                 "Windows 10/11 и Python 3.13 (64-bit). Не самый новый с жёлтой кнопки, а именно 3.13: python.org → "
                 "Downloads → Windows → «Python 3.13.x» → Windows installer (64-bit). При установке поставь "
                 "галочку «Add python.exe to PATH». "
                 "Запускай через start.bat. В первый раз он минут 5–10 ставит библиотеки, это нормально."),
                ("Как настроить Fortnite?",
                 "Настройки → Видео → Режим окна: «Оконный без рамок». В полноэкранном режиме бот не "
                 "видит экран. Язык игры русский или английский. В лобби выбери Королевская битва → Отряды."),
                ("Как запустить бота?",
                 "Открой Fortnite и дождись лобби. Во вкладке «Функции бота» включи нужное и нажми "
                 "«Запустить». Первый раз бот ~1–3 минуты загружает распознавание текста. "
                 "Дальше можно отходить от ПК."),
                ("Горячие клавиши",
                 "F9 пауза / продолжить, F10 остановить бота. Работают прямо из игры."),
                ("Как сделать, чтобы всё запускалось само?",
                 "Внизу вкладки «Функции бота» → «Программа»: включи «Запускать вместе с Windows» и "
                 "«Сразу запускать бота». Afk token будет стартовать при включении ПК и сидеть в трее."),
                ("Как управлять ботом с телефона?",
                 "Подключи Telegram-бота (карточка «Награды в Telegram») и пиши ему команды: /status "
                 "(статус и статистика), /screen (скрин экрана), /start, /stop, /pause."),
                ("Что даёт Premium?",
                 "Всё из VIP + 10 функций: пульт в Telegram с кнопками, фарм до цели (каток / наград / "
                 "токена), статистика и графики, расписание, точка высадки, ночной режим 2.0, свои "
                 "профили, анти-кик «как человек», темы и значок ♛ в чате, приоритетная поддержка. "
                 "Если у тебя уже VIP навсегда, апгрейд до Premium дешевле (вкладка «Магазин»)."),
                ("Что даёт Ultimate?",
                 "Всё из Premium + умный бег: обход препятствий, плавная мышь как у живого игрока, уход "
                 "от зоны и выход из катки, если остался в команде один. Открытие сундуков через ИИ "
                 "появится позже. Функции лежат во вкладке «Функции бота» → «Ultimate»."),
                ("Как писать в чат?",
                 "Во вкладке «Чат» сидят все, у кого стоит Afk token. Придумай ник и пиши. "
                 "Ссылки и рекламу нельзя, за спам и оскорбления мут. VIP видно по значку ★."),
                ("Награды в Telegram",
                 "@BotFather → /newbot → вставь токен в карточку «Награды в Telegram» → открой своего бота, "
                 "нажми Start → «Найти мой Chat ID» → «Тест»."),
                ("Что-то не работает",
                 f"Скинь {TG_NICK} скрин и файл logs/afk_token.log из папки программы, разберёмся."),
            ]),
            ("🌸  О программе", [
                ("Что такое Afk token?",
                 "Бот, который играет в Fortnite вместо тебя: сам заходит в катки, прыгает с автобуса, "
                 "бегает и открывает сундуки, забирает награды и запускает новую катку. И так по кругу, пока "
                 "ты спишь, учишься или работаешь."),
                ("Как он работает?",
                 "Бот смотрит на экран: кнопку «Играть» и сундуки узнаёт по цвету и форме, надписи на "
                 "кнопках читает как текст. Потом жмёт их мышкой и клавиатурой, как обычный "
                 "игрок. В файлы игры он не лезет и ничего не внедряет."),
                ("Чем Free отличается от VIP?",
                 "Free: авто-запуск катки и прыжок с автобуса. VIP: всё остальное, то есть выход и новые катки "
                 "без остановки, «Играть снова», сундуки, награды, перезапуск при вылете, анти-AFK, "
                 f"Telegram. VIP навсегда {self.shop.get('price_vip', '79')} ₽, Premium "
                 f"{self.shop.get('price_premium', '159')} ₽ (вкладка «Магазин»), один ключ на один ПК."),
                ("Обновления",
                 "Программа обновляется сама: при запуске проверяет новую версию, скачивает и "
                 "перезапускается. Ключ и настройки сохраняются."),
                ("Выпадет ли Пиратский магазин?",
                 "Бот катает катки и открывает сундуки за тебя, но шанс выпадения задаёт игра. "
                 "Гарантировать токен не может никто."),
                ("Это безопасно?",
                 "Правила Epic Games запрещают автоматизацию в игре. За AFK-фарм аккаунт могут "
                 "ограничить или заблокировать. Используешь на свой страх и риск."),
            ]),
        ]
        for title, qa in sections:
            ctk.CTkLabel(page, text=title, text_color=ACCENT, font=F(18, True)).pack(anchor="w", pady=(10, 6))
            for q, a in qa:
                self._faq_item(page, q, a)

    def _faq_item(self, page, q, a):
        card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=10)
        card.pack(fill="x", pady=3)
        head = ctk.CTkButton(card, text="＋  " + q, anchor="w", height=42, fg_color="transparent",
                             hover_color=CARD2, text_color=TEXT, font=F(14, True), corner_radius=10)
        head.pack(fill="x")
        body = ctk.CTkLabel(card, text=a, text_color=MUTED, font=F(13), wraplength=760, justify="left")
        opened = {"v": False}

        def toggle():
            opened["v"] = not opened["v"]
            if opened["v"]:
                body.pack(anchor="w", padx=18, pady=(0, 14))
                head.configure(text="－  " + q, text_color=ACCENT)
            else:
                body.pack_forget()
                head.configure(text="＋  " + q, text_color=TEXT)
        head.configure(command=toggle)

    # ================= всплывающие уведомления =================
    def toast(self, text, color=None):
        try:
            t = ctk.CTkFrame(self, fg_color=CARD2, corner_radius=12, border_width=1,
                             border_color=color or ACCENT)
            ctk.CTkLabel(t, text=text, text_color=TEXT, font=F(13), wraplength=360,
                         justify="left").pack(padx=16, pady=10)
            t.place(relx=0.99, rely=0.98, anchor="se")
            t.lift()
            self.after(3500, t.destroy)
        except tk.TclError:
            pass

    # ================= трей и автозапуск =================
    def _init_tray(self):
        if self.tray is not None:
            return
        try:
            import pystray
            from PIL import Image
            img = Image.open(os.path.join(ASSETS, "avatar.png"))
        except Exception:
            self.tray = False
            return

        def ui(fn):
            return lambda icon, item: self.q.put(("cb", lambda _: fn(), None))
        menu = pystray.Menu(
            pystray.MenuItem("Открыть Afk token", ui(self.show_window), default=True),
            pystray.MenuItem(lambda item: "Остановить бота" if self.bot.running else "Запустить бота",
                             ui(lambda: self.stop_bot() if self.bot.running else self.start_bot())),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", ui(self.quit_app)))
        self.tray = pystray.Icon("AfkToken", img, APP_NAME, menu)
        try:
            self.tray.run_detached()
        except Exception:
            self.tray = False

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def quit_app(self):
        self.bot.stop()
        try:
            if self.tray:
                self.tray.stop()
        except Exception:
            pass
        self.destroy()
        os._exit(0)

    @staticmethod
    def autostart_cmd():
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --tray'
        pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pyw):
            pyw = sys.executable
        return f'"{pyw}" "{os.path.abspath(__file__)}" --tray'

    def set_autostart(self, on):
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                               0, winreg.KEY_SET_VALUE)
            if on:
                winreg.SetValueEx(k, "AfkToken", 0, winreg.REG_SZ, self.autostart_cmd())
            else:
                try:
                    winreg.DeleteValue(k, "AfkToken")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(k)
            return True
        except Exception as e:
            self.toast(f"Не удалось изменить автозапуск: {e}", RED)
            return False

    def _settings_card(self, page):
        card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=10)
        card.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(card, text="Программа", text_color=TEXT, font=F(14, True)).pack(anchor="w", padx=16, pady=(14, 6))
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))
        opts = [("autostart", "Запускать вместе с Windows (в трее)"),
                ("autorun_bot", "Сразу запускать бота при старте программы"),
                ("tray_on_close", "Крестик сворачивает в трей, а не закрывает"),
                ("auto_update", "Обновляться автоматически")]
        for i, (key, text) in enumerate(opts):
            v = tk.BooleanVar(value=bool(self.settings.get(key)))

            def cmd(key=key, v=v):
                val = bool(v.get())
                if key == "autostart" and not self.set_autostart(val):
                    v.set(not val)
                    return
                self.settings[key] = val
                save_settings(self.settings)
                self.toast("Сохранено", GREEN)
            ctk.CTkSwitch(grid, text=text, variable=v, command=cmd, progress_color=ACCENT, button_color=TEXT,
                          button_hover_color="#ffffff", fg_color=BORDER, text_color=TEXT,
                          font=F(13)).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 30), pady=5)

    # ================= вкладка: создатель =================
    def build_creator(self):
        page = ctk.CTkFrame(self.content, fg_color=BG)
        self.pages["creator"] = page
        self.page_header(page, "Создатель")
        card = ctk.CTkFrame(page, fg_color=CARD, corner_radius=14)
        card.pack(fill="x")
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=26, pady=26)
        av = asset_img("avatar.png", (96, 96))
        if av:
            ctk.CTkLabel(row, text="", image=av).pack(side="left")
        else:
            ctk.CTkLabel(row, text="K", width=84, height=84, corner_radius=42, fg_color=ACCENT,
                         text_color=BTN_TXT, font=F(36, True)).pack(side="left")
        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", padx=22)
        ctk.CTkLabel(info, text="kk4ose", text_color=TEXT, font=F(26, True)).pack(anchor="w")
        ctk.CTkLabel(info, text=f"Создатель {APP_NAME}", text_color=MUTED, font=F(13)).pack(anchor="w")
        self.link(info, f"Telegram: {TG_NICK}", lic.TG_URL, 15).pack(anchor="w", pady=(8, 0))
        ctk.CTkButton(row, text="Написать в Telegram", height=40, fg_color=ACCENT, hover_color=ACCENT_H,
                      text_color=BTN_TXT, font=F(14, True),
                      command=lambda: webbrowser.open(lic.TG_URL)).pack(side="right")

        for t, d in [("Купить ключ", "Напиши в Telegram и отправь код компьютера из окна активации. "
                                     "Ключ навсегда, один ключ на один компьютер."),
                     ("Поддержка", "Если бот не жмёт какую-то кнопку или игра обновилась, "
                                   "напиши, пришли файл logs/afk_token.log."),
                     ("Версия", f"{APP_NAME} {APP_VERSION}")]:
            c = ctk.CTkFrame(page, fg_color=CARD, corner_radius=10)
            c.pack(fill="x", pady=(10, 0))
            ctk.CTkLabel(c, text=t, text_color=TEXT, font=F(14, True)).pack(anchor="w", padx=18, pady=(12, 0))
            ctk.CTkLabel(c, text=d, text_color=MUTED, font=F(13), wraplength=760,
                         justify="left").pack(anchor="w", padx=18, pady=(2, 12))

    # ================= вкладка: админ =================
    def build_admin(self):
        page = ctk.CTkFrame(self.content, fg_color=BG)
        self.pages["admin"] = page
        h = self.page_header(page, "Админ", "пользователи и ключи")
        ctk.CTkButton(h, text="⟳  Обновить", width=110, height=34, fg_color=CARD2, hover_color=BORDER,
                      text_color=TEXT, font=F(13), command=self._adm_refresh_current).pack(side="right")
        self.adm_mode = ctk.CTkSegmentedButton(
            h, values=["Ключи", "Пользователи"], command=self._adm_switch,
            selected_color=ACCENT_D, selected_hover_color=ACCENT_D, unselected_color=CARD,
            unselected_hover_color=CARD2, fg_color=CARD, text_color=TEXT, font=F(13, True))
        self.adm_mode.set("Ключи")
        self.adm_mode.pack(side="right", padx=12)
        root_page = page
        page = ctk.CTkFrame(root_page, fg_color="transparent")
        page.pack(fill="both", expand=True)
        self.adm_keys_view = page

        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 12))
        self.adm_stats = {}
        for i, (k, t, col) in enumerate([("total", "Всего ключей", TEXT), ("active", "Активировано", ACCENT),
                                         ("online", "Онлайн сейчас", GREEN), ("free", "Свободных", TEXT),
                                         ("banned", "Заблокировано", RED)]):
            c = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=10)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            stats.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(c, text=t, text_color=MUTED, font=F(12)).pack(anchor="w", padx=16, pady=(10, 0))
            lb = ctk.CTkLabel(c, text="—", text_color=col, font=F(22, True))
            lb.pack(anchor="w", padx=16, pady=(0, 10))
            self.adm_stats[k] = lb

        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        self.adm_search = ctk.CTkEntry(bar, width=260, height=34, fg_color=CARD, border_color=BORDER,
                                       text_color=TEXT, font=F(13),
                                       placeholder_text="Поиск: ключ, ПК, заметка, HWID")
        self.adm_search.pack(side="left")
        self.adm_search.bind("<KeyRelease>", lambda e: self.admin_fill())
        self.adm_filter = ctk.CTkSegmentedButton(
            bar, values=["Все", "Активированные", "Онлайн", "Свободные", "Бан"],
            command=lambda v: self.admin_fill(), selected_color=ACCENT_D,
            selected_hover_color=ACCENT_D, unselected_color=CARD, unselected_hover_color=CARD2,
            fg_color=CARD, text_color=TEXT, font=F(12))
        self.adm_filter.set("Все")
        self.adm_filter.pack(side="left", padx=10)

        # таблица
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Afk.Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                        rowheight=30, borderwidth=0, font=(FONT, 10))
        style.configure("Afk.Treeview.Heading", background=SIDEBAR, foreground=MUTED, relief="flat",
                        borderwidth=0, font=(FONT, 10, "bold"))
        style.map("Afk.Treeview", background=[("selected", ACCENT_D)], foreground=[("selected", "#ffffff")])
        style.map("Afk.Treeview.Heading", background=[("active", CARD2)])
        style.layout("Afk.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        tbox = ctk.CTkFrame(page, fg_color=CARD, corner_radius=10)
        tbox.pack(fill="both", expand=True)
        cols = [("key", "Ключ", 200), ("status", "Статус", 110), ("pc", "ПК", 130),
                ("hwid", "Код ПК (HWID)", 160), ("act", "Активирован", 115),
                ("seen", "Последний вход", 115), ("runs", "Запусков", 75), ("ref", "Реф-код", 95), ("note", "Заметка", 160)]
        self.tree = ttk.Treeview(tbox, columns=[c[0] for c in cols], show="headings",
                                 style="Afk.Treeview", selectmode="browse")
        for cid, title, w in cols:
            self.tree.heading(cid, text=title, anchor="w")
            self.tree.column(cid, width=w, anchor="w", stretch=cid in ("note", "pc"))
        self.tree.tag_configure("banned", foreground=RED)
        self.tree.tag_configure("online", foreground=GREEN)
        self.tree.tag_configure("free", foreground=MUTED)
        self.tree.tag_configure("admin", foreground=ACCENT)
        sb = ctk.CTkScrollbar(tbox, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 4), pady=6)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        self.tree.bind("<Double-1>", lambda e: self.adm_copy())

        acts = ctk.CTkFrame(page, fg_color="transparent")
        acts.pack(fill="x", pady=(10, 0))
        acts2 = ctk.CTkFrame(page, fg_color="transparent")
        acts2.pack(fill="x", pady=(8, 0))

        def b(text, cmd, parent=None, main=False, danger=False):
            btn = ctk.CTkButton(parent or acts, text=text, height=34, command=cmd, font=F(12, main),
                                fg_color=ACCENT if main else ("#3a2228" if danger else CARD2),
                                hover_color=ACCENT_H if main else BORDER,
                                text_color=BTN_TXT if main else (RED if danger else TEXT))
            btn.pack(side="left", padx=(0, 8))
            return btn
        # ряд 1 — действия с ключом
        b("Выдать ключ", self.adm_give, main=True)
        b("Создать ключи", self.adm_create)
        b("Ключ на N дней", self.adm_create_timed)
        b("Копировать ключ", self.adm_copy)
        b("Заметка", self.adm_note)
        b("Сбросить ПК", self.adm_reset)
        b("Разблок. шару", self.adm_unlock_share)
        # ряд 2 — блокировки и общее (чтобы «Выпустить обновление» всегда было видно)
        self.adm_ban_btn = b("Заблокировать", self.adm_ban, acts2, danger=True)
        b("Удалить", self.adm_delete, acts2, danger=True)
        b("🛒 Магазин", self.adm_shop, acts2)
        b("⬆ Выпустить обновление", self.adm_release, acts2, main=True)
        self.adm_msg = ctk.CTkLabel(acts, text="", text_color=MUTED, font=F(12))
        self.adm_msg.pack(side="left", padx=8)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._adm_sel_changed())
        self.build_admin_users(root_page)

    def admin_refresh(self):
        self.adm_msg.configure(text="Загрузка...", text_color=MUTED)

        def done(res):
            if isinstance(res, Exception):
                self.adm_msg.configure(text=f"Ошибка: {res}", text_color=RED)
                return
            self.admin_rows = res or []
            self.adm_msg.configure(text=time.strftime("Обновлено %H:%M:%S"), text_color=MUTED)
            self.admin_fill()
        self.bg(lic.admin_list, done)

    @staticmethod
    def _row_status(r):
        if r.get("locked_share"):
            return "🔒 Шара", "banned"
        if r.get("banned"):
            return "Бан", "banned"
        if r.get("expires_at") and minutes_ago(r["expires_at"]) > 0:
            return "Истёк", "free"
        if not r.get("hwid"):
            return (f"Свободен ({r['valid_days']} дн.)" if r.get("valid_days") else "Свободен"), "free"
        if r.get("last_seen") and minutes_ago(r["last_seen"]) <= 12:
            return ("Админ · онлайн" if r.get("is_admin") else "Онлайн"), "online"
        if r.get("is_admin"):
            return "Админ", "admin"
        if r.get("expires_at"):
            return "VIP до " + fmt_time(r["expires_at"])[:5], ""
        return "Активирован", ""

    def admin_fill(self):
        rows = self.admin_rows
        st = {"total": len(rows), "active": 0, "online": 0, "free": 0, "banned": 0}
        for r in rows:
            s, tag = self._row_status(r)
            if r.get("hwid"):
                st["active"] += 1
            else:
                st["free"] += 1
            if tag == "online":
                st["online"] += 1
            if r.get("banned"):
                st["banned"] += 1
        for k, v in st.items():
            self.adm_stats[k].configure(text=str(v))

        q = self.adm_search.get().strip().lower()
        flt = self.adm_filter.get()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            s, tag = self._row_status(r)
            if flt == "Активированные" and not r.get("hwid"):
                continue
            if flt == "Онлайн" and tag != "online":
                continue
            if flt == "Свободные" and (r.get("hwid") or r.get("banned")):
                continue
            if flt == "Бан" and not r.get("banned"):
                continue
            hay = " ".join(str(r.get(k) or "") for k in ("key", "pc_name", "note", "hwid")).lower()
            if q and q not in hay:
                continue
            tr = {"premium": " · Premium", "upgrade": " · Апгрейд", "ultimate": " · Ultimate"}.get(r.get("tier") or "", "")
            self.tree.insert("", "end", iid=r["key"], tags=(tag,), values=(
                r["key"], s + tr, r.get("pc_name") or "—", r.get("hwid") or "—",
                fmt_time(r.get("activated_at")), fmt_time(r.get("last_seen")),
                r.get("launches") or 0, r.get("ref_code") or "", r.get("note") or ""))

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            self.adm_msg.configure(text="Выбери строку в таблице", text_color=YELLOW)
            return None
        return next((r for r in self.admin_rows if r["key"] == sel[0]), None)

    def _adm_sel_changed(self):
        sel = self.tree.selection()
        r = next((x for x in self.admin_rows if sel and x["key"] == sel[0]), None)
        self.adm_ban_btn.configure(text="Разблокировать" if r and r.get("banned") else "Заблокировать")

    def _adm_do(self, key, action, note=None, ok_text="Готово"):
        def done(res):
            if isinstance(res, Exception):
                self.adm_msg.configure(text=f"Ошибка: {res}", text_color=RED)
            else:
                self.adm_msg.configure(text=ok_text, text_color=GREEN)
                self.admin_refresh()
        self.bg(lic.admin_action, done, key, action, note)

    def adm_copy(self):
        r = self._selected()
        if r:
            self.copy(r["key"])
            self.adm_msg.configure(text=f"Скопирован {r['key']}", text_color=GREEN)

    def adm_give(self):
        free = [r for r in self.admin_rows
                if not r.get("hwid") and not r.get("banned") and not r.get("note")]
        if not free:
            self.adm_msg.configure(text="Свободных ключей нет, создай новые", text_color=YELLOW)
            return
        who = ctk.CTkInputDialog(text="Кому выдаёшь ключ? (ник в Telegram)", title="Выдать ключ").get_input()
        if who is None:
            return
        k = free[0]["key"]
        self.copy(k)
        self._adm_do(k, "note", (who.strip() or "выдан") + time.strftime(" · %d.%m.%y"),
                     f"Ключ {k} скопирован, отправь покупателю")

    def adm_create(self):
        win = ctk.CTkToplevel(self)
        win.title("Создать ключи")
        win.geometry("520x300")
        win.configure(fg_color=SIDEBAR)
        win.transient(self)
        win.after(150, win.grab_set)
        ctk.CTkLabel(win, text="Какие ключи создать?", text_color=TEXT, font=F(16, True)).pack(pady=(18, 8))
        seg = ctk.CTkSegmentedButton(win, values=["VIP", "Premium", "Апгрейд VIP→Premium", "Ultimate"],
                                     selected_color=ACCENT_D, selected_hover_color=ACCENT_D, unselected_color=CARD,
                                     unselected_hover_color=CARD2, fg_color=CARD, text_color=TEXT, font=F(12))
        seg.set("VIP")
        seg.pack(padx=16)
        ctk.CTkLabel(win, text="Апгрейд активируется только на ПК, где уже есть VIP навсегда.",
                     text_color=MUTED, font=F(11), wraplength=380).pack(pady=(6, 4))
        ent = ctk.CTkEntry(win, width=120, height=34, fg_color=CARD, border_color=BORDER, text_color=TEXT,
                           font=F(14), justify="center", placeholder_text="кол-во")
        ent.insert(0, "10")
        ent.pack(pady=8)

        def go():
            try:
                n = max(1, min(500, int(ent.get())))
            except ValueError:
                return
            tier = {"VIP": "vip", "Premium": "premium", "Ultimate": "ultimate"}.get(seg.get(), "upgrade")
            win.destroy()
            self._adm_create_keys(n, tier)
        ctk.CTkButton(win, text="Создать", height=36, fg_color=ACCENT, hover_color=ACCENT_H, text_color=BTN_TXT,
                      font=F(13, True), command=go).pack(pady=8)

    def _adm_create_keys(self, n, tier):
        keys = list({lic.new_key() for _ in range(n)})

        def done(res):
            if isinstance(res, Exception):
                self.adm_msg.configure(text=f"Ошибка: {res}", text_color=RED)
                return
            path = os.path.join(lic.app_dir(), time.strftime(f"new_keys_{tier}_%Y%m%d_%H%M%S.txt"))
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(keys) + "\n")
            except Exception:
                pass
            self.copy("\n".join(keys))
            self.adm_msg.configure(text=f"Создано {res}, скопированы и сохранены в {os.path.basename(path)}",
                                   text_color=GREEN)
            self.admin_refresh()
        names = {"vip": "VIP", "premium": "Premium", "upgrade": "Апгрейд", "ultimate": "Ultimate"}
        self.bg(lic.admin_add_tier, done, keys, tier, names[tier])

    def adm_create_timed(self):
        d = ctk.CTkInputDialog(text="На сколько дней VIP? (ключ начнёт отсчёт с активации)",
                               title="Ключ на время").get_input()
        try:
            d = max(1, min(365, int(d)))
        except (TypeError, ValueError):
            return
        k = lic.new_key()

        def done(res):
            if isinstance(res, Exception):
                self.adm_msg.configure(text=f"Ошибка: {res}", text_color=RED)
                return
            self.copy(k)
            self.adm_msg.configure(text=f"Ключ на {d} дн. скопирован: {k}", text_color=GREEN)
            self.admin_refresh()
        self.bg(lic.admin_add_timed, done, k, d, f"VIP на {d} дн.")

    def adm_note(self):
        r = self._selected()
        if not r:
            return
        t = ctk.CTkInputDialog(text=f"Заметка для {r['key']}\n(сейчас: {r.get('note') or 'нет'})",
                               title="Заметка").get_input()
        if t is not None:
            self._adm_do(r["key"], "note", t.strip(), "Заметка сохранена")

    def adm_reset(self):
        r = self._selected()
        if r and messagebox.askyesno(APP_NAME, f"Отвязать {r['key']} от компьютера?\n"
                                               "Его можно будет активировать на другом ПК."):
            self._adm_do(r["key"], "reset_hwid", None, "Привязка сброшена")

    def adm_unlock_share(self):
        r = self._selected()
        if not r:
            return

        def done(res):
            if isinstance(res, Exception):
                self.adm_msg.configure(text=f"Ошибка: {res}", text_color=RED)
            else:
                self.adm_msg.configure(text="Блокировка за расшаривание снята", text_color=GREEN)
                self.admin_refresh()
        self.bg(lic.admin_unlock_share, done, r["key"])

    def adm_ban(self):
        r = self._selected()
        if not r:
            return
        if r.get("banned"):
            self._adm_do(r["key"], "unban", None, "Разблокирован")
        elif messagebox.askyesno(APP_NAME, f"Заблокировать {r['key']}?"):
            self._adm_do(r["key"], "ban", None, "Заблокирован")

    def adm_delete(self):
        r = self._selected()
        if r and messagebox.askyesno(APP_NAME, f"Удалить ключ {r['key']} навсегда?"):
            self._adm_do(r["key"], "delete", None, "Удалён")

    # ================= админ: все пользователи (и бесплатные) =================
    def _adm_switch(self, v):
        if v == "Пользователи":
            self.adm_keys_view.pack_forget()
            self.adm_users_view.pack(fill="both", expand=True)
            if not self.user_rows:
                self.users_refresh()
        else:
            self.adm_users_view.pack_forget()
            self.adm_keys_view.pack(fill="both", expand=True)

    def _adm_refresh_current(self):
        if self.adm_mode.get() == "Пользователи":
            self.users_refresh()
        else:
            self.admin_refresh()

    def build_admin_users(self, root):
        page = ctk.CTkFrame(root, fg_color="transparent")
        self.adm_users_view = page

        stats = ctk.CTkFrame(page, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 12))
        self.usr_stats = {}
        for i, (k, t, col) in enumerate([("total", "Всего юзеров", TEXT), ("free", "Бесплатных", TEXT),
                                         ("vip", "VIP", ACCENT), ("online", "Онлайн сейчас", GREEN),
                                         ("running", "Бот работает", GREEN), ("new", "Новых за 24ч", YELLOW)]):
            c = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=10)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            stats.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(c, text=t, text_color=MUTED, font=F(12)).pack(anchor="w", padx=16, pady=(10, 0))
            lb = ctk.CTkLabel(c, text="—", text_color=col, font=F(22, True))
            lb.pack(anchor="w", padx=16, pady=(0, 10))
            self.usr_stats[k] = lb

        bar = ctk.CTkFrame(page, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 8))
        self.usr_search = ctk.CTkEntry(bar, width=260, height=34, fg_color=CARD, border_color=BORDER,
                                       text_color=TEXT, font=F(13),
                                       placeholder_text="Поиск: ник, ПК, HWID, ключ")
        self.usr_search.pack(side="left")
        self.usr_search.bind("<KeyRelease>", lambda e: self.users_fill())
        self.usr_filter = ctk.CTkSegmentedButton(
            bar, values=["Все", "Бесплатные", "VIP", "Онлайн", "Мут"],
            command=lambda v: self.users_fill(), selected_color=ACCENT_D,
            selected_hover_color=ACCENT_D, unselected_color=CARD, unselected_hover_color=CARD2,
            fg_color=CARD, text_color=TEXT, font=F(12))
        self.usr_filter.set("Все")
        self.usr_filter.pack(side="left", padx=10)

        tbox = ctk.CTkFrame(page, fg_color=CARD, corner_radius=10)
        tbox.pack(fill="both", expand=True)
        cols = [("nick", "Ник в чате", 130), ("ed", "Версия", 95), ("status", "Статус", 140),
                ("pc", "ПК", 130), ("ver", "Прога", 55), ("first", "Первый запуск", 115),
                ("seen", "Последний раз", 115), ("runs", "Запусков", 70), ("msgs", "Сообщ.", 60),
                ("hwid", "Код ПК (HWID)", 160), ("key", "Ключ", 190)]
        self.utree = ttk.Treeview(tbox, columns=[c[0] for c in cols], show="headings",
                                  style="Afk.Treeview", selectmode="browse")
        for cid, title, w in cols:
            self.utree.heading(cid, text=title, anchor="w")
            self.utree.column(cid, width=w, anchor="w", stretch=cid in ("pc", "key"))
        self.utree.tag_configure("online", foreground=GREEN)
        self.utree.tag_configure("vip", foreground=ACCENT)
        self.utree.tag_configure("muted", foreground=RED)
        self.utree.tag_configure("off", foreground=MUTED)
        sb = ctk.CTkScrollbar(tbox, command=self.utree.yview)
        self.utree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 4), pady=6)
        self.utree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        self.utree.bind("<Double-1>", lambda e: self.usr_copy())
        self.utree.bind("<<TreeviewSelect>>", lambda e: self._usr_sel_changed())

        acts = ctk.CTkFrame(page, fg_color="transparent")
        acts.pack(fill="x", pady=(10, 0))

        def b(text, cmd, danger=False):
            btn = ctk.CTkButton(acts, text=text, height=34, command=cmd, font=F(12),
                                fg_color="#3a2228" if danger else CARD2, hover_color=BORDER,
                                text_color=RED if danger else TEXT)
            btn.pack(side="left", padx=(0, 8))
            return btn
        b("Копировать HWID", self.usr_copy)
        self.usr_mute_btn = b("Мут в чате", self.usr_mute, danger=True)
        b("Сбросить ник", lambda: self._usr_do("reset_nick", "Ник сброшен"))
        b("Удалить его сообщения", lambda: self._usr_do("wipe_user", "Сообщения удалены", True), danger=True)
        b("Очистить весь чат", self.usr_clear_chat, danger=True)
        self.usr_msg = ctk.CTkLabel(acts, text="Бесплатные появляются тут после обновления до 1.3",
                                    text_color=MUTED, font=F(12))
        self.usr_msg.pack(side="left", padx=8)

    def users_refresh(self):
        self.usr_msg.configure(text="Загрузка...", text_color=MUTED)

        def done(res):
            if isinstance(res, Exception):
                self.usr_msg.configure(text=f"Ошибка: {res}", text_color=RED)
                return
            self.user_rows = res or []
            self.usr_msg.configure(text=time.strftime("Обновлено %H:%M:%S"), text_color=MUTED)
            self.users_fill()
        self.bg(lic.admin_users, done)

    @staticmethod
    def _usr_status(r):
        online = r.get("last_seen") and minutes_ago(r["last_seen"]) <= 12
        if online and r.get("bot_running"):
            st = "Онлайн · бот работает"
        elif online:
            st = "Онлайн"
        else:
            m = minutes_ago(r.get("last_seen"))
            if not r.get("last_seen") or m >= 1e8:
                st = "—"
            else:
                st = (f"был {int(m // 60)} ч назад" if m < 1440 else f"был {int(m // 1440)} дн назад")
        if r.get("chat_banned"):
            tag = "muted"
        elif online:
            tag = "online"
        elif r.get("edition") in ("vip", "admin", "premium", "ultimate"):
            tag = "vip"
        else:
            tag = "off"
        return st, tag, bool(online)

    def users_fill(self):
        rows = self.user_rows
        st = {"total": len(rows), "free": 0, "vip": 0, "online": 0, "running": 0, "new": 0}
        for r in rows:
            _, _, online = self._usr_status(r)
            if r.get("edition") in ("vip", "admin", "premium", "ultimate"):
                st["vip"] += 1
            else:
                st["free"] += 1
            if online:
                st["online"] += 1
                if r.get("bot_running"):
                    st["running"] += 1
            if minutes_ago(r.get("first_seen")) <= 1440:
                st["new"] += 1
        for k, v in st.items():
            self.usr_stats[k].configure(text=str(v))

        q = self.usr_search.get().strip().lower()
        flt = self.usr_filter.get()
        eds = {"free": "Бесплатная", "vip": "VIP ★", "premium": "Premium ♛", "ultimate": "Ultimate ⚡", "admin": "Админ"}
        self.utree.delete(*self.utree.get_children())
        for r in rows:
            s, tag, online = self._usr_status(r)
            ed = r.get("edition") or "free"
            if flt == "Бесплатные" and ed != "free":
                continue
            if flt == "VIP" and ed == "free":
                continue
            if flt == "Онлайн" and not online:
                continue
            if flt == "Мут" and not r.get("chat_banned"):
                continue
            hay = " ".join(str(r.get(k) or "") for k in ("nick", "pc_name", "hwid", "vip_key")).lower()
            if q and q not in hay:
                continue
            self.utree.insert("", "end", iid=r["hwid"], tags=(tag,), values=(
                (r.get("nick") or "—") + ("  🔇" if r.get("chat_banned") else ""),
                eds.get(ed, ed), s, r.get("pc_name") or "—", r.get("app_version") or "—",
                fmt_time(r.get("first_seen")), fmt_time(r.get("last_seen")),
                r.get("launches") or 0, r.get("msgs") or 0, r["hwid"], r.get("vip_key") or ""))

    def _usr_selected(self):
        sel = self.utree.selection()
        if not sel:
            self.usr_msg.configure(text="Выбери строку в таблице", text_color=YELLOW)
            return None
        return next((r for r in self.user_rows if r["hwid"] == sel[0]), None)

    def _usr_sel_changed(self):
        sel = self.utree.selection()
        r = next((x for x in self.user_rows if sel and x["hwid"] == sel[0]), None)
        self.usr_mute_btn.configure(text="Размут в чате" if r and r.get("chat_banned") else "Мут в чате")

    def usr_copy(self):
        r = self._usr_selected()
        if r:
            self.copy(r["hwid"])
            self.usr_msg.configure(text=f"Скопирован {r['hwid']}", text_color=GREEN)

    def _usr_do(self, action, ok_text, confirm=False):
        r = self._usr_selected()
        if not r:
            return
        if confirm and not messagebox.askyesno(APP_NAME, f"{ok_text}? ({r.get('nick') or r['hwid']})"):
            return

        def done(res):
            if isinstance(res, Exception):
                self.usr_msg.configure(text=f"Ошибка: {res}", text_color=RED)
            else:
                self.usr_msg.configure(text=ok_text, text_color=GREEN)
                self.users_refresh()
                self._chat_reload()
        self.bg(lic.admin_chat, done, action, None, r["hwid"])

    def usr_mute(self):
        r = self._usr_selected()
        if r:
            if r.get("chat_banned"):
                self._usr_do("unmute", "Размучен")
            else:
                self._usr_do("mute", "Замучен в чате", True)

    def usr_clear_chat(self):
        if not messagebox.askyesno(APP_NAME, "Удалить ВСЕ сообщения в чате у всех?"):
            return

        def done(res):
            self.usr_msg.configure(text=f"Ошибка: {res}" if isinstance(res, Exception) else "Чат очищен",
                                   text_color=RED if isinstance(res, Exception) else GREEN)
            self._chat_reload()
        self.bg(lic.admin_chat, done, "clear")

    # ================= онлайн-отметка (для админки) =================
    def _start_user_ping(self):
        if self._ping_started or not lic.configured():
            return
        self._ping_started = True
        self.after(1500, lambda: self._user_ping(True))

    def _user_ping(self, start=False):
        def done(res):
            if isinstance(res, dict):
                if res.get("nick") and not self.chat_nick and not self._nick_editing:
                    self.chat_nick = res["nick"]
                    self._chat_update_input()
                self.chat_muted = bool(res.get("muted"))
            self.after(5 * 60 * 1000, self._user_ping)
        self.bg(lic.ping, done, start, bool(self.bot.running))

    # ================= вкладка: чат =================
    def build_chat(self):
        page = ctk.CTkFrame(self.content, fg_color=BG)
        self.pages["chat"] = page
        h = self.page_header(page, "Чат", "все, у кого стоит Afk token")
        self.chat_online_lb = ctk.CTkLabel(h, text="", text_color=GREEN, font=F(13, True))
        self.chat_online_lb.pack(side="right")
        nk = ctk.CTkLabel(h, text="сменить ник", text_color=MUTED, font=F(12), cursor="hand2")
        nk.bind("<Button-1>", lambda e: self.chat_change_nick())
        nk.pack(side="right", padx=16)

        box = ctk.CTkFrame(page, fg_color=CARD, corner_radius=12)
        box.pack(fill="both", expand=True)
        self.chat_box = ctk.CTkTextbox(box, fg_color=CARD, text_color=TEXT, font=F(14), wrap="word",
                                       activate_scrollbars=True, border_width=0)
        self.chat_box.pack(fill="both", expand=True, padx=10, pady=10)
        tb = self.chat_box
        tb.tag_config("time", foreground="#7e6f8e")
        tb.tag_config("n_free", foreground="#c9b8e8")
        tb.tag_config("n_vip", foreground=ACCENT)
        tb.tag_config("n_admin", foreground=YELLOW)
        tb.tag_config("n_prem", foreground=GOLD)
        tb.tag_config("n_me", foreground=GREEN)
        tb.tag_config("txt", foreground=TEXT)
        tb.tag_config("sys", foreground=MUTED)
        tb.configure(state="disabled")
        tb._textbox.bind("<Button-3>", self._chat_menu)

        row = ctk.CTkFrame(page, fg_color="transparent")
        row.pack(fill="x", pady=(10, 0))
        self.chat_entry = ctk.CTkEntry(row, height=42, fg_color=CARD, border_color=BORDER,
                                       text_color=TEXT, font=F(14))
        self.chat_entry.pack(side="left", fill="x", expand=True)
        self.chat_entry.bind("<Return>", lambda e: self.chat_submit())
        self.chat_btn = ctk.CTkButton(row, text="Отправить", width=130, height=42, fg_color=ACCENT,
                                      hover_color=ACCENT_H, text_color=BTN_TXT, font=F(14, True),
                                      command=self.chat_submit)
        self.chat_btn.pack(side="left", padx=(10, 0))
        self.chat_err = ctk.CTkLabel(page, text="Без ссылок, рекламы и оскорблений, за это мут. "
                                               "ПКМ по сообщению, чтобы скопировать.",
                                     text_color=MUTED, font=F(11))
        self.chat_err.pack(anchor="w", pady=(4, 0))
        self._chat_update_input()
        self._chat_render(scroll=True)
        if self.chat_online:
            self.chat_online_lb.configure(text=f"●  онлайн: {self.chat_online}")

    def _chat_update_input(self):
        if not hasattr(self, "chat_entry"):
            return
        try:
            if not lic.configured():
                self.chat_entry.configure(placeholder_text="Чат недоступен: сервер не настроен")
                self.chat_btn.configure(state="disabled")
            elif self.chat_muted:
                self.chat_entry.configure(placeholder_text="Ты в муте, писать нельзя")
                self.chat_btn.configure(state="disabled", text="Мут")
            elif not self.chat_nick:
                self.chat_entry.configure(placeholder_text="Придумай ник для чата (3–20 символов) и нажми Enter")
                self.chat_btn.configure(state="normal", text="Сохранить ник")
            else:
                self.chat_entry.configure(placeholder_text=f"Сообщение от {self.chat_nick}...")
                self.chat_btn.configure(state="normal", text="Отправить")
        except Exception:
            pass

    def _chat_set_err(self, text, color=RED):
        try:
            self.chat_err.configure(text=text, text_color=color)
        except Exception:
            pass

    def chat_change_nick(self):
        self._nick_editing = True
        self.chat_nick = None
        self._chat_update_input()
        self.chat_entry.delete(0, "end")
        self.chat_entry.focus_set()

    def chat_submit(self):
        text = self.chat_entry.get().strip()
        if not text or self.chat_muted:
            return
        if not self.chat_nick:
            def done_nick(res):
                if isinstance(res, Exception):
                    self._chat_set_err(f"Ошибка: {res}")
                elif res.get("ok"):
                    self.chat_nick = res["nick"]
                    self._nick_editing = False
                    self.chat_entry.delete(0, "end")
                    self._chat_set_err(f"Готово! Твой ник: {self.chat_nick}", GREEN)
                    self._chat_update_input()
                else:
                    self._chat_set_err(res.get("error", "Ошибка"))
            self.bg(lic.chat_set_nick, done_nick, text)
            return
        if len(text) > 300:
            self._chat_set_err("Максимум 300 символов")
            return
        self.chat_btn.configure(state="disabled")

        def done(res):
            self.chat_btn.configure(state="normal")
            if isinstance(res, Exception):
                self._chat_set_err("Нет связи с сервером" if isinstance(res, lic.NetworkError) else f"Ошибка: {res}")
            elif res.get("ok"):
                self.chat_entry.delete(0, "end")
                self._chat_set_err("")
                self._chat_tick(force=True, scroll=True)
            else:
                e = res.get("error", "Ошибка")
                self._chat_set_err(e)
                if "мут" in e.lower():
                    self.chat_muted = True
                    self._chat_update_input()
                elif "ник" in e.lower():
                    self.chat_nick = None
                    self._chat_update_input()
        self.bg(lic.chat_send, done, text)

    # --- загрузка сообщений ---
    def _start_chat_loop(self):
        if self._chat_loop_started or not lic.configured():
            return
        self._chat_loop_started = True
        self.after(2500, self._chat_loop)

    def _chat_loop(self):
        visible = self.cur_page == "chat" and self.state() != "withdrawn"
        self._chat_tick()
        self.after(3000 if visible else 45000, self._chat_loop)

    def _chat_reload(self):
        self.chat_msgs = []
        self.chat_last_id = 0
        self._chat_render()
        self._chat_tick(force=True, scroll=True)

    def _chat_tick(self, force=False, scroll=False):
        if self._chat_busy and not force:
            return
        self._chat_busy = True
        first = self.chat_last_id == 0

        def done(res):
            self._chat_busy = False
            if isinstance(res, Exception) or not isinstance(res, dict):
                return
            self.chat_online = res.get("online") or 0
            try:
                self.chat_online_lb.configure(text=f"●  онлайн: {self.chat_online}")
            except Exception:
                pass
            nick, muted = res.get("nick"), bool(res.get("muted"))
            if (nick and nick != self.chat_nick and not self._nick_editing) or muted != self.chat_muted:
                if nick and not self._nick_editing:
                    self.chat_nick = nick
                self.chat_muted = muted
                self._chat_update_input()
            changed = False
            dels = set(res.get("deleted") or [])
            if dels and any(m["id"] in dels for m in self.chat_msgs):
                self.chat_msgs = [m for m in self.chat_msgs if m["id"] not in dels]
                changed = True
            new = [m for m in (res.get("msgs") or []) if m["id"] > self.chat_last_id and m["id"] not in dels]
            if new:
                self.chat_msgs.extend(new)
                self.chat_msgs = self.chat_msgs[-200:]
                self.chat_last_id = max(m["id"] for m in new)
                changed = True
                if not first and self.cur_page != "chat":
                    self.chat_unread += sum(1 for m in new if not m.get("mine"))
                    self._chat_nav_badge()
            if changed:
                self._chat_render(scroll=scroll or first)
        self.bg(lic.chat_fetch, done, self.chat_last_id)

    def _chat_nav_badge(self):
        b = getattr(self, "nav_buttons", {}).get("chat")
        if b:
            try:
                b.configure(text="✉   Чат" + (f"   ({min(self.chat_unread, 99)})" if self.chat_unread else ""))
            except Exception:
                pass

    def _chat_render(self, scroll=False):
        tb = getattr(self, "chat_box", None)
        if tb is None:
            return
        try:
            at_bottom = tb._textbox.yview()[1] >= 0.98
            tb.configure(state="normal")
            tb.delete("1.0", "end")
            if not self.chat_msgs:
                tb.insert("end", "Тут пока пусто. Напиши первым 🌸\n" if lic.configured()
                          else "Чат недоступен.\n", ("sys",))
            last_day = None
            for m in self.chat_msgs:
                try:
                    dt = datetime.fromisoformat(m["at"].replace("Z", "+00:00")).astimezone()
                except Exception:
                    dt = datetime.now()
                day = dt.strftime("%d.%m")
                if day != last_day:
                    last_day = day
                    tb.insert("end", f"— {day} —\n", ("sys",))
                tag = f"m{m['id']}"
                badge = m.get("badge") or "free"
                ntag = "n_me" if m.get("mine") else {"vip": "n_vip", "admin": "n_admin",
                                                     "premium": "n_prem", "ultimate": "n_prem"}.get(badge, "n_free")
                mark = {"vip": "★ ", "admin": "⚙ ", "premium": "♛ ", "ultimate": "⚡ "}.get(badge, "")
                tb.insert("end", dt.strftime("%H:%M  "), ("time", tag))
                tb.insert("end", mark + m["nick"], (ntag, tag))
                tb.insert("end", ":  " + m["text"] + "\n", ("txt", tag))
            tb.configure(state="disabled")
            if scroll or at_bottom:
                tb.see("end")
        except Exception:
            pass

    def _chat_menu(self, event):
        tb = self.chat_box._textbox
        idx = tb.index(f"@{event.x},{event.y}")
        mid = next((int(t[1:]) for t in tb.tag_names(idx) if t.startswith("m") and t[1:].isdigit()), None)
        if mid is None:
            return
        m = next((x for x in self.chat_msgs if x["id"] == mid), None)
        if not m:
            return
        menu = tk.Menu(self, tearoff=0, bg=CARD2, fg=TEXT, activebackground=ACCENT_D,
                       activeforeground="#ffffff", bd=0)
        menu.add_command(label="Копировать текст", command=lambda: self.copy(m["text"]))
        menu.add_command(label="Ответить", command=lambda: (
            self.chat_entry.delete(0, "end"), self.chat_entry.insert(0, f"{m['nick']}, "),
            self.chat_entry.focus_set()))
        if self.is_admin:
            menu.add_separator()
            menu.add_command(label="Удалить сообщение", command=lambda: self._chat_admin("delete", mid))
            menu.add_command(label=f"Мут {m['nick']}", command=lambda: self._chat_admin("mute", mid))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _chat_admin(self, action, mid):
        if action == "mute" and not messagebox.askyesno(APP_NAME, "Замутить автора в чате?"):
            return

        def done(res):
            if isinstance(res, Exception):
                self._chat_set_err(f"Ошибка: {res}")
                return
            self._chat_set_err("Удалено" if action == "delete" else "Автор замучен", GREEN)
            if action == "delete":
                self.chat_msgs = [x for x in self.chat_msgs if x["id"] != mid]
                self._chat_render()
        self.bg(lic.admin_chat, done, action, mid)

    # ================= уровни / магазин =================
    def _allowed(self, key):
        if key in bot_core.FREE_FEATURES:
            return True
        if key in bot_core.ULTIMATE_FEATURES:
            return self.tier == "ultimate"
        if key in bot_core.PREMIUM_FEATURES:
            return self.tier in PREM
        return self.vip

    def _side_shop_text(self):
        if self.tier == "premium":
            return f"⚡  Ultimate за {self.shop.get('price_ultimate', '249')} ₽"
        if self.tier == "vip" and not self.vip_until:
            return f"♛  Premium за {self.shop.get('price_upgrade', '99')} ₽"
        if self.tier == "vip":
            return "★  VIP навсегда"
        return "♛  Premium и Ultimate"

    def _on_shop_cfg(self, cfg):
        if isinstance(cfg, dict):
            self.shop.update(cfg)
        try:
            if self.side_shop_btn is not None:
                self.side_shop_btn.configure(text=self._side_shop_text())
            if "shop" in self.pages:
                cur = self.cur_page
                self.pages["shop"].destroy()
                self.build_shop()
                if cur == "shop":
                    self.show_page("shop")
        except Exception:
            pass

    def open_shop_url(self, what):
        url = self.shop.get(f"url_{what}") or ""
        if not url.startswith("http"):
            url = lic.TG_URL
            self.toast(f"Пиши {TG_NICK}, он продаст ключ", YELLOW)
        webbrowser.open(url)

    def _grid(self, parent):
        g = ctk.CTkFrame(parent, fg_color="transparent")
        g.pack(fill="x")
        g.grid_columnconfigure((0, 1), weight=1, uniform="c")
        return g

    def _tab_banner(self, parent, title, sub, button, gold=False):
        b = ctk.CTkFrame(parent, fg_color="#3a2a12" if gold else ACCENT_D, corner_radius=12,
                         border_width=2 if gold else 0, border_color=GOLD)
        b.pack(fill="x", pady=(0, 8))
        row = ctk.CTkFrame(b, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=16)
        txt = ctk.CTkFrame(row, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(txt, text=title, text_color=GOLD if gold else TEXT, font=F(22 if gold else 18, True),
                     justify="left").pack(anchor="w")
        ctk.CTkLabel(txt, text=sub, text_color="#f1e6d2" if gold else "#e9dcf7", font=F(13), wraplength=620,
                     justify="left").pack(anchor="w", pady=(4, 0))
        if button:
            label, what = button
            ctk.CTkButton(row, text=label, height=42, width=230, corner_radius=10,
                          fg_color=GOLD if gold else ACCENT, hover_color=ACCENT_H,
                          text_color="#2b1f06" if gold else BTN_TXT, font=F(14, True),
                          command=lambda: self.show_page("shop")).pack(side="right", padx=(12, 0))
        return b

    def _func_tab_switch(self, label):
        self._ftab = label
        try:
            self.ftab_seg.set(label)
        except Exception:
            pass
        name = ("ultimate" if "Ultimate" in label else "free" if "Free" in label
                else "vip" if "VIP" in label else "premium")
        for n, fr in self.ftabs.items():
            fr.pack_forget()
        self.ftabs[name].pack(fill="x")
        if name == "premium":
            self.after(50, self._draw_chart)

    # ---------- вкладка Ultimate ----------
    def build_ultimate_tab(self, fr):
        pl = self.shop.get("price_ultimate", "249")
        if self.tier == "ultimate":
            self._tab_banner(fr, "⚡ Ultimate активен", "Все функции Ultimate открыты. Спасибо за поддержку 💙",
                             None, gold=True)
        else:
            self._tab_banner(fr, f"⚡ Ultimate за {pl} ₽",
                             "Всё из Premium + умный бег: обходит препятствия, крутит мышью как живой игрок, "
                             "уходит от зоны и выходит из катки, если остался один.",
                             (f"⚡  Ultimate за {pl} ₽", "ultimate"), gold=True)
        g = self._grid(fr)
        cards = [
            ("obstacle_nav", "Обход препятствий",
             "Бот больше не застревает: упёрся — перепрыгивает, не вышло — прыгает в сторону, "
             "совсем тупик — разворачивается и обходит.", None),
            ("smooth_mouse", "Плавные движения мышкой",
             "Камера поворачивается как у живого игрока: с разгоном, торможением и лёгкой дугой, "
             "а не одним резким рывком.", None),
            ("zone_nav", "Уход от зоны",
             "Читает компас и миникарту, держит курс в безопасную сторону и не лезет в воду. "
             "Поворот камеры калибрует сам в первые секунды катки. Шторм определяет по цвету "
             "миникарты; если бот бегает странно, выключи шторм ниже.",
             ("storm_nav", {"Шторм: выкл": False, "Шторм: вкл": True})),
            ("auto_leave", "Выход после смерти команды",
             "Выходит, когда вся команда погибла или матч закончился. Если матч завис, выйдет через ESC.",
             ("max_match_min", "Выход через ESC после, мин", 10, 120)),
            ("land_mode", "Точка высадки",
             "Прыгает в начале, середине или конце маршрута автобуса. В конце меньше людей.",
             ("land_spot", {"Начало": "start", "Середина": "mid", "Конец": "end", "Рандом": "random"})),
            ("sprint", "Спринт и живые движения",
             "Иногда зажимает Shift, стрейфит и меняет направление, бегает как игрок.", None),
            ("low_gfx", "Низкая графика на время фарма",
             "Ставит минимальную графику, ПК тише и холоднее. Потом всё вернёт как было.", None),
            ("team_check", "Выход, если остался один",
             "Смотрит на панель команды. Тиммейты выбыли или их не было с начала — выходит и ищет "
             "новую катку, а не стоит один. Выбили тебя, а свои живы — ждёт их. В соло не работает.", None),
        ]
        for i, (key, title, desc, num) in enumerate(cards):
            self._func_card(g, i // 2, i % 2, key, title, desc, num)
        # ИИ-сундуки: пока недоступно
        soon = ctk.CTkFrame(g, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)
        soon.grid(row=(len(cards) + 1) // 2, column=0, columnspan=2, sticky="nsew", pady=6)
        top = ctk.CTkFrame(soon, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(top, text="🧠  Открытие сундуков через ИИ", text_color=MUTED, font=F(14, True)).pack(side="left")
        ctk.CTkLabel(top, text=" СКОРО ", fg_color=ULTRA, text_color="#06212b", corner_radius=6,
                     font=F(11, True), height=20).pack(side="left", padx=8)
        sw = ctk.CTkSwitch(top, text="", width=46, progress_color=ULTRA, button_color=TEXT, fg_color=BORDER)
        sw.pack(side="right")
        sw.configure(state="disabled")
        ctk.CTkLabel(soon, text="Нейросеть будет сама видеть сундуки на экране и вести к ним бота. "
                                "Пока недоступно — появится в одном из следующих обновлений, владельцам "
                                "Ultimate включится без доплаты.",
                     text_color=MUTED, font=F(12), wraplength=820, justify="left").pack(anchor="w", padx=16, pady=(0, 14))

    # ---------- вкладка Premium ----------
    def build_premium_tab(self, fr):
        pu, pp = self.shop.get("price_upgrade", "99"), self.shop.get("price_premium", "159")
        if self.tier in PREM:
            self._tab_banner(fr, "♛ Premium активен", "Все 10 функций открыты. Спасибо за поддержку 💛", None,
                             gold=True)
        elif self.tier == "vip" and not self.vip_until:
            self._tab_banner(fr, f"🏴‍☠️ Получи токен всего за {pu} ₽",
                             "У тебя VIP, поэтому апгрейд до Premium со скидкой. Расписание, фарм до цели, пульт с "
                             "телефона, точка высадки и ещё 6 функций.", (f"♛  Обновиться за {pu} ₽", "upgrade"),
                             gold=True)
        else:
            self._tab_banner(fr, f"🏴‍☠️ Получи токен всего за {pp} ₽",
                             "Premium = всё из VIP + 10 функций: бот фармит по расписанию и до цели, "
                             "управляется с телефона и прыгает в лучшую точку.",
                             (f"♛  Premium за {pp} ₽", "premium"), gold=True)
        g = self._grid(fr)
        L = self.tier not in PREM
        P = PREMIUM_LIST

        def b_tg(card, locked):
            self._num_row(card, "shot_every", "Авто-скрин экрана раз в, мин (0 = выкл)", 0, 240, locked)
            ctk.CTkLabel(card, text="Нужен подключённый Telegram (вкладка VIP). Напиши боту /menu.",
                         text_color=MUTED, font=F(11)).pack(anchor="w", padx=16, pady=(0, 10))

        def b_goal(card, locked):
            self._seg_row(card, "goal_type", {"Каток": "matches", "Наград": "rewards", "Сундуков": "chests",
                                              "Токен 🏴‍☠️": "token"}, locked)
            self._num_row(card, "goal_value", "Сколько (для токена 1)", 1, 9999, locked)
            self._seg_row(card, "goal_action", {"Остановить бота": "stop", "Закрыть игру": "close",
                                                "Выключить ПК": "shutdown"}, locked)
            self.goal_lb = ctk.CTkLabel(card, text="", text_color=ACCENT, font=F(12, True))
            self.goal_lb.pack(anchor="w", padx=16, pady=(0, 12))

        def b_stats(card, locked):
            self.chart = tk.Canvas(card, height=150, bg=CARD, highlightthickness=0)
            self.chart.pack(fill="x", padx=16, pady=(0, 6))
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(0, 12))
            self.chart_sum = ctk.CTkLabel(row, text="", text_color=MUTED, font=F(12))
            self.chart_sum.pack(side="left")
            bt = ctk.CTkButton(row, text="📤 Отчёт в Telegram", height=30, width=150, fg_color=CARD2,
                               hover_color=BORDER, text_color=TEXT, font=F(12), command=self.send_week_report)
            bt.pack(side="right")
            if locked:
                bt.configure(state="disabled")

        def b_sched(card, locked):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(0, 6))
            for key, lb in (("sched_from", "С"), ("sched_to", "до")):
                ctk.CTkLabel(row, text=lb, text_color=MUTED, font=F(12)).pack(side="left", padx=(0, 6))
                e = ctk.CTkEntry(row, width=70, height=28, fg_color=CARD2, border_color=BORDER, text_color=TEXT,
                                 font=F(13), justify="center")
                e.insert(0, self.settings.get(key, "23:00"))
                e.pack(side="left", padx=(0, 12))

                def ap(*_, e=e, key=key):
                    v = e.get().strip().replace(".", ":")
                    try:
                        hh, mm = [int(x) for x in v.split(":")]
                        assert 0 <= hh < 24 and 0 <= mm < 60
                        v = f"{hh:02d}:{mm:02d}"
                    except Exception:
                        v = self.settings.get(key, "23:00")
                    e.delete(0, "end")
                    e.insert(0, v)
                    self.settings[key] = v
                    save_settings(self.settings)
                e.bind("<Return>", ap)
                e.bind("<FocusOut>", ap)
                if locked:
                    e.configure(state="disabled")
            days = ctk.CTkFrame(card, fg_color="transparent")
            days.pack(fill="x", padx=16, pady=(0, 12))
            for i, dn in enumerate(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"], 1):
                v = tk.BooleanVar(value=str(i) in str(self.settings.get("sched_days", "1234567")))

                def tog(i=i, v=v):
                    cur = set(str(self.settings.get("sched_days", "1234567")))
                    (cur.add if v.get() else cur.discard)(str(i))
                    self.settings["sched_days"] = "".join(sorted(cur))
                    save_settings(self.settings)
                cb = ctk.CTkCheckBox(days, text=dn, variable=v, command=tog, width=52, checkbox_width=18,
                                     checkbox_height=18, fg_color=ACCENT, hover_color=ACCENT_H, text_color=TEXT,
                                     font=F(11))
                cb.pack(side="left")
                if locked:
                    cb.configure(state="disabled")

        def b_land(card, locked):
            self._seg_row(card, "land_spot", {"Начало": "start", "Середина": "mid", "Конец": "end",
                                              "Рандом": "random"}, locked)

        def b_night(card, locked):
            self._switch_row(card, "net_guard", "Пропал интернет: ждать и ничего не жать", locked)

        def b_prof(card, locked):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(0, 6))
            ent = ctk.CTkEntry(row, height=30, fg_color=CARD2, border_color=BORDER, text_color=TEXT, font=F(12),
                               placeholder_text="Название профиля")
            ent.pack(side="left", fill="x", expand=True)
            row2 = ctk.CTkFrame(card, fg_color="transparent")
            row2.pack(fill="x", padx=16, pady=(0, 12))
            names = list((self.settings.get("user_profiles") or {}).keys()) or ["нет профилей"]
            om = ctk.CTkOptionMenu(row2, values=names, height=30, fg_color=CARD2, button_color=ACCENT_D,
                                   button_hover_color=ACCENT_D, text_color=TEXT, font=F(12), dropdown_font=F(12))
            om.pack(side="left", fill="x", expand=True)

            def save_p():
                n = ent.get().strip()[:24]
                if not n:
                    return
                skip = {"user_profiles", "tg_token", "tg_chat", "fps_backup", "gfx_backup", "skip_version",
                        "shop_seen", "premium_offer_seen", "last_weekly"}
                prof = {k: v for k, v in self.settings.items() if k not in skip}
                ups = dict(self.settings.get("user_profiles") or {})
                ups[n] = prof
                self.settings["user_profiles"] = ups
                save_settings(self.settings)
                om.configure(values=list(ups))
                om.set(n)
                ent.delete(0, "end")
                self.toast(f"Профиль «{n}» сохранён", GREEN)

            def load_p():
                prof = (self.settings.get("user_profiles") or {}).get(om.get())
                if prof:
                    self.settings.update(prof)
                    save_settings(self.settings)
                    self.show_main()
                    self.toast(f"Профиль «{om.get()}» загружен", GREEN)

            def del_p():
                ups = dict(self.settings.get("user_profiles") or {})
                if ups.pop(om.get(), None) is not None:
                    self.settings["user_profiles"] = ups
                    save_settings(self.settings)
                    om.configure(values=list(ups) or ["нет профилей"])
                    om.set((list(ups) or ["нет профилей"])[0])
            btns = [ctk.CTkButton(row, text="Сохранить", width=100, height=30, fg_color=ACCENT,
                                  hover_color=ACCENT_H, text_color=BTN_TXT, font=F(12, True), command=save_p),
                    ctk.CTkButton(row2, text="Загрузить", width=90, height=30, fg_color=CARD2, hover_color=BORDER,
                                  text_color=TEXT, font=F(12), command=load_p),
                    ctk.CTkButton(row2, text="✕", width=34, height=30, fg_color=CARD2, hover_color=BORDER,
                                  text_color=RED, font=F(12), command=del_p)]
            btns[0].pack(side="left", padx=(8, 0))
            btns[1].pack(side="left", padx=(8, 0))
            btns[2].pack(side="left", padx=(6, 0))
            if locked:
                for w in btns + [ent, om]:
                    w.configure(state="disabled")

        def b_theme(card, locked):
            opts = {v[0]: k for k, v in THEMES.items()}
            back = {k: v[0] for k, v in THEMES.items()}

            def pick(label):
                self.settings["theme"] = opts[label]
                save_settings(self.settings)
                self.after(50, self.show_main)
            seg = ctk.CTkSegmentedButton(card, values=list(opts), command=pick, selected_color=ACCENT_D,
                                         selected_hover_color=ACCENT_D, unselected_color=CARD2,
                                         unselected_hover_color=BORDER, fg_color=CARD2, text_color=TEXT, font=F(12))
            seg.set(back.get(self.settings.get("theme", "sakura"), "Сакура"))
            seg.pack(anchor="w", padx=16, pady=(0, 12))
            if locked:
                seg.configure(state="disabled")

        def b_sup(card, locked):
            bt = ctk.CTkButton(card, text="💬 Приоритетная поддержка", height=32, fg_color=GOLD,
                               hover_color=ACCENT_H, text_color="#2b1f06", font=F(12, True),
                               command=lambda: webbrowser.open(lic.TG_URL))
            bt.pack(anchor="w", padx=16, pady=(0, 12))
            if locked:
                bt.configure(state="disabled")

        items = [("tg_menu", P[0], b_tg), ("goal_on", P[1], b_goal), ("weekly_report", P[2], b_stats),
                 ("sched_on", P[3], b_sched), ("land_mode", P[4], b_land), ("low_gfx", P[5], b_night),
                 (None, P[6], b_prof), ("human_afk", P[7], None), (None, P[8], b_theme), (None, P[9], b_sup)]
        descs = {
            "weekly_report": "Каждое воскресенье вечером присылает в Telegram картинку-отчёт за неделю.",
            "human_afk": "Стрейфы, прыжки, присед и повороты вместо одного W. Меньше шансов, что кикнет "
                         "за AFK. Работает вместе с «Анти-AFK» (вкладка VIP).",
            "low_gfx": "На время фарма ставит минимальную графику, ПК тише и холоднее. Потом всё вернёт как было "
                       "(при запуске игры). Пропал интернет? Бот подождёт и ничего не будет жать.",
            "land_mode": "Прыгает в начале, середине или конце маршрута автобуса. В конце меньше "
                         "людей, спокойнее фармить сундуки.",
            "sched_on": "Бот сам запускается в начале окна и останавливается в конце (Fortnite запустит сам, "
                        "если включён «Перезапуск игры»).",
        }
        self.goal_lb = None
        self.chart = None
        for i, (key, (emo, title, desc), build) in enumerate(items):
            if key in bot_core.ULTIMATE_FEATURES:
                continue                      # с 1.6 — во вкладке Ultimate
            self._pcard(g, sum(1 for k, *_ in items[:i] if k not in bot_core.ULTIMATE_FEATURES),
                        key, f"{emo}  {title}", descs.get(key, desc), build, L)

    def _pcard(self, grid, i, key, title, desc, build, locked):
        card = ctk.CTkFrame(grid, fg_color=CARD, corner_radius=10,
                            border_width=0 if locked else 1, border_color="#5a4520")
        card.grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0, 6) if i % 2 == 0 else (6, 0), pady=6)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(top, text=title, text_color=MUTED if locked else TEXT, font=F(14, True)).pack(side="left")
        if locked:
            self.premium_badge(top).pack(side="left", padx=8)
        if key:
            var = tk.BooleanVar(value=bool(self.settings.get(key)) and not locked)

            def toggled(key=key, var=var):
                self.settings[key] = bool(var.get())
                save_settings(self.settings)
            sw = ctk.CTkSwitch(top, text="", variable=var, command=toggled, width=46, progress_color=GOLD,
                               button_color=TEXT, button_hover_color="#ffffff", fg_color=BORDER)
            sw.pack(side="right")
            if locked:
                sw.configure(state="disabled")
        ctk.CTkLabel(card, text=desc, text_color=MUTED, font=F(12), wraplength=380,
                     justify="left").pack(anchor="w", padx=16, pady=(0, 8))
        if build:
            build(card, locked)
        if locked:
            ctk.CTkButton(card, text="♛  Открыть в Premium", height=28, width=170, fg_color=CARD2,
                          hover_color=BORDER, text_color=GOLD, font=F(12, True),
                          command=lambda: self.show_page("shop")).pack(anchor="w", padx=16, pady=(0, 12))

    def _num_row(self, card, nkey, ntitle, lo, hi, locked):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(row, text=ntitle, text_color=MUTED, font=F(12)).pack(side="left")
        e = ctk.CTkEntry(row, width=70, height=28, fg_color=CARD2, border_color=BORDER, text_color=TEXT,
                         font=F(13), justify="center")
        e.insert(0, str(int(float(self.settings.get(nkey, lo) or 0))))
        e.pack(side="right")
        if locked:
            e.configure(state="disabled")

        def apply(*_):
            try:
                v = max(lo, min(hi, int(float(e.get().replace(",", ".")))))
            except ValueError:
                v = int(float(self.settings.get(nkey, lo) or lo))
            e.delete(0, "end")
            e.insert(0, str(v))
            self.settings[nkey] = v
            save_settings(self.settings)
        e.bind("<Return>", apply)
        e.bind("<FocusOut>", apply)

    def _seg_row(self, card, skey, opts, locked):
        back = {v: k for k, v in opts.items()}

        def cmd(label):
            self.settings[skey] = opts[label]
            save_settings(self.settings)
        seg = ctk.CTkSegmentedButton(card, values=list(opts), command=cmd, selected_color=ACCENT_D,
                                     selected_hover_color=ACCENT_D, unselected_color=CARD2,
                                     unselected_hover_color=BORDER, fg_color=CARD2, text_color=TEXT, font=F(12))
        seg.set(back.get(self.settings.get(skey), list(opts)[0]))
        seg.pack(anchor="w", padx=16, pady=(0, 8))
        if locked:
            seg.configure(state="disabled")

    def _switch_row(self, card, key, text, locked):
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(row, text=text, text_color=MUTED, font=F(12)).pack(side="left")
        var = tk.BooleanVar(value=bool(self.settings.get(key)) and not locked)

        def tog():
            self.settings[key] = bool(var.get())
            save_settings(self.settings)
        sw = ctk.CTkSwitch(row, text="", variable=var, command=tog, width=40, progress_color=GOLD,
                           button_color=TEXT, fg_color=BORDER)
        sw.pack(side="right")
        if locked:
            sw.configure(state="disabled")

    # ---------- статистика по дням ----------
    def _daily_tick(self):
        st = self.bot.stats
        cur = {k: st.get(k, 0) for k in ("matches", "rewards", "chests", "tokens", "jumps")}
        last = self._last_stats
        if last is not None:
            d = self.daily.setdefault(datetime.now().strftime("%Y-%m-%d"), {})
            for k, v in cur.items():
                dv = v - last.get(k, 0)
                if dv > 0:
                    d[k] = d.get(k, 0) + dv
            if self.bot.running and not self.bot.paused:
                d["sec"] = d.get("sec", 0) + 1
        self._last_stats = cur
        if time.time() - self._daily_saved > 60:
            self._daily_saved = time.time()
            keep = sorted(self.daily)[-60:]
            self.daily = {k: self.daily[k] for k in keep}
            try:
                with open(DAILY_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.daily, f)
            except Exception:
                pass
            if self.cur_page == "functions" and getattr(self, "_ftab", "") and "Premium" in self._ftab:
                self._draw_chart()

    def _week(self):
        from datetime import timedelta
        today = datetime.now().date()
        out = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            out.append((d, self.daily.get(d.strftime("%Y-%m-%d"), {})))
        return out

    def _draw_chart(self):
        c = getattr(self, "chart", None)
        if c is None:
            return
        try:
            c.delete("all")
            w = max(300, c.winfo_width())
            h = 150
            wk = self._week()
            mx = max([d.get("matches", 0) for _, d in wk] + [1])
            bw = (w - 20) / 7
            names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            for i, (day, d) in enumerate(wk):
                v = d.get("matches", 0)
                x0 = 10 + i * bw + bw * 0.18
                x1 = 10 + (i + 1) * bw - bw * 0.18
                bh = (h - 45) * v / mx
                c.create_rectangle(x0, h - 25 - bh, x1, h - 25, fill=GOLD if i == 6 else ACCENT, width=0)
                c.create_text((x0 + x1) / 2, h - 32 - bh, text=str(v) if v else "", fill=TEXT,
                              font=(FONT, 10, "bold"))
                c.create_text((x0 + x1) / 2, h - 12, text=names[day.weekday()], fill=MUTED, font=(FONT, 10))
            tot = {k: sum(d.get(k, 0) for _, d in wk) for k in ("matches", "rewards", "chests", "tokens", "sec")}
            self.chart_sum.configure(text=f"За 7 дней: {tot['matches']} каток · {tot['rewards']} наград · "
                                          f"{tot['chests']} сундуков · {tot['sec'] // 3600} ч")
        except Exception:
            pass

    def week_report_png(self):
        from PIL import Image, ImageDraw, ImageFont
        import io

        def font(sz, bold=False):
            for n in (("segoeuib.ttf" if bold else "segoeui.ttf"), "arial.ttf", "DejaVuSans.ttf"):
                try:
                    return ImageFont.truetype(n, sz)
                except Exception:
                    continue
            return ImageFont.load_default()
        W, H = 900, 520
        im = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(im)
        d.text((40, 30), "Afk token · отчёт за неделю", fill=TEXT, font=font(34, True))
        wk = self._week()
        tot = {k: sum(x.get(k, 0) for _, x in wk) for k in ("matches", "rewards", "chests", "tokens", "sec")}
        d.text((40, 82), f"{tot['matches']} каток  ·  {tot['rewards']} наград  ·  {tot['chests']} сундуков  ·  "
                         f"{tot['sec'] // 3600} ч работы" + (f"  ·  🏴‍☠️ {tot['tokens']}" if tot["tokens"] else ""),
               fill=MUTED, font=font(22))
        mx = max([x.get("matches", 0) for _, x in wk] + [1])
        names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        bw = (W - 80) / 7
        for i, (day, x) in enumerate(wk):
            v = x.get("matches", 0)
            x0, x1 = 40 + i * bw + 18, 40 + (i + 1) * bw - 18
            bh = 300 * v / mx
            d.rounded_rectangle([x0, 460 - bh, x1, 460], 10, fill=GOLD if i == 6 else ACCENT)
            if v:
                d.text(((x0 + x1) / 2, 450 - bh), str(v), fill=TEXT, font=font(22, True), anchor="mb")
            d.text(((x0 + x1) / 2, 490), names[day.weekday()], fill=MUTED, font=font(20), anchor="mm")
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        return buf.getvalue()

    def send_week_report(self):
        if not self.bot.tg_ready():
            self.toast("Сначала подключи Telegram (вкладка VIP)", YELLOW)
            return
        try:
            self.tg_reply("📊 Afk token: отчёт за неделю", photo=self.week_report_png())
            self.toast("Отчёт отправлен в Telegram", GREEN)
        except Exception as e:
            self.toast(f"Не удалось: {e}", RED)

    # ---------- расписание / авто-скрины ----------
    def _in_window(self, now):
        try:
            fh, fm = [int(x) for x in str(self.settings.get("sched_from", "23:00")).split(":")]
            th, tm = [int(x) for x in str(self.settings.get("sched_to", "07:00")).split(":")]
        except Exception:
            return False
        m, f, t = now.hour * 60 + now.minute, fh * 60 + fm, th * 60 + tm
        if f == t:
            return False
        if f < t:
            inside, day = f <= m < t, now
        else:
            from datetime import timedelta
            inside = m >= f or m < t
            day = now if m >= f else now - timedelta(days=1)
        return inside and str(day.isoweekday()) in str(self.settings.get("sched_days", "1234567"))

    def _sched_tick(self):
        try:
            if self.tier in PREM and self.settings.get("sched_on"):
                inside = self._in_window(datetime.now())
                if inside and not self.bot.running and not self._sched_active:
                    self._sched_active = True
                    self._append_log(time.strftime("[%H:%M:%S] ") + "🗓 Расписание: запускаю бота")
                    self.start_bot()
                elif not inside and self._sched_active:
                    self._sched_active = False
                    if self.bot.running:
                        self._append_log(time.strftime("[%H:%M:%S] ") + "🗓 Расписание: время вышло, останавливаю")
                        self.stop_bot()
            else:
                self._sched_active = False
            # еженедельный отчёт: воскресенье после 20:00
            now = datetime.now()
            wk = now.strftime("%G-%V")
            if (self.tier in PREM and self.settings.get("weekly_report") and now.isoweekday() == 7
                    and now.hour >= 20 and self.settings.get("last_weekly") != wk and self.bot.tg_ready()):
                self.settings["last_weekly"] = wk
                save_settings(self.settings)
                self.tg_reply("📊 Afk token: отчёт за неделю", photo=self.week_report_png())
        except Exception:
            pass
        self.after(30000, self._sched_tick)

    def _shot_loop(self):
        last = time.time()
        while True:
            time.sleep(20)
            try:
                n = int(self.settings.get("shot_every", 0) or 0)
                if n <= 0 or not self.bot.running or not self.bot.on("tg_menu") or not self.bot.tg_ready():
                    last = time.time()
                    continue
                if time.time() - last >= n * 60:
                    last = time.time()
                    jpg = bot_core.AfkBot.screenshot_jpg()
                    self.tg_reply(f"🖥 Авто-скрин · {time.strftime('%H:%M')}", photo=jpg)
            except Exception:
                pass

    # ================= вкладка: Магазин =================
    def build_shop(self):
        page = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        self.pages["shop"] = page
        pv, pp, pu = (self.shop.get("price_vip", "79"), self.shop.get("price_premium", "159"),
                      self.shop.get("price_upgrade", "99"))
        self.page_header(page, "Магазин" if self.tier not in PREM else "Premium",
                         "ключ навсегда · один ключ = один ПК")
        if self.tier in PREM:
            self._tab_banner(page, "♛ У тебя Premium", "Все функции открыты навсегда. Настраивай во вкладке "
                             "«Функции бота» → «Функции Premium».", None, gold=True)
        else:
            ban = asset_img("banner_wide.png", (900, 150))
            if ban:
                ctk.CTkLabel(page, text="", image=ban).pack(fill="x", pady=(0, 10))
        cols = ctk.CTkFrame(page, fg_color="transparent")
        cols.pack(fill="x")
        cols.grid_columnconfigure((0, 1), weight=1, uniform="s")

        # VIP снят с продажи: карточку показываем только тем, у кого он уже есть
        show_vip = self.tier == "vip"
        v = ctk.CTkFrame(cols, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER)
        if show_vip:
            v.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(v, text="★ VIP", text_color=ACCENT, font=F(22, True)).pack(anchor="w", padx=22, pady=(20, 0))
        ctk.CTkLabel(v, text=f"{pv} ₽", text_color=TEXT, font=F(40, True)).pack(anchor="w", padx=22)
        ctk.CTkLabel(v, text="навсегда", text_color=MUTED, font=F(12)).pack(anchor="w", padx=22, pady=(0, 10))
        for t in VIP_LIST:
            ctk.CTkLabel(v, text="✓  " + t, text_color=TEXT, font=F(13), anchor="w", justify="left",
                         wraplength=380).pack(anchor="w", padx=22, pady=2)
        if False:   # VIP больше не продаётся
            ctk.CTkButton(v, text=f"Купить VIP за {pv} ₽", height=44, corner_radius=10, fg_color=ACCENT,
                          hover_color=ACCENT_H, text_color=BTN_TXT, font=F(15, True),
                          command=lambda: self.open_shop_url("vip")).pack(fill="x", padx=22, pady=(16, 22))
        else:
            ctk.CTkLabel(v, text="✓ У тебя уже есть", text_color=GREEN, font=F(14, True)).pack(
                anchor="w", padx=22, pady=(16, 22))

        # Premium
        p = ctk.CTkFrame(cols, fg_color="#2b2112", corner_radius=14, border_width=2, border_color=GOLD)
        if show_vip:
            p.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        else:
            p.grid(row=0, column=0, columnspan=2, sticky="nsew")
        top = ctk.CTkFrame(p, fg_color="transparent")
        top.pack(fill="x", padx=22, pady=(20, 0))
        ctk.CTkLabel(top, text="♛ PREMIUM", text_color=GOLD, font=F(22, True)).pack(side="left")
        ctk.CTkLabel(top, text=" ВЫГОДНО ", fg_color=GOLD, text_color="#2b1f06", corner_radius=6,
                     font=F(11, True)).pack(side="left", padx=10)
        if self.tier == "vip" and not self.vip_until:
            pr = ctk.CTkFrame(p, fg_color="transparent")
            pr.pack(anchor="w", padx=22)
            ctk.CTkLabel(pr, text=f"{pu} ₽", text_color=TEXT, font=F(40, True)).pack(side="left")
            ctk.CTkLabel(pr, text=f"  вместо {pp} ₽, апгрейд для VIP", text_color=GOLD,
                         font=F(13, True)).pack(side="left", pady=(14, 0))
        else:
            ctk.CTkLabel(p, text=f"{pp} ₽", text_color=TEXT, font=F(40, True)).pack(anchor="w", padx=22)
        ctk.CTkLabel(p, text="навсегда · фарм без остановки + 10 функций", text_color="#d8c49a", font=F(12)).pack(
            anchor="w", padx=22, pady=(0, 10))
        for emo, t, d in PREMIUM_LIST:
            ctk.CTkLabel(p, text=f"{emo}  {t}", text_color=TEXT, font=F(13, True), anchor="w").pack(
                anchor="w", padx=22, pady=(3, 0))
            ctk.CTkLabel(p, text=d, text_color="#c9b88f", font=F(11), anchor="w", justify="left",
                         wraplength=400).pack(anchor="w", padx=44)
        if self.tier in PREM:
            ctk.CTkLabel(p, text="♛ Активен", text_color=GOLD, font=F(15, True)).pack(anchor="w", padx=22,
                                                                                      pady=(16, 22))
        elif self.tier == "vip" and not self.vip_until:
            ctk.CTkButton(p, text=f"♛  Обновиться до Premium за {pu} ₽", height=44, corner_radius=10,
                          fg_color=GOLD, hover_color="#e6ac22", text_color="#2b1f06", font=F(15, True),
                          command=lambda: self.open_shop_url("upgrade")).pack(fill="x", padx=22, pady=(16, 22))
        else:
            ctk.CTkButton(p, text=f"♛  Купить Premium за {pp} ₽", height=44, corner_radius=10,
                          fg_color=GOLD, hover_color="#e6ac22", text_color="#2b1f06", font=F(15, True),
                          command=lambda: self.open_shop_url("premium")).pack(fill="x", padx=22, pady=(16, 22))

        # Ultimate
        pl = self.shop.get("price_ultimate", "249")
        u = ctk.CTkFrame(page, fg_color="#10222b", corner_radius=14, border_width=2, border_color=ULTRA)
        u.pack(fill="x", pady=(14, 0))
        utop = ctk.CTkFrame(u, fg_color="transparent")
        utop.pack(fill="x", padx=22, pady=(18, 0))
        ctk.CTkLabel(utop, text="⚡ ULTIMATE", text_color=ULTRA, font=F(22, True)).pack(side="left")
        ctk.CTkLabel(utop, text=" НОВОЕ ", fg_color=ULTRA, text_color="#06212b", corner_radius=6,
                     font=F(11, True)).pack(side="left", padx=10)
        ctk.CTkLabel(utop, text=f"{pl} ₽", text_color=TEXT, font=F(32, True)).pack(side="right")
        ctk.CTkLabel(u, text="навсегда · всё из Premium + умный бег", text_color="#a8d8ea", font=F(12)).pack(
            anchor="w", padx=22, pady=(0, 8))
        for t in ("✓  Обход препятствий: бот больше не застревает",
                  "✓  Плавные движения мышкой, как у живого игрока",
                  "✓  Уход от зоны",
                  "✓  Бот выходит из катки, если остался в команде один",
                  "⏳  Открытие сундуков через ИИ — скоро, пока недоступно"):
            ctk.CTkLabel(u, text=t, text_color=TEXT if t[0] == "✓" else MUTED, font=F(13), anchor="w").pack(
                anchor="w", padx=22, pady=2)
        if self.tier == "ultimate":
            ctk.CTkLabel(u, text="⚡ Активен", text_color=ULTRA, font=F(15, True)).pack(anchor="w", padx=22,
                                                                                     pady=(12, 18))
        else:
            ctk.CTkButton(u, text=f"⚡  Купить Ultimate за {pl} ₽", height=44, corner_radius=10, fg_color=ULTRA,
                          hover_color="#5cc3ee", text_color="#06212b", font=F(15, True),
                          command=lambda: self.open_shop_url("ultimate")).pack(fill="x", padx=22, pady=(12, 18))

        foot = ctk.CTkFrame(page, fg_color="transparent")
        foot.pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(foot, text="Уже купил? Введи ключ, и функции откроются сразу.", text_color=MUTED,
                     font=F(13)).pack(side="left")
        ctk.CTkButton(foot, text="🔑  Ввести ключ", height=36, fg_color=CARD2, hover_color=BORDER,
                      text_color=TEXT, font=F(13, True), command=self.open_vip).pack(side="right")
        ctk.CTkLabel(page, text=f"Покупка на Starvell с гарантией площадки. Вопросы пиши {TG_NICK}",
                     text_color=MUTED, font=F(12)).pack(anchor="w", pady=(10, 0))

    def open_premium_offer(self):
        """Окно для владельцев VIP: новая привилегия Premium + вкладка со всеми функциями."""
        self.settings["premium_offer_seen"] = True
        save_settings(self.settings)
        pu = self.shop.get("price_upgrade", "99")
        win = ctk.CTkToplevel(self)
        win.title("Новая привилегия: Premium")
        win.geometry("560x640")
        win.resizable(False, False)
        win.configure(fg_color=SIDEBAR)
        win.transient(self)
        win.after(150, win.grab_set)
        ctk.CTkLabel(win, text="♛ Новая привилегия: PREMIUM", text_color=GOLD, font=F(22, True)).pack(
            pady=(20, 0))
        ctk.CTkLabel(win, text=f"Обновиться можно всего за {pu} ₽", text_color=TEXT, font=F(17, True)).pack(
            pady=(4, 10))
        tv = ctk.CTkTabview(win, fg_color=CARD, segmented_button_selected_color=ACCENT_D,
                            segmented_button_selected_hover_color=ACCENT_D, segmented_button_fg_color=CARD2,
                            segmented_button_unselected_color=CARD2, text_color=TEXT, height=430)
        tv.pack(fill="both", expand=True, padx=18)
        t1 = tv.add("Что это")
        t2 = tv.add("Функции Premium")
        ctk.CTkLabel(t1, text="🏴‍☠️ Получи токен быстрее", text_color=TEXT, font=F(18, True)).pack(
            anchor="w", padx=12, pady=(12, 4))
        ctk.CTkLabel(t1, text="Ты уже с нами на VIP, спасибо 💛 Для тебя апгрейд до Premium со скидкой: "
                              f"{pu} ₽ вместо {self.shop.get('price_premium', '159')} ₽, навсегда.\n\n"
                              "Бот сам запускается по расписанию, фармит до цели (например, до Пиратского "
                              "токена) и выключает ПК, управляется кнопками с телефона, прыгает в лучшую точку "
                              "и бегает как живой игрок.\n\nВсе 10 функций лежат во вкладке «Функции Premium» "
                              "рядом 👉",
                     text_color=MUTED, font=F(13), wraplength=470, justify="left").pack(anchor="w", padx=12)
        sc = ctk.CTkScrollableFrame(t2, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        for emo, t, d in PREMIUM_LIST:
            ctk.CTkLabel(sc, text=f"{emo}  {t}", text_color=TEXT, font=F(14, True), anchor="w").pack(
                anchor="w", padx=8, pady=(8, 0))
            ctk.CTkLabel(sc, text=d, text_color=MUTED, font=F(12), wraplength=440, justify="left",
                         anchor="w").pack(anchor="w", padx=34)
        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=14)
        ctk.CTkButton(row, text="Позже", width=110, height=42, fg_color=CARD2, hover_color=BORDER, text_color=TEXT,
                      font=F(13), command=win.destroy).pack(side="left")

        def go():
            win.destroy()
            self.open_shop_url("upgrade")
        ctk.CTkButton(row, text=f"♛  Обновиться за {pu} ₽", height=42, fg_color=GOLD, hover_color="#e6ac22",
                      text_color="#2b1f06", font=F(15, True), command=go).pack(side="right", fill="x",
                                                                              expand=True, padx=(10, 0))

    def adm_shop(self):
        """Админ: цены и ссылки магазина (видят все пользователи)."""
        win = ctk.CTkToplevel(self)
        win.title("Магазин: цены и ссылки")
        win.geometry("560x640")
        win.configure(fg_color=SIDEBAR)
        win.transient(self)
        win.after(150, win.grab_set)
        ents = {}
        rows = [("price_vip", "Цена VIP, ₽"), ("price_premium", "Цена Premium, ₽"),
                ("price_upgrade", "Цена апгрейда VIP→Premium, ₽"), ("url_vip", "Ссылка на лот VIP"),
                ("url_premium", "Ссылка на лот Premium"), ("url_upgrade", "Ссылка на лот апгрейда"),
                ("price_ultimate", "Цена Ultimate, ₽"), ("url_ultimate", "Ссылка на лот Ultimate")]
        for k, t in rows:
            ctk.CTkLabel(win, text=t, text_color=MUTED, font=F(12)).pack(anchor="w", padx=20, pady=(10, 0))
            e = ctk.CTkEntry(win, height=32, fg_color=CARD, border_color=BORDER, text_color=TEXT, font=F(12))
            e.insert(0, str(self.shop.get(k, "")))
            e.pack(fill="x", padx=20)
            ents[k] = e
        msg = ctk.CTkLabel(win, text="", text_color=MUTED, font=F(12))
        msg.pack(pady=(8, 0))

        ctk.CTkLabel(win, text="Вставка: Ctrl+V или правый клик по полю → «Вставить»", text_color=MUTED,
                     font=F(11)).pack()

        def save_all():
            vals = {k: e.get().strip() for k, e in ents.items()}
            bad = [t for (k, t) in rows if k.startswith("url_") and vals[k] and not vals[k].startswith("http")]
            if bad:
                msg.configure(text="Ссылка должна начинаться с https://: " + ", ".join(bad), text_color=RED)
                return
            changed = {k: v for k, v in vals.items() if v != str(self.shop.get(k, ""))}
            if not changed:
                msg.configure(text="Ничего не поменялось, на сервере то же самое", text_color=YELLOW)
                return
            msg.configure(text="Сохраняю...", text_color=MUTED)

            def work():
                for k, v in changed.items():
                    lic.admin_set_config(k, v)
                return lic.get_config()

            def done(res):
                if isinstance(res, Exception):
                    msg.configure(text=f"Ошибка: {res}", text_color=RED)
                    return
                miss = [k for k, v in changed.items() if str(res.get(k, "")) != v]
                if miss:
                    msg.configure(text="Сервер не принял: " + ", ".join(miss) + ". Проверь SQL 1.4", text_color=RED)
                    return
                names = dict(rows)
                msg.configure(text="Сохранено ✓ " + ", ".join(names[k] for k in changed), text_color=GREEN)
                self._on_shop_cfg(res)
            self.bg(work, done)
        ctk.CTkButton(win, text="Сохранить", height=38, fg_color=ACCENT, hover_color=ACCENT_H, text_color=BTN_TXT,
                      font=F(13, True), command=save_all).pack(pady=10)

    # ================= выход =================
    def on_close(self):
        if self.settings.get("tray_on_close", True) and self.tray:
            self.withdraw()
            if not getattr(self, "_tray_hint", False):
                self._tray_hint = True
                try:
                    self.tray.notify("Afk token работает в трее. Нажми на иконку, чтобы открыть.", APP_NAME)
                except Exception:
                    pass
            return
        self.quit_app()


if __name__ == "__main__":
    # 1.6: по умолчанию открывается новый интерфейс «Стекло». Классическое окно — с ключом
    # --classic, при автозапуске в трей (--tray) или если новый интерфейс открыть не удалось.
    if "--classic" not in sys.argv and "--tray" not in sys.argv:
        try:
            import afk_token_glass
            afk_token_glass.run()          # при успехе сам завершает программу
        except Exception as _e:
            try:
                with open(os.path.join(LOG_DIR, "afk_token.log"), "a", encoding="utf-8") as _f:
                    _f.write(time.strftime("%Y-%m-%d [%H:%M:%S] ") + f"Новый интерфейс не открылся: {_e!r}\n")
            except Exception:
                pass
    App().mainloop()
