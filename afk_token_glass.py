# -*- coding: utf-8 -*-
"""Afk token — интерфейс «Стекло» (1.6). Окно из папки new_ui управляет тем же ботом.

Запускается из afk_token.py (start.bat). Если pywebview или WebView2 недоступны —
afk_token.py открывает классическое окно. Чат, рефералы и трей пока есть только
в классическом окне (кнопка в «Создатель» или запуск с ключом --classic).
"""
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque

if sys.stdout is None:  # запуск без консоли
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
    sys.stderr = sys.stdout

import bot_core
import license_client as lic
import afk_token as classic   # берём готовую логику: обновления, Telegram-пульт, статистика

APP_NAME = classic.APP_NAME
APP_VERSION = classic.APP_VERSION
APP = lic.app_dir()
LOG_DIR = os.path.join(APP, "logs")
UI_INDEX = os.path.join(getattr(sys, "_MEIPASS", APP), "new_ui", "index.html")
if not os.path.exists(UI_INDEX):
    UI_INDEX = os.path.join(APP, "new_ui", "index.html")
NO_GLASS_MARK = os.path.join(APP, ".no_glass")
SECRET_KEYS = ("tg_token",)
BLOCKED_KEYS = ("user_profiles", "fps_backup", "gfx_backup", "cpd", "shop_seen", "premium_offer_seen",
                "last_weekly", "skip_version")


class _Queue:
    """Замена очереди окна: классический код кладёт сюда ("cb", функция, аргумент)."""

    def put(self, item):
        if item and item[0] == "cb":
            threading.Thread(target=lambda: item[1](item[2]), daemon=True).start()


class _Headless:
    """Логика классического окна без самого окна: пульт из Telegram, авто-скрины,
    расписание, статистика по дням и недельный отчёт."""
    tg_reply = classic.App.tg_reply
    tg_menu = classic.App.tg_menu
    tg_command = classic.App.tg_command
    _tg_poll_loop = classic.App._tg_poll_loop
    _shot_loop = classic.App._shot_loop
    _in_window = classic.App._in_window
    _week = classic.App._week
    week_report_png = classic.App.week_report_png
    _daily_tick = classic.App._daily_tick

    def __init__(self, api):
        self._api = api
        self.settings = api._s
        self.bot = api._bot
        self.q = _Queue()
        self._tg_poll_pause = False
        self.cur_page = None
        self._last_stats = None
        self._daily_saved = time.time()
        self._sched_active = False
        try:
            with open(classic.DAILY_FILE, encoding="utf-8") as f:
                self.daily = json.load(f)
        except Exception:
            self.daily = {}

    @property
    def tier(self):
        return self._api._tier

    def start_bot(self):
        return self._api.start_bot()

    def stop_bot(self):
        return self._api.stop_bot()

    def bg(self, func, callback=None, *args):
        def worker():
            try:
                res = func(*args)
            except Exception as e:
                res = e
            if callback:
                callback(res)
        threading.Thread(target=worker, daemon=True).start()

    def _draw_chart(self):
        pass

    def loop(self):
        """Раз в секунду — статистика; раз в 30 сек — расписание и недельный отчёт; раз в 5 мин — онлайн-отметка."""
        from datetime import datetime
        n = 0
        while True:
            time.sleep(1)
            n += 1
            try:
                self._daily_tick()
                if n % 30 == 0:
                    self._sched(datetime.now())
                if n % 300 == 5 and lic.configured():
                    lic.ping(n == 5, bool(self.bot.running))
            except Exception:
                pass

    def _sched(self, now):
        s = self.settings
        if self.tier in classic.PREM and s.get("sched_on"):
            inside = self._in_window(now)
            if inside and not self.bot.running and not self._sched_active:
                self._sched_active = True
                self._api._log("🗓 Расписание: запускаю бота")
                res = self.start_bot()
                if not res.get("ok"):
                    self._api._log("🗓 Не запустился: " + str(res.get("error")))
            elif not inside and self._sched_active:
                self._sched_active = False
                if self.bot.running:
                    self._api._log("🗓 Расписание: время вышло, останавливаю")
                    self.stop_bot()
        else:
            self._sched_active = False
        wk = now.strftime("%G-%V")
        if (self.tier in classic.PREM and s.get("weekly_report") and now.isoweekday() == 7 and now.hour >= 20
                and s.get("last_weekly") != wk and self.bot.tg_ready()):
            s["last_weekly"] = wk
            classic.save_settings(s)
            self.tg_reply("📊 Afk token: отчёт за неделю", photo=self.week_report_png())


class Api:
    """Методы без подчёркивания видны из окна как pywebview.api.<имя>()."""

    def __init__(self):
        self._s = classic.load_settings()
        self._lock = threading.Lock()
        self._logs = deque(maxlen=500)
        self._state = "stopped"
        self._key = None
        self._tier = "free"
        self._admin = False
        self._key_lost = False
        self._rev = 0                      # растёт, когда меняются ключ / магазин — окно перечитывает meta()
        self._shop = dict(lic.SHOP_DEFAULTS)
        self._update = None                # (версия, что нового, ссылка)
        self._upd = {"status": "", "frac": 0, "busy": False, "error": ""}
        self._gate_last_ok = 0.0
        self._gate_paused = False
        self._gate_running = False
        self._bg_started = False
        self._log_n = 0
        os.makedirs(LOG_DIR, exist_ok=True)
        self._bot = bot_core.AfkBot(self._s, log=self._log, on_state=self._on_state)
        self._head = _Headless(self)

    # ---------- служебное ----------
    def _log(self, msg):
        stamp = time.strftime("%H:%M:%S")
        with self._lock:
            self._logs.append((stamp, str(msg)))
        try:
            path = os.path.join(LOG_DIR, "afk_token.log")
            self._log_n += 1
            if self._log_n % 200 == 1 and os.path.exists(path) and os.path.getsize(path) > 5 * 1024 * 1024:
                os.replace(path, path + ".old")
            with open(path, "a", encoding="utf-8") as f:
                f.write(time.strftime("%Y-%m-%d ") + f"[{stamp}] {msg}\n")
        except Exception:
            pass

    def _on_state(self, st):
        if st != self._state and st in ("running", "stopped"):
            classic.save_settings(self._s)
        self._state = st

    def _set_license(self, key, res):
        self._key = key
        self._admin = bool(res.get("admin"))
        self._tier = "free" if res.get("offline") else ("ultimate" if self._admin else (res.get("tier") or "vip"))
        self._key_lost = False
        self._bot.vip = self._tier != "free"
        self._bot.tier = self._tier
        self._paid_defaults()
        self._rev += 1

    def _paid_defaults(self):
        """Платный ключ: один раз включаем «Бег» — без него бот после приземления просто стоит
        и функции Premium/Ultimate (ходьба, камера, обход, зона) не срабатывают.
        Если человек потом сам выключит «Бег», больше не трогаем."""
        if self._tier == "free" or self._s.get("explore_auto_on"):
            return
        self._s["explore"] = True
        self._s["explore_auto_on"] = True
        try:
            classic.save_settings(self._s)
        except Exception:
            pass
        self._rev += 1
        self._log("🏃 Включил «Бег»: без него бот не ходит по карте и не крутит камерой")

    def _allowed(self, key):
        if key in bot_core.FREE_FEATURES:
            return True
        if not self._key:
            return False
        if key in bot_core.ULTIMATE_FEATURES:
            return self._tier == "ultimate"
        if key in bot_core.PREMIUM_FEATURES:
            return self._tier in bot_core.PREMIUM_TIERS
        return True

    def _start_background(self):
        if self._bg_started:
            return
        self._bg_started = True
        threading.Thread(target=self._head._tg_poll_loop, daemon=True).start()
        threading.Thread(target=self._head._shot_loop, daemon=True).start()
        threading.Thread(target=self._head.loop, daemon=True).start()
        threading.Thread(target=self._load_shop, daemon=True).start()
        threading.Thread(target=self._check_update, daemon=True).start()

    def _load_shop(self):
        try:
            cfg = lic.get_config()
            if isinstance(cfg, dict):
                self._shop.update(cfg)
                self._rev += 1
        except Exception:
            pass

    def _check_update(self):
        time.sleep(2.5)
        try:
            res = classic.check_update()
        except Exception:
            res = None
        if res:
            self._update = res

    # ---------- запуск окна ----------
    def init(self):
        """Первый вызов из окна: настройки, состояние и проверка сохранённого ключа."""
        self._start_background()
        lic_info = {"ok": False}
        saved = lic.load_saved()
        if not lic.configured():
            lic_info = {"ok": False, "error": "сервер ключей не настроен (server_config.py)"}
        elif saved and saved.get("key"):
            try:
                res = lic.activate(saved["key"])
            except Exception as e:
                res = {"ok": False, "error": str(e)}
            if res.get("ok"):
                self._set_license(saved["key"], res)
                lic_info = {"ok": True, "offline": bool(res.get("offline"))}
            else:
                lic_info = {"ok": False, "error": res.get("error", "")}
        out = self.meta()
        out.update({"license": lic_info, "state": self._state})
        return out

    def meta(self):
        """Всё, что окну нужно знать про ключ, уровень, магазин и настройки."""
        s = {k: v for k, v in self._s.items() if isinstance(v, (bool, int, float, str))
             and k not in SECRET_KEYS and k not in BLOCKED_KEYS}
        keys = set(bot_core.DEFAULTS)
        return {"version": APP_VERSION + (" β" if classic.BETA else ""), "rev": self._rev,
                "has_key": bool(self._key), "tier": self._tier, "admin": self._admin,
                "free_edition": bool(classic.FREE_EDITION), "shop": dict(self._shop), "settings": s,
                "has_tg_token": bool(self._s.get("tg_token")),
                "allowed": {k: self._allowed(k) for k in keys if isinstance(bot_core.DEFAULTS[k], bool)}}

    def activate(self, key):
        key = str(key or "").strip().upper()
        if not key:
            return {"ok": False, "error": "Введи ключ"}
        try:
            res = lic.activate(key)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if res.get("ok"):
            self._set_license(key, res)
            return {"ok": True, "tier": self._tier}
        return {"ok": False, "error": res.get("error") or "Ключ не подходит"}

    def set_setting(self, key, value):
        if key not in bot_core.DEFAULTS or key in BLOCKED_KEYS:
            return False
        old = bot_core.DEFAULTS[key]
        if isinstance(old, bool):
            value = bool(value)
        elif isinstance(old, (int, float)):
            try:
                value = float(value)
                value = int(value) if isinstance(old, int) or value == int(value) else value
            except (TypeError, ValueError):
                return False
        elif isinstance(old, str):
            value = str(value).strip()[:200]
        else:
            return False
        self._s[key] = value
        classic.save_settings(self._s)
        return True

    # ---------- бот ----------
    def start_bot(self):
        if self._bot.running:
            return {"ok": True}
        free = not self._key and classic.FREE_EDITION
        if not self._key and not free:
            return {"ok": False, "error": "сначала активируй ключ", "need_key": True}
        if free:
            self._tier = "free"
        elif lic.configured():
            try:
                res = lic.session(True)
            except Exception as e:
                res = e
            if isinstance(res, Exception) or not isinstance(res, dict) or res.get("reason") == "empty":
                loc = lic.local_license()      # сервер недоступен → аварийный режим по сохранённой лицензии
                if not loc:
                    return {"ok": False, "error": "нет связи с сервером, для запуска нужен интернет"}
                self._tier = loc["tier"]
                self._gate_last_ok = 0.0
                self._log("🛟 Сервер не ответил, пока работают только бесплатные функции")
            elif not res.get("ok"):
                return {"ok": False, "error": res.get("error") or "ключ не разрешён"}
            else:
                self._tier = "ultimate" if self._admin else (res.get("tier") or self._tier)
                self._gate_last_ok = time.time()
        self._gate_paused = False
        self._bot.vip = not free and self._tier != "free"
        self._bot.tier = self._tier
        self._paid_defaults()
        self._state = "loading"
        self._bot.start()
        if not free and lic.configured() and not self._gate_running:
            self._gate_running = True
            threading.Thread(target=self._gate_loop, daemon=True).start()
        return {"ok": True}

    def stop_bot(self):
        self._bot.stop()
        return True

    def toggle_pause(self):
        self._bot.toggle_pause()
        return True

    def poll(self):
        """Окно спрашивает раз в ~0.7 сек: новые строки журнала, состояние и статистика."""
        with self._lock:
            logs = list(self._logs)
            self._logs.clear()
        b = self._bot
        if not b.running and self._state != "loading":
            self._state = "stopped"
        st = b.stats
        sec = int(time.time() - st["started"]) if st.get("started") else 0
        upd = None
        if self._update:
            ver = self._update[0]
            can = classic.can_auto_update() and bool(self._update[2])
            upd = {"version": ver, "notes": self._update[1], "can_auto": can,
                   "auto": bool(self._s.get("auto_update", True)) and can and not b.running,
                   "skipped": self._s.get("skip_version") == ver, "progress": dict(self._upd)}
        return {"state": self._state, "logs": logs, "tier": self._tier, "key_lost": self._key_lost,
                "rev": self._rev, "update": upd,
                "stats": {"matches": st["matches"], "chests": st["chests"], "rewards": st["rewards"],
                          "jumps": st["jumps"], "tokens": st["tokens"],
                          "time": f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}"}}

    # ---------- разное ----------
    def open_url(self, url):
        if isinstance(url, str) and url.startswith(("https://t.me/", "https://starvell.com/",
                                                    "https://new.donatepay.ru/donate/")):
            webbrowser.open(url)
            return True
        return False

    def open_shop(self, what):
        """Открыть лот в магазине (ссылки задаёт админ). Нет ссылки — Telegram создателя."""
        url = str(self._shop.get(f"url_{what}") or "")
        if not url.startswith("https://"):
            url = lic.TG_URL
        webbrowser.open(url)
        return True

    def copy(self, text):
        try:
            subprocess.run("clip", input=str(text).encode("utf-16-le"), check=True, shell=True, timeout=5)
            return True
        except Exception:
            return False

    def hwid(self):
        return lic.get_hwid()

    def open_classic(self):
        """Закрыть это окно и открыть классическое (чат, рефералы, пользователи, трей)."""
        self._bot.stop()
        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable, "--classic"], cwd=APP)
            else:
                subprocess.Popen([sys.executable, os.path.join(APP, "afk_token.py"), "--classic"], cwd=APP)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        threading.Timer(0.6, lambda: os._exit(0)).start()
        return {"ok": True}

    # ---------- Telegram ----------
    # ---------- чат (видят все, у кого стоит Afk token) ----------
    def chat_fetch(self, after):
        try:
            return lic.chat_fetch(after) or {}
        except Exception as e:
            return {"error": str(e)}

    def chat_send(self, text):
        try:
            return lic.chat_send((text or "").strip()[:300]) or {}
        except Exception as e:
            return {"error": str(e)}

    def chat_nick(self, nick):
        try:
            return lic.chat_set_nick((nick or "").strip()[:24]) or {}
        except Exception as e:
            return {"error": str(e)}

    def tg_save(self, token, chat):
        if token:
            self._s["tg_token"] = str(token).strip()
        self._s["tg_chat"] = str(chat or "").strip()
        classic.save_settings(self._s)
        return True

    def tg_find_chat(self):
        import tg_notify
        if not self._s.get("tg_token"):
            return {"ok": False, "error": "Сначала вставь токен бота"}
        self._head._tg_poll_pause = True
        try:
            cid, name = tg_notify.find_chat_id(self._s["tg_token"])
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            self._head._tg_poll_pause = False
        self._s["tg_chat"] = cid
        classic.save_settings(self._s)
        return {"ok": True, "chat": cid, "name": name}

    def tg_test(self):
        import tg_notify
        if not (self._s.get("tg_token") and self._s.get("tg_chat")):
            return {"ok": False, "error": "Заполни токен и Chat ID"}
        try:
            tg_notify.send_text(self._s["tg_token"], self._s["tg_chat"],
                                "✅ Afk token подключён. Сюда будут приходить награды.")
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    # ---------- обновления ----------
    def update_skip(self):
        if self._update:
            self._s["skip_version"] = self._update[0]
            classic.save_settings(self._s)
        return True

    def update_start(self):
        if not self._update or self._upd["busy"]:
            return False
        ver, notes, url = self._update
        if not (classic.can_auto_update() and url):
            webbrowser.open(url if str(url).startswith("https://") else lic.TG_URL)
            return False
        self._upd.update(busy=True, error="", status="Скачиваю обновление…", frac=0)
        self._bot.stop()

        def work():
            import tempfile
            try:
                tmp = tempfile.mkdtemp(prefix="afktoken_upd_")
                zp = os.path.join(tmp, "update.zip")

                def progress(done, total):
                    self._upd.update(frac=(done / total if total else 0),
                                     status=f"Скачиваю… {done // 1024} КБ" + (f" из {total // 1024} КБ" if total else ""))
                classic.download_update(url, zp, progress)
                self._upd.update(status="Распаковываю…", frac=1)
                src = classic.prepare_update(zp, tmp)
                self._upd.update(status="Готово! Перезапускаю программу…")
                classic.launch_updater(src, tmp)
                time.sleep(0.9)
                os._exit(0)
            except Exception as e:
                self._upd.update(busy=False, error=f"Не получилось обновить: {e}", status="")
        threading.Thread(target=work, daemon=True).start()
        return True

    # ---------- предложения / тикеты ----------
    @staticmethod
    def _sug_err(e):
        msg = str(e)
        if "afk_sug" in msg or "afk_admin_sug" in msg or "Could not find the function" in msg:
            return "Предложения ещё не включены на сервере. Напиши @kk4ose"
        if isinstance(e, lic.NetworkError):
            return "Нет связи с сервером"
        return msg[:200]

    def sug_send(self, kind, title, body):
        try:
            res = lic.sug_send(str(kind), str(title)[:80], str(body)[:1500], self._tier if self._key else "free")
        except Exception as e:
            return {"ok": False, "error": self._sug_err(e)}
        return res if isinstance(res, dict) else {"ok": False, "error": "пустой ответ сервера"}

    def sug_mine(self):
        try:
            return {"ok": True, "rows": lic.sug_mine()}
        except Exception as e:
            return {"ok": False, "error": self._sug_err(e)}

    def admin_sug_list(self):
        try:
            self._adm()
            return {"ok": True, "rows": lic.admin_sug_list()}
        except Exception as e:
            return {"ok": False, "error": self._sug_err(e)}

    def admin_sug_update(self, sid, status, reply=None):
        if status not in ("new", "planned", "done", "rejected", "answered", "delete"):
            return {"ok": False, "error": "неизвестный статус"}
        try:
            self._adm()
            lic.admin_sug_update(sid, status, reply)
        except Exception as e:
            return {"ok": False, "error": self._sug_err(e)}
        return {"ok": True}

    # ---------- личные сообщения (1.6.1) ----------
    @staticmethod
    def _msg_err(e):
        msg = str(e)
        if "afk_msg" in msg or "afk_admin_msg" in msg or "Could not find the function" in msg:
            return "Сообщения ещё не включены на сервере (supabase_v161_messages.sql)"
        if isinstance(e, lic.NetworkError):
            return "Нет связи с сервером"
        return msg[:200]

    def msg_fetch(self):
        """Окно зовёт при запуске: непрочитанные сообщения от создателя."""
        if not self._key:
            return {"ok": True, "rows": []}
        try:
            return {"ok": True, "rows": lic.msg_fetch()}
        except Exception as e:
            return {"ok": False, "error": self._msg_err(e)}

    def msg_read(self, mid):
        try:
            lic.msg_read(mid)
        except Exception as e:
            return {"ok": False, "error": self._msg_err(e)}
        return {"ok": True}

    def admin_msg_send(self, key, body):
        body = str(body or "").strip()
        if not body:
            return {"ok": False, "error": "Сообщение пустое"}
        try:
            self._adm()
            res = lic.admin_msg_send(str(key), body[:1000])
        except Exception as e:
            return {"ok": False, "error": self._msg_err(e)}
        return res if isinstance(res, dict) else {"ok": False, "error": "пустой ответ сервера"}

    def admin_msg_list(self, key):
        try:
            self._adm()
            return {"ok": True, "rows": lic.admin_msg_list(str(key))}
        except Exception as e:
            return {"ok": False, "error": self._msg_err(e)}

    def admin_msg_delete(self, mid):
        try:
            self._adm()
            lic.admin_msg_delete(mid)
        except Exception as e:
            return {"ok": False, "error": self._msg_err(e)}
        return {"ok": True}

    # ---------- админ ----------
    def _adm(self):
        if not self._admin:
            raise PermissionError("только для админа")

    def admin_list(self):
        try:
            self._adm()
            rows = lic.admin_list()
        except Exception as e:
            return {"ok": False, "error": str(e)}
        out = []
        for r in rows:
            st, tag = classic.App._row_status(r)
            tr = {"premium": " · Premium", "upgrade": " · Апгрейд", "ultimate": " · Ultimate"}.get(r.get("tier") or "", "")
            out.append({"key": r["key"], "status": st + tr, "tag": tag, "pc": r.get("pc_name") or "",
                        "hwid": r.get("hwid") or "", "note": r.get("note") or "", "banned": bool(r.get("banned")),
                        "seen": classic.fmt_time(r.get("last_seen")), "runs": r.get("launches") or 0})
        return {"ok": True, "rows": out}

    def admin_action(self, key, action, note=None):
        if action not in ("note", "reset_hwid", "ban", "unban", "delete"):
            return {"ok": False, "error": "неизвестное действие"}
        try:
            self._adm()
            lic.admin_action(str(key), action, note)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    def admin_create(self, n, tier):
        if tier not in ("vip", "premium", "upgrade", "ultimate"):
            return {"ok": False, "error": "неизвестный уровень"}
        try:
            self._adm()
            n = max(1, min(500, int(n)))
            keys = list({lic.new_key() for _ in range(n)})
            names = {"vip": "VIP", "premium": "Premium", "upgrade": "Апгрейд", "ultimate": "Ultimate"}
            res = lic.admin_add_tier(keys, tier, names[tier])
        except Exception as e:
            return {"ok": False, "error": str(e)}
        name = time.strftime(f"new_keys_{tier}_%Y%m%d_%H%M%S.txt")
        try:
            with open(os.path.join(APP, name), "w", encoding="utf-8") as f:
                f.write("\n".join(keys) + "\n")
        except Exception:
            name = ""
        self.copy("\n".join(keys))
        return {"ok": True, "created": res, "file": name, "first": keys[0]}

    def admin_shop_save(self, vals):
        try:
            self._adm()
            vals = {k: str(v).strip() for k, v in dict(vals).items() if k in lic.SHOP_DEFAULTS}
            bad = [k for k, v in vals.items() if k.startswith("url_") and v and not v.startswith("https://")]
            if bad:
                return {"ok": False, "error": "ссылка должна начинаться с https://: " + ", ".join(bad)}
            changed = {k: v for k, v in vals.items() if v != str(self._shop.get(k, ""))}
            for k, v in changed.items():
                lic.admin_set_config(k, v)
            cfg = lic.get_config()
            miss = [k for k, v in changed.items() if str(cfg.get(k, "")) != v]
            self._shop.update(cfg)
            self._rev += 1
            if miss:
                return {"ok": False, "error": "сервер не принял: " + ", ".join(miss)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "changed": len(changed)}

    def admin_release(self, version, file, notes):
        try:
            self._adm()
            version, file = str(version).strip(), str(file).strip()
            if not version or not file:
                return {"ok": False, "error": "заполни версию и имя файла"}
            url = file if file.startswith("http") else lic.storage_url(file)
            import urllib.request
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "AfkToken"})
            try:
                urllib.request.urlopen(req, timeout=15).close()
            except Exception as e:
                return {"ok": False, "error": f"файл не открывается по ссылке ({e}). Проверь имя файла и что "
                                              "папка releases публичная"}
            lic.admin_release(version, str(notes or "").strip(), url)
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True}

    # ---------- онлайн-гейт: та же логика, что в классическом окне ----------
    def _gate_loop(self):
        try:
            while self._bot.running:
                for _ in range(int(lic.HEARTBEAT_MIN * 60)):
                    if not self._bot.running:
                        return
                    time.sleep(1)
                res, net_err = None, False
                try:
                    res = lic.session(False)
                except lic.NetworkError:
                    net_err = True
                except Exception:
                    res = None
                result = res if isinstance(res, dict) else None
                d = lic.gate_decide(time.time(), self._gate_last_ok, result, net_err, lic.local_license())
                if d.startswith("tier:") or d.startswith("emergency:"):
                    if d.startswith("tier:"):
                        self._gate_last_ok = time.time()
                    if d.startswith("emergency:"):
                        self._tier = d.split(":", 1)[1]          # без сервера: только бесплатное
                    else:
                        self._tier = "ultimate" if self._admin else d.split(":", 1)[1]
                    self._bot.tier = self._tier
                    self._bot.vip = self._tier != "free"
                    if self._gate_paused:
                        self._gate_paused = False
                        self._bot.paused = False
                        self._on_state("running")
                        self._log("🌐 Связь с сервером вернулась, продолжаю")
                elif d in ("stop_banned", "stop_invalid"):
                    self._log("⛔ Ключ заблокирован, останавливаю" if d == "stop_banned"
                              else "⛔ Ключ не прошёл проверку, останавливаю")
                    self._key = None
                    self._key_lost = True
                    self._rev += 1
                    self._bot.stop()
                    return
                elif d == "pause_offline" and not self._gate_paused:
                    self._gate_paused = True
                    self._bot.paused = True
                    self._on_state("paused")
                    self._log("🌐 Нет связи с сервером, жду")
        finally:
            self._gate_running = False


def ensure_webview():
    """pywebview есть? Нет — ставим один раз. Не вышло — сутки не пробуем (классическое окно)."""
    try:
        import webview  # noqa: F401
        return True
    except Exception:
        pass
    if getattr(sys, "frozen", False):
        return False
    try:
        if os.path.exists(NO_GLASS_MARK) and time.time() - os.path.getmtime(NO_GLASS_MARK) < 86400:
            return False
    except Exception:
        pass
    print("Ставлю компонент нового интерфейса (pywebview), один раз...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pywebview"], check=True, timeout=900)
        import webview  # noqa: F401
        return True
    except Exception as e:
        print("Не получилось поставить pywebview:", e)
        try:
            with open(NO_GLASS_MARK, "w", encoding="utf-8") as f:
                f.write(str(e))
        except Exception:
            pass
        return False


def run():
    """Открывает стеклянное окно. Возвращает False, если его показать нельзя (тогда — классическое)."""
    if not os.path.exists(UI_INDEX) or not ensure_webview():
        return False
    import webview
    threading.Thread(target=bot_core.fix_ssl, daemon=True).start()
    api = Api()
    title = f"{APP_NAME} {APP_VERSION}" + (" β" if classic.BETA else "")
    try:
        webview.create_window(title, UI_INDEX, js_api=api, width=1024, height=690, resizable=False,
                              background_color="#120a22")
        webview.start(gui="edgechromium")
    except Exception as e:
        api._log(f"Новый интерфейс не открылся ({e}), открываю классический")
        if api._bg_started:          # окно уже работало — второе открывать нельзя
            os._exit(1)
        return False
    api._bot.stop()
    time.sleep(0.5)
    os._exit(0)


if __name__ == "__main__":
    if not run():
        classic.App().mainloop()
