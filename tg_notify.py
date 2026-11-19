# -*- coding: utf-8 -*-
"""Отправка уведомлений в Telegram через своего бота (@BotFather)."""
import json
import urllib.error
import urllib.request
import uuid

API = "https://api.telegram.org/bot{token}/{method}"


class TgError(Exception):
    pass


def _call(token, method, data=None, files=None, timeout=20):
    url = API.format(token=token.strip(), method=method)
    if files:
        boundary = uuid.uuid4().hex
        body = b""
        for k, v in (data or {}).items():
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n"
                     f"{v}\r\n").encode("utf-8")
        for k, (fname, content, ctype) in files.items():
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; "
                     f"filename=\"{fname}\"\r\nContent-Type: {ctype}\r\n\r\n").encode("utf-8")
            body += content + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    else:
        req = urllib.request.Request(url, data=json.dumps(data or {}).encode("utf-8"),
                                     method="POST")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            res = json.loads(e.read())
        except Exception:
            raise TgError(f"HTTP {e.code}")
    except Exception as e:
        raise TgError(f"Нет связи с Telegram: {e}")
    if not res.get("ok"):
        desc = res.get("description", "ошибка")
        if "Unauthorized" in desc or "Not Found" in desc:
            desc = "Неверный токен бота"
        elif "chat not found" in desc:
            desc = "Chat ID не найден — открой своего бота и нажми Start"
        raise TgError(desc)
    return res.get("result")


def send_text(token, chat_id, text):
    return _call(token, "sendMessage", {"chat_id": chat_id, "text": text[:4000]})


def send_menu(token, chat_id, text, rows):
    """Сообщение с кнопками-пультом внизу чата (Premium)."""
    kb = {"keyboard": [[{"text": t} for t in r] for r in rows], "resize_keyboard": True,
          "is_persistent": True}
    return _call(token, "sendMessage", {"chat_id": chat_id, "text": text[:4000], "reply_markup": kb})


def send_photo(token, chat_id, jpg_bytes, caption=""):
    return _call(token, "sendPhoto", {"chat_id": chat_id, "caption": caption[:1000]},
                 files={"photo": ("reward.jpg", jpg_bytes, "image/jpeg")})


def find_chat_id(token):
    """Берёт chat id из последнего сообщения, которое написали боту."""
    upd = _call(token, "getUpdates", {"limit": 50}) or []
    for u in reversed(upd):
        msg = u.get("message") or u.get("my_chat_member") or {}
        chat = msg.get("chat")
        if chat and chat.get("type") == "private":
            name = chat.get("username") or chat.get("first_name") or ""
            return str(chat["id"]), name
    raise TgError("Не вижу сообщений. Открой своего бота в Telegram, нажми Start "
                  "(или напиши ему что угодно) и попробуй снова")


def get_updates(token, offset=None, timeout=25):
    data = {"timeout": timeout, "allowed_updates": ["message"]}
    if offset is not None:
        data["offset"] = offset
    return _call(token, "getUpdates", data, timeout=timeout + 15) or []


def set_commands(token):
    cmds = [{"command": "status", "description": "Статус и статистика бота"},
            {"command": "screen", "description": "Скрин экрана"},
            {"command": "start", "description": "Запустить бота"},
            {"command": "stop", "description": "Остановить бота"},
            {"command": "pause", "description": "Пауза / продолжить"},
            {"command": "menu", "description": "♛ Кнопки-пульт (Premium)"},
            {"command": "goal", "description": "♛ Прогресс цели (Premium)"},
            {"command": "help", "description": "Список команд"}]
    return _call(token, "setMyCommands", {"commands": cmds})
