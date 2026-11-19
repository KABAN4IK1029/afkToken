# -*- coding: utf-8 -*-
"""Система ключей Afk token (сервер - Supabase). Ключи навсегда, 1 ключ = 1 компьютер."""
import hashlib
import json
import os
import platform
import sys
import time
import urllib.error
import urllib.request
import uuid

# Данные сервера берутся из server_config.py (этот файл обновления не трогают).
# Если его нет - используются строки ниже (старый способ).
SUPABASE_URL = "https://XXXXXXXX.supabase.co"
SUPABASE_KEY = "ВСТАВЬ_СЮДА_PUBLISHABLE_ИЛИ_ANON_KEY"
try:
    import server_config as _sc
    if "XXXXXXXX" not in _sc.SUPABASE_URL and "ВСТАВЬ" not in _sc.SUPABASE_KEY:
        SUPABASE_URL, SUPABASE_KEY = _sc.SUPABASE_URL, _sc.SUPABASE_KEY
except Exception:
    pass

RELEASES_BUCKET = "releases"

APP_VERSION = "1.0"
OFFLINE_DAYS = 3   # сколько дней программа работает без интернета после последней проверки
TG_URL = "https://t.me/kk4ose"


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


LICENSE_FILE = os.path.join(app_dir(), "license.json")


class NetworkError(Exception):
    pass


class ServerError(Exception):
    pass


def configured():
    return "XXXXXXXX" not in SUPABASE_URL and "ВСТАВЬ" not in SUPABASE_KEY


def get_hwid():
    """Код компьютера: XXXX-XXXX-XXXX-XXXX (не меняется при переустановке программы)."""
    raw = None
    try:
        import winreg
        k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography",
                           0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
        raw = winreg.QueryValueEx(k, "MachineGuid")[0]
    except Exception:
        raw = f"{uuid.getnode()}|{platform.node()}"
    h = hashlib.sha256(("afk-token|" + raw).encode()).hexdigest().upper()
    return "-".join(h[i:i + 4] for i in range(0, 16, 4))


def pc_name():
    return platform.node()[:64]


def rpc(name, params, timeout=15):
    if not configured():
        raise ServerError("Сервер ключей не настроен (license_client.py)")
    req = urllib.request.Request(
        f"{SUPABASE_URL.rstrip('/')}/rest/v1/rpc/{name}",
        data=json.dumps(params).encode("utf-8"), method="POST")
    req.add_header("apikey", SUPABASE_KEY)
    req.add_header("Content-Type", "application/json")
    if SUPABASE_KEY.startswith("eyJ"):
        req.add_header("Authorization", "Bearer " + SUPABASE_KEY)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        if e.code in (408, 429, 500, 502, 503, 504):   # сервер временно недоступен — это НЕ фатально
            raise NetworkError(f"HTTP {e.code}")
        body = e.read().decode("utf-8", "ignore")
        try:
            msg = json.loads(body).get("message") or body
        except Exception:
            msg = body
        raise ServerError(msg[:200])
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise NetworkError(str(e))


# ---------- локальное сохранение ----------
# В license.json хранится только сам ключ и привязка к ПК. Уровень (Premium / Ultimate)
# и админка программа берёт ТОЛЬКО из ответа сервера, файлу не доверяет: правка файла
# ничего не даёт. Без связи с сервером работает максимум бесплатный уровень.
last_tier = "free"   # уровень из последнего ответа сервера (или "free" без связи)


def load_saved():
    try:
        with open(LICENSE_FILE, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, dict) or not data.get("key"):
        return None
    if data.get("hwid") and data.get("hwid") != get_hwid():
        return None
    return {"key": str(data["key"]), "hwid": data.get("hwid"),
            "last_ok": float(data.get("last_ok") or 0), "expires_at": data.get("expires_at")}


def save(data):
    keep = {k: data.get(k) for k in ("key", "hwid", "last_ok", "expires_at")}
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(keep, f)


def forget():
    try:
        os.remove(LICENSE_FILE)
    except Exception:
        pass


# ---------- проверка ----------
def activate(key, start=True):
    """Возвращает {'ok':bool, 'admin':bool, 'error':str, 'offline':bool}."""
    global last_tier
    key = key.strip().upper()
    hwid = get_hwid()
    try:
        res = rpc("afk_check", {"p_key": key, "p_hwid": hwid, "p_pc": pc_name(),
                                "p_ver": APP_VERSION, "p_start": start})
    except NetworkError:
        saved = load_saved()
        if (saved and saved.get("key") == key and saved.get("hwid") == hwid
                and time.time() - saved.get("last_ok", 0) < OFFLINE_DAYS * 86400
                and not _expired(saved.get("expires_at"))):
            last_tier = "free"          # без сервера только бесплатные функции
            return {"ok": True, "admin": False, "offline": True,
                    "expires_at": saved.get("expires_at"), "tier": "free"}
        return {"ok": False, "error": "Нет связи с сервером ключей. Проверь интернет."}
    except ServerError as e:
        return {"ok": False, "error": str(e)}
    res = res or {}
    if res.get("ok"):
        tier = res.get("tier") or ("premium" if res.get("admin") else "vip")
        last_tier = "ultimate" if res.get("admin") else tier
        save({"key": key, "hwid": hwid, "last_ok": time.time(), "expires_at": res.get("expires_at")})
        return {"ok": True, "admin": bool(res.get("admin")), "offline": False,
                "expires_at": res.get("expires_at"), "tier": tier}
    if res.get("expired") or (res.get("error") and "заблок" in res.get("error", "").lower()):
        forget()
    return {"ok": False, "error": res.get("error") or "Ключ не подходит",
            "expired": bool(res.get("expired"))}


def _expired(iso):
    if not iso:
        return False
    try:
        from datetime import datetime, timezone
        return datetime.fromisoformat(iso.replace("Z", "+00:00")) < datetime.now(timezone.utc)
    except Exception:
        return False


# ---------- реферальная система ----------
def ref_me():
    """Мой реф-код и статистика: {code, invited, pending, rewarded}."""
    return rpc("afk_ref_me", {"p_hwid": get_hwid(), "p_pc": pc_name()})


def ref_use(code, key):
    """Засчитать покупку VIP другу, который дал реф-код."""
    return rpc("afk_ref_use", {"p_code": code.strip().upper(), "p_key": key.strip().upper(),
                               "p_hwid": get_hwid()})


def ref_claim():
    """Забрать награду (7 дней VIP за друга). Возвращает {ok, key, days} или {ok:false, error}."""
    saved = load_saved() or {}
    return rpc("afk_ref_claim", {"p_hwid": get_hwid(), "p_key": saved.get("key") or None})


# ---------- админ ----------
def _admin_args():
    saved = load_saved() or {}
    return {"p_key": saved.get("key", ""), "p_hwid": get_hwid()}


def admin_list():
    return rpc("afk_admin_list", _admin_args()) or []


def admin_action(target, action, note=None):
    args = _admin_args()
    args.update({"p_target": target, "p_action": action, "p_note": note})
    return rpc("afk_admin_action", args)


def admin_add_timed(new_key, days, note=None):
    args = _admin_args()
    args.update({"p_new": new_key, "p_days": int(days), "p_note": note})
    return rpc("afk_admin_add_timed", args)


def admin_add_keys(keys):
    args = _admin_args()
    args["p_keys"] = keys
    return rpc("afk_admin_add", args)


# ---------- обновления ----------
def latest_release():
    """Последний релиз с сервера (для всех, кроме заблокированных ключей) или None."""
    saved = load_saved() or {}
    return rpc("afk_latest_release", {"p_key": saved.get("key") or None, "p_hwid": get_hwid()},
               timeout=10)


def storage_url(file_name):
    """Публичная ссылка на файл в Supabase Storage (папка releases)."""
    from urllib.parse import quote
    return f"{SUPABASE_URL.rstrip('/')}/storage/v1/object/public/{RELEASES_BUCKET}/{quote(file_name)}"


def admin_release(version, notes, file_url):
    args = _admin_args()
    args.update({"p_version": version, "p_notes": notes, "p_file_url": file_url})
    return rpc("afk_admin_release", args)


def new_key():
    import secrets
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "AFK-" + "-".join("".join(secrets.choice(alphabet) for _ in range(4))
                             for _ in range(4))


# ---------- пользователи и чат (1.3) ----------
def _my_key():
    return (load_saved() or {}).get("key") or None


def ping(start=False, running=False):
    """Отметка «я онлайн» — видна в админке (и бесплатные, и VIP)."""
    return rpc("afk_ping", {"p_hwid": get_hwid(), "p_pc": pc_name(), "p_ver": APP_VERSION,
                            "p_key": _my_key(), "p_start": bool(start), "p_running": bool(running)},
               timeout=10)


def chat_fetch(after=0):
    return rpc("afk_chat_fetch", {"p_hwid": get_hwid(), "p_after": int(after or 0)}, timeout=10)


def chat_send(text):
    return rpc("afk_chat_send", {"p_hwid": get_hwid(), "p_key": _my_key(), "p_text": text}, timeout=10)


def chat_set_nick(nick):
    return rpc("afk_chat_set_nick", {"p_hwid": get_hwid(), "p_key": _my_key(), "p_nick": nick})


def admin_users():
    return rpc("afk_admin_users", _admin_args()) or []


def admin_chat(action, msg=None, target=None):
    args = _admin_args()
    args.update({"p_action": action, "p_msg": msg, "p_target": target})
    return rpc("afk_admin_chat", args)


# ---------- Premium / магазин (1.4) ----------
SHOP_DEFAULTS = {"price_vip": "79", "price_premium": "159", "price_upgrade": "99",
                 "url_vip": "https://starvell.com/offers/0fc3f238-0ce6-4a13-98e8-262b6ad640c9",
                 "url_premium": "", "url_upgrade": "",
                 "price_ultimate": "249", "url_ultimate": ""}


def get_config():
    """Цены и ссылки магазина (меняются из админки). Без сервера - значения по умолчанию."""
    cfg = dict(SHOP_DEFAULTS)
    try:
        res = rpc("afk_get_config", {}, timeout=8) or {}
        cfg.update({k: v for k, v in res.items() if v is not None})
    except Exception:
        pass
    return cfg


def admin_set_config(k, v):
    args = _admin_args()
    args.update({"p_k": k, "p_v": v})
    return rpc("afk_admin_set_config", args)


# ---------- предложения / тикеты (1.6) ----------
def sug_send(kind, title, body, tier=None):
    return rpc("afk_sug_send", {"p_hwid": get_hwid(), "p_key": _my_key(), "p_kind": kind,
                                "p_title": title, "p_body": body, "p_tier": tier}, timeout=12)


def sug_mine():
    return rpc("afk_sug_mine", {"p_hwid": get_hwid()}, timeout=10) or []


def admin_sug_list():
    return rpc("afk_admin_sug_list", _admin_args(), timeout=12) or []


def admin_sug_update(sid, status, reply=None):
    args = _admin_args()
    args.update({"p_id": int(sid), "p_status": status, "p_reply": reply})
    return rpc("afk_admin_sug_update", args, timeout=12)


# ---------- личные сообщения от создателя (1.6.1) ----------
def msg_fetch():
    """Непрочитанные сообщения для моего ключа — показываются при запуске."""
    key = _my_key()
    if not key:
        return []
    return rpc("afk_msg_fetch", {"p_key": key, "p_hwid": get_hwid()}, timeout=10) or []


def msg_read(mid):
    return rpc("afk_msg_read", {"p_key": _my_key(), "p_hwid": get_hwid(), "p_id": int(mid)}, timeout=10)


def admin_msg_send(target, body):
    args = _admin_args()
    args.update({"p_target": target, "p_body": body})
    return rpc("afk_admin_msg_send", args, timeout=12)


def admin_msg_list(target):
    args = _admin_args()
    args["p_target"] = target
    return rpc("afk_admin_msg_list", args, timeout=12) or []


def admin_msg_delete(mid):
    args = _admin_args()
    args["p_id"] = int(mid)
    return rpc("afk_admin_msg_delete", args, timeout=12)


def admin_add_tier(keys, tier, note=None):
    args = _admin_args()
    args.update({"p_keys": keys, "p_tier": tier, "p_note": note})
    return rpc("afk_admin_add_tier", args)


# ---------- онлайн-гейт (1.5): бот не работает без «ок» сервера ----------
HEARTBEAT_MIN = 4       # как часто бот переспрашивает сервер, пока работает
GATE_GRACE_MIN = 30     # обычный обрыв связи терпим столько минут
EMERGENCY_DAYS = 7      # если СЕРВЕР лёг надолго — честный ключ работает ещё столько дней


def session(start=False):
    """Разрешение на работу бота от сервера. Возвращает dict или бросает NetworkError."""
    key = _my_key()
    hwid = get_hwid()
    if not key:
        return {"ok": False, "reason": "no_key", "error": "Нет ключа"}
    try:
        res = rpc("afk_session", {"p_key": key, "p_hwid": hwid, "p_ver": APP_VERSION,
                                  "p_start": bool(start)}, timeout=12)
    except ServerError as e:
        # Сервер ОТВЕТИЛ, но afk_session нет или она с ошибкой (например, не выполнен
        # supabase_v15.sql). Это не «сервер недоступен» — проверяем ключ старой функцией.
        global last_session_error
        last_session_error = str(e)[:160]
        r = rpc("afk_check", {"p_key": key, "p_hwid": hwid, "p_pc": pc_name(),
                              "p_ver": APP_VERSION, "p_start": bool(start)}, timeout=12) or {}
        if r.get("ok"):
            tier = r.get("tier") or ("premium" if r.get("admin") else "vip")
            return {"ok": True, "tier": tier, "admin": bool(r.get("admin")), "legacy": True}
        err = r.get("error") or "Ключ не подходит"
        if "заблок" in err.lower():
            reason = "banned"
        elif r.get("expired"):
            reason = "expired"
        else:
            reason = "not_found"
        return {"ok": False, "reason": reason, "error": err}
    return res or {"ok": False, "reason": "empty"}


last_session_error = ""   # последняя ошибка afk_session (для журнала)


def admin_unlock_share(target_key):
    args = _admin_args()
    args["p_target"] = target_key
    return rpc("afk_admin_unlock_share", args)


def local_license():
    """Сохранённый ключ для аварийного режима, когда СЕРВЕР недоступен.
    В аварийном режиме работают только бесплатные функции: уровень без сервера не подтвердить."""
    saved = load_saved()
    if not saved or not saved.get("key"):
        return None
    if time.time() - saved.get("last_ok", 0) > EMERGENCY_DAYS * 86400:
        return None
    if _expired(saved.get("expires_at")):
        return None
    return {"tier": "free"}


def gate_decide(now, last_ok, result, net_error, local=None):
    """Чистая логика гейта (без сети/UI — чтобы тестировать).
    result — ответ session() или None. net_error — обрыв связи. local — local_license() или None.
    Ответы: 'tier:<x>' | 'stop_banned' | 'stop_invalid' | 'emergency:<x>' | 'pause_offline' | 'run'.
    """
    if result and result.get("ok"):
        return "tier:" + (result.get("tier") or "vip")
    # сервер ОТВЕТИЛ и сказал «нет» — это не авария, а реальный запрет
    if result and result.get("reason") == "banned":
        return "stop_banned"
    if result and result.get("reason") in ("not_found", "not_activated", "expired", "other_pc", "no_key"):
        return "stop_invalid"
    # сервер НЕ ответил (обрыв связи / пусто)
    if net_error or result is None or result.get("reason") == "empty":
        if now - last_ok <= GATE_GRACE_MIN * 60:
            return "run"                       # короткий сбой — работаем дальше
        if local:                              # сервер лёг надолго, но ключ честный → аварийный режим
            return "emergency:" + local["tier"]
        return "pause_offline"
    return "run"
