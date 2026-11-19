# -*- coding: utf-8 -*-
"""Ядро AFK-бота для Fortnite. Читает текст на экране (EasyOCR) и жмёт кнопки."""
import ctypes
import json
import difflib
import os
import random
import re
from collections import deque
import sys
import threading
import time
import traceback

def _dpi_aware():
    """Без этого при масштабе Windows 125/150% (почти все ноутбуки) скриншот в реальных
    пикселях, а мышь — в «уменьшенных»: бот видел «Играть», но кликал мимо."""
    try:
        import ctypes as _c
        try:
            _c.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            _c.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


_dpi_aware()

import vision


def app_dir():
    """Папка программы (рядом с exe или с исходником) — туда пишем rewards/, dataset/."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def save_image(path, img, ext=".png", quality=90):
    """cv2.imwrite не умеет русские буквы в пути на Windows — пишем через imencode."""
    import cv2
    params = [cv2.IMWRITE_JPEG_QUALITY, quality] if ext == ".jpg" else []
    ok, buf = cv2.imencode(ext, img, params)
    if ok:
        buf.tofile(path)
    return ok

DEFAULTS = {
    "auto_play": True,       # запускать катки (Отряды)
    "launch_mode": "lobby",  # lobby = через лобби, replay = кнопка "Играть снова"
    "auto_leave": True,      # выходить из матча в лобби
    "skip_rewards": True,    # забирать награды / закрывать окна
    "auto_restart": True,    # перезапуск игры при ошибках / зависании
    "auto_jump": True,       # прыжок из автобуса
    "jump_delay": 10,
    "anti_afk": True,        # зажимать W
    "afk_hold": 30,          # сколько секунд держать W
    "afk_pause": 30,         # пауза между зажатиями, сек
    "max_match_min": 35,
    "stuck_min": 15,
    "scan_scale": 0.5,       # масштаб снимка для чтения текста (меньше = быстрее)
    "scan_interval": 1.0,    # пауза между проверками экрана, сек
    "tg_enabled": False,     # присылать награды в Telegram
    "tg_token": "",
    "tg_chat": "",
    "tg_photo": True,
    "tg_reports": True,      # периодические отчёты
    "report_min": 60,        # раз в сколько минут
    "tg_match": False,       # сообщать о каждой катке
    "explore": True,         # «Бег»: ходить по карте (без него бот стоит после приземления)
    "explore_delay": 90,     # максимум ждать приземления, сек (обычно поиск стартует сразу после посадки)
    "turn_speed": 800,       # чувствительность поворота камеры
    "auto_update": True,     # обновлять программу автоматически
    "tray_on_close": True,   # крестик сворачивает в трей
    "autostart": False,      # запускать вместе с Windows
    "autorun_bot": False,    # сразу запускать бота при старте программы
    "tg_control": True,      # управление ботом командами из Telegram
    "token_alert": True,     # громкое уведомление, если выпал Пиратский токен
    "auto_pause": True,      # пауза, когда человек сел за ПК
    "resume_min": 3,         # продолжить, если человека нет N минут
    "monitor_off": False,    # гасить монитор во время работы
    "fps_limit": 0,          # ограничение FPS игры (0 = не трогать)
    "fps_backup": "",        # прежнее значение FPS (для возврата)
    "skip_version": "",      # версия, которую пользователь пропустил
    # ----- PREMIUM -----
    "tg_menu": True,         # кнопки-пульт в Telegram
    "shot_every": 0,         # авто-скрин в Telegram раз в N минут (0 - выкл)
    "goal_on": False,        # фарм под цель
    "goal_type": "matches",  # matches / rewards / chests / token
    "goal_value": 20,
    "goal_action": "stop",   # stop / close / shutdown
    "sched_on": False,       # расписание
    "sched_from": "23:00",
    "sched_to": "07:00",
    "sched_days": "1234567", # дни недели (1 = пн)
    "land_mode": False,      # точка высадки
    "land_spot": "mid",      # start / mid / end / random
    "low_gfx": False,        # низкая графика на время фарма
    "gfx_backup": "",
    "net_guard": True,       # пропал интернет - ждать, не жать кнопки
    "human_afk": False,      # анти-кик: движения как у человека
    "weekly_report": False,  # еженедельный отчёт-картинка в Telegram
    "theme": "sakura",       # тема оформления
    "user_profiles": {},     # свои профили настроек
    "fun_log": True,         # живые реплики бота в логе (прикол, на работу не влияет)
    # ---- 1.6 ----
    "mouse_style": "smooth",  # smooth = плавно как человек, sharp = резко (как раньше)
    "team_size": "squads",    # solo / duos / trios / squads — что выбирать в лобби
    "sprint": True,           # иногда зажимать Shift (спринт), стрейфы
    "zone_nav": True,         # компас + миникарта: не лезть в воду (и в шторм, если storm_nav)
    "storm_nav": True,        # уходить от шторма по цвету миникарты (выключается в настройках)
    "team_check": True,       # рестарт, когда в команде никого не осталось
    "team_calibrated": True,  # панель откалибрована по реальному HUD (1.6)
    "reward_shots": True,     # скрин награды в папку rewards и в Telegram
    "dataset_capture": False, # (админ) сохранять кадры для обучения нейросети
    "dataset_every": 4,
    "scan_every": 35,         # раз во сколько секунд оглядываться в поисках сундука
    "scan_turns": 2,          # сколько поворотов за один осмотр       # раз во сколько секунд сохранять кадр
    "yolo_conf": 0.45,        # уверенность нейросети
    # области экрана (доли ширины/высоты) — калибруются под HUD
    "compass_box": [0.34, 0.0, 0.68, 0.045],
    "minimap_box": [0.889, 0.022, 0.986, 0.178],
    "team_box": [0.0, 0.62, 0.24, 0.98],
    "cpd": 0.0,               # единиц мыши на 1° поворота (0 = откалибровать в игре)
    # ----- ULTIMATE (1.6) -----
    "obstacle_nav": True,     # умный обход препятствий: прыжок -> в сторону -> разворот
    "smooth_mouse": True,     # плавная мышь, как у живого игрока
    # служебные отметки (без них в DEFAULTS они не сохранялись в settings.json)
    "shop_seen": False,           # магазин уже показывали при первом запуске
    "premium_offer_seen": False,  # окно «Новая привилегия: Premium» уже показывали
    "last_weekly": "",            # неделя, за которую уже ушёл еженедельный отчёт
}

TEAM_SIZE_WORDS = {
    "solo": ["соло", "solo"],
    "duos": ["дуэты", "дуэт", "дуо", "duos", "duo"],
    "trios": ["трио", "trios"],
    "squads": ["отряды", "отряд", "squads", "squad"],
}

# корни слов размера команды на кнопке режима в новом лобби («Нулевая высота, Одиночки»)
TEAM_SIZE_ROOTS = {
    "solo": ("одиноч", "соло", "solo"),
    "duos": ("дуэт", "дуо", "duo"),
    "trios": ("трио", "trio"),
    "squads": ("отряд", "squad"),
}
MODE_OK_WORDS = ["подтвердить", "применить", "готово", "сохранить", "принять",
                 "confirm", "apply", "done", "save", "accept"]


def size_of(text):
    for size, roots in TEAM_SIZE_ROOTS.items():
        if any(r in text for r in roots):
            return size
    return None


# «характер» бота — редкие живые реплики. Чисто косметика.
QUIP_CHEST = [
    "а вот и лутик 📦", "хозяйке на заметку: ещё один сундук",
    "мне, мне, всё мне 😏", "богатею пока ты спишь 💰",
    "лутаю как не в себя", "ещё один в коллекцию 🤑",
]
QUIP_MATCH = [
    "катка в кармане, погнали дальше 🫡", "гг, следующая 🎮",
    "не устал, не вспотел 😎", "фарм не спит 🌙",
    "ещё одна в копилку 🏆",
]
QUIP_TOKEN = [
    "ВОТ ЭТО УДАЧА 🏴‍☠️🔥", "джекпот, босс! 🤩", "лови редкость, не моргай ✨",
]

# функции бесплатной версии (остальное - VIP)
FREE_FEATURES = {"auto_play", "auto_jump", "auto_pause"}
# функции только для Premium
PREMIUM_FEATURES = {"tg_menu", "goal_on", "sched_on", "land_mode", "low_gfx", "net_guard",
                    "human_afk", "weekly_report"}
# функции только для Ultimate (и уровни, которым открыт Premium)
ULTIMATE_FEATURES = {"obstacle_nav", "smooth_mouse", "zone_nav", "team_check",
                     "auto_leave", "low_gfx", "land_mode", "sprint"}   # с 1.6 только Ultimate
PREMIUM_TIERS = ("premium", "ultimate")
GOAL_STAT = {"matches": "matches", "rewards": "rewards", "chests": "chests", "token": "tokens"}
GOAL_NAMES = {"matches": "катки", "rewards": "награды", "chests": "сундуки", "token": "Пиратский токен"}
LAND_DELAY = {"start": (1, 3), "mid": (16, 22), "end": (32, 38)}

FORTNITE_PROC = "FortniteClient-Win64-Shipping.exe"
LAUNCH_URL = "com.epicgames.launcher://apps/Fortnite?action=launch&silent=true"
LAUNCH_WAIT = 120

# (имя, слова, область (x1,y1,x2,y2) в долях экрана, функция-переключатель)
BUTTONS = [
    ("play_again", ["играть снова", "играть еще", "играть еще раз", "сыграть снова",
                    "сыграть еще", "play again", "requeue", "ready up again"],
     (0, 0, 1, 1), "auto_play"),
    ("return_lobby", ["вернуться в лобби", "в лобби", "выйти в лобби",
                      "return to lobby", "back to lobby"], (0, 0, 1, 1), "auto_leave"),
    ("claim", ["забрать", "забрать награду", "забрать награды", "забрать все",
               "получить", "получить все", "получить награду", "claim all",
               "collect all", "claim", "claim reward", "claim rewards", "collect"],
     (0, 0.3, 1, 1), "skip_rewards"),
    ("continue", ["продолжить", "continue"], (0, 0.3, 1, 1), "skip_rewards"),
    ("close", ["закрыть", "close", "пропустить", "skip"], (0, 0, 1, 1), "skip_rewards"),
    ("play", ["играть", "play"], (0, 0.6, 1, 1), "auto_play"),
]
LEAVE_WORDS = ["покинуть матч", "выйти из матча", "в лобби", "вернуться в лобби",
               "leave match", "return to lobby", "leave game"]
CONFIRM_WORDS = ["да", "подтвердить", "покинуть", "yes", "confirm", "leave"]
# подсказки, которые видны только в воздухе (свободное падение / дельтаплан)
AIR_WORDS = ["свободное", "падение", "дельтаплан", "раскрыть", "skydiv", "glider", "deploy", "freefall"]
CHEST_WORDS = ["открыть", "обыскать", "сундук", "search", "open", "chest"]
LOOT_WORDS = ["подобрать", "взять", "pick up", "pickup"]
DEAD_WORDS = ["режим зрителя", "наблюдение", "наблюдаете", "spectating", "вы заняли", "вы выбыли", "вас устранил",
              "eliminated by"]
# экран выпадения Пиратского токена
TOKEN_WORDS = ["пиратский магазин", "пиратскому магазину", "доступ к пиратскому", "pirate shop"]
PLAY_WORDS = ["играть", "play"]
CANCEL_PARTS = ("отмен", "cancel", "поиск", "подбор", "matchmak", "ожидан")
# новое лобби Fortnite (лента режимов внизу)
LOBBY_WORDS = ["текущий выбор", "current selection", "сокровище", "шкафчик", "locker",
               "пропуска", "задания", "карьера", "состязания", "магазин", "item shop", "quests"]
BR_WORDS = ["королевская битва", "battle royale", "батл рояль", "королевская"]
START_WORDS = ["играть", "play", "выбрать", "select", "запустить", "launch", "начать", "start",
               "готов", "ready", "в бой", "присоединиться", "join"]
# экран итогов матча: тут есть «Духи», «Найдено сокровище» — это НЕ лобби, Esc тут жать нельзя
RESULT_WORDS = ["итоги матча", "статистика матча", "вы заняли", "match summary", "match stats",
                "you placed", "до следующего уровня"]
SEARCH_PARTS = ("поиск", "подбор", "matchmak", "отмен", "cancel", "ожидан", "searching")
JUMP_WORDS = ["прыгнуть", "прыгнуть из автобуса", "выпрыгнуть", "прыжок",
              "высадиться", "jump", "jump from bus"]


# ================= защита ввода: клавиши и мышь только в окно Fortnite =================
_FN = {"h": None, "t": 0.0}


def fortnite_hwnd():
    """Окно Fortnite (кэш 2 сек) или None, если игра не открыта."""
    if time.time() - _FN["t"] < 2.0:
        return _FN["h"]
    found = []
    try:
        user32 = ctypes.windll.user32

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                n = user32.GetWindowTextLengthW(hwnd)
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    user32.GetWindowTextW(hwnd, buf, n + 1)
                    if buf.value.strip() == "Fortnite":
                        found.append(hwnd)
                        return False
            return True

        user32.EnumWindows(cb, 0)
    except Exception:
        pass
    _FN["h"], _FN["t"] = (found[0] if found else None), time.time()
    return _FN["h"]


def game_active():
    """True — можно жать: Fortnite спереди (или игры нет вообще — запуск через лаунчер)."""
    h = fortnite_hwnd()
    if not h:
        return True
    try:
        return int(ctypes.windll.user32.GetForegroundWindow() or 0) == int(h)
    except Exception:
        return True


def _win_scale():
    """Во сколько раз настоящие пиксели экрана больше тех, что Windows отдаёт окнам
    (масштаб 125/150%). Скриншот и клики бота — в настоящих пикселях."""
    try:
        user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
        hdc = user32.GetDC(0)
        real = gdi32.GetDeviceCaps(hdc, 118)          # DESKTOPHORZRES — всегда настоящие
        user32.ReleaseDC(0, hdc)
        seen = user32.GetSystemMetrics(0)
        return (real / float(seen)) if real and seen else 1.0
    except Exception:
        return 1.0


def _rect_of(h):
    from ctypes import wintypes
    r = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(h, ctypes.byref(r))
    k = _win_scale()
    return int(r.left * k), int(r.top * k), int(r.right * k), int(r.bottom * k)


def game_rect():
    h = fortnite_hwnd()
    if not h:
        return None
    try:
        return _rect_of(h)
    except Exception:
        return None


def on_taskbar(x, y):
    """Точка на панели задач Windows (там «Поиск» и Пуск) — туда не кликаем никогда."""
    try:
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        for cls in ("Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
            h = user32.FindWindowW(cls, None)
            if not h or not user32.IsWindowVisible(h):
                continue
            l, t, rr, b = _rect_of(h)
            if l <= x <= rr and t <= y <= b and (b - t) < 400:
                return True
    except Exception:
        pass
    return False


class SafeInput:
    """Обёртка над pydirectinput: если спереди не Fortnite (поиск Windows, Пуск, браузер),
    клавиши НЕ нажимаются — иначе W/A/D/пробел печатались в поиск. Отпускать можно всегда."""

    def __init__(self, pdi, bot):
        self._p, self._bot, self._warn = pdi, bot, 0.0

    def __getattr__(self, name):
        return getattr(self._p, name)

    def _ok(self):
        if game_active():
            return True
        try:
            self._bot.focus_game()          # пробуем вернуть игру вперёд (поиск/Пуск закроются)
        except Exception:
            pass
        _FN["t"] = 0.0
        if game_active():
            return True
        if time.time() - self._warn > 30:
            self._warn = time.time()
            self._bot.log("⏸ Спереди не Fortnite — клавиши не жму, чтобы не печатать в другие окна")
        return False

    def keyDown(self, key, *a, **k):
        if self._ok():
            return self._p.keyDown(key, *a, **k)

    def keyUp(self, key, *a, **k):
        return self._p.keyUp(key, *a, **k)


# ================= зрение (без чтения текста, быстро) =================
def screen_thumb(img):
    import cv2
    return cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (160, 90), interpolation=cv2.INTER_AREA)


def screen_moved(ref, cur):
    """Изменилась ли картинка заметно (хотя бы ~0.3% пикселей). Нужно, чтобы отличать
    живую игру (лобби, матч, полёт) от зависшей - только зависшую стоит перезапускать."""
    import cv2
    if ref is None:
        return True
    return float((cv2.absdiff(ref, cur) > 12).mean()) > 0.003


# зоны интерфейса Fortnite, где сундуки не ищем (доли экрана): x1, y1, x2, y2
HUD_ZONES = [(0, 0, 1, 0.10), (0.77, 0, 1, 1), (0, 0.86, 1, 1), (0, 0.80, 0.24, 1),
             (0.60, 0.80, 1, 1), (0, 0.30, 0.20, 0.62)]


def find_chest(img, amin=120):
    """Ищет золотой сундук (свечение). img - BGR кадр. Возвращает dict или None.
    dx/dy - смещение от центра экрана (-0.5..0.5), area - размер (больше = ближе).
    Отсекает похожее по цвету: песок/дерево (сплошная заливка), закат/солнце (пересвет),
    пятна посреди жёлтого фона и всё, что слишком высоко над горизонтом."""
    import cv2
    import numpy as np
    SW, SH = 640, 360
    small = cv2.resize(img, (SW, SH), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (12, 110, 165), (34, 255, 255))
    for x1, y1, x2, y2 in HUD_ZONES:
        m[int(y1 * SH):int(y2 * SH), int(x1 * SW):int(x2 * SW)] = 0
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m)
    best = None
    for i in range(1, n):
        a = st[i, 4]
        w, h = st[i, 2], st[i, 3]
        if a < amin or a > 6000 or a / float(w * h) < 0.2 or not (0.3 <= w / float(h) <= 3.0):
            continue
        cx, cy = cen[i]
        dy = cy / SH - 0.5
        if dy < -0.25:
            continue  # в небе / на верхушках - не сундук
        msk = lab == i
        px = hsv[msk]
        core = px[(px[:, 1] >= 110) & (px[:, 2] >= 165)]
        if len(core) < 8 or (core[:, 0].std() < 1.0 and core[:, 2].std() < 12):
            continue  # однотонная иконка интерфейса
        fill = len(core) / float(a)
        if not (0.42 <= fill <= 0.74):
            continue  # сплошная заливка = песок/доски/стена; сундук светится «рвано», с бликами
        if (core[:, 2] > 235).mean() > 0.10:
            continue  # пересвет = солнце/закат/отражение
        x, y = st[i, 0], st[i, 1]
        x0, y0 = max(0, x - 10), max(0, y - 10)
        x1, y1 = min(SW, x + w + 10), min(SH, y + h + 10)
        ring = hsv[y0:y1, x0:x1][~msk[y0:y1, x0:x1]]
        if len(ring) and (((ring[:, 0] >= 12) & (ring[:, 0] <= 34) & (ring[:, 1] >= 80)).mean() > 0.9):
            continue  # пятно посреди жёлтого (песок, поле)
        score = a * (1.4 - abs(cx / SW - 0.5)) * (0.8 + cy / SH * 0.4)
        if best is None or score > best["score"]:
            best = dict(score=score, area=int(a), dx=cx / SW - 0.5, dy=dy)
    return best


def find_play_button(img):
    """Жёлтая кнопка «Играть» слева внизу лобби. Возвращает (x, y) в пикселях кадра или None."""
    import cv2
    H, W = img.shape[:2]
    x2, y1 = int(W * 0.45), int(H * 0.60)
    k = 0.5
    small = cv2.resize(img[y1:H, 0:x2], None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, (24, 150, 200), (36, 255, 255))
    n, _, st, cen = cv2.connectedComponentsWithStats(m)
    best = None
    for i in range(1, n):
        x, y, w, h, a = st[i]
        w0, h0 = w / k / W, h / k / H
        if not (0.10 <= w0 <= 0.35 and 0.035 <= h0 <= 0.12):
            continue
        if a / float(w * h) < 0.75 or not (2.5 <= w / max(h, 1) <= 8):
            continue
        if best is None or a > best[0]:
            best = (a, int(cen[i][0] / k), int(cen[i][1] / k + y1))
    return best[1:] if best else None


def fix_ssl():
    try:
        import truststore
        truststore.inject_into_ssl()
        return
    except Exception:
        pass
    try:
        import ssl
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
        ssl._create_default_https_context = (
            lambda *a, **k: ssl.create_default_context(cafile=certifi.where()))
    except Exception:
        pass


def norm(s):
    s = s.lower().replace("ё", "е")
    s = re.sub(r"[^a-zа-я ]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def match(text, words, contains=False):
    if not text:
        return False
    for wd in words:
        if text == wd:
            return True
        if contains and len(wd) >= 7 and wd in text:
            return True
        if len(wd) >= 5 and difflib.SequenceMatcher(None, text, wd).ratio() >= 0.8:
            return True
    return False


def find_words(items, words, area=(0, 0, 1, 1), contains=False):
    x1, y1, x2, y2 = area
    for text, ax, ay, rx, ry, *_ in items:
        if x1 <= rx <= x2 and y1 <= ry <= y2 and match(text, words, contains):
            return (ax, ay), text
    return None, None


class AfkBot:
    def __init__(self, settings, log=print, on_state=None):
        self.s = settings
        self.vip = True          # False = бесплатная версия
        self.tier = "vip"        # free / vip / premium
        self._goal_base = {}
        self._goal_done = False
        self.net_down = False
        self.log = log
        self.on_state = on_state or (lambda st: None)
        self.running = False
        self.paused = False
        self.reader = None
        self.ocr_lock = threading.Lock()
        self.exploring = False
        self.explore_thread = None
        self.match_started = None
        self.match_chests = 0
        self.last_human = 0.0        # время последнего действия человека (мышь/клавиатура)
        self.auto_paused = False
        self.grace_until = 0.0       # после запуска/продолжения не ставим авто-паузу
        self.last_token_alert = 0.0
        self.stats = {"tokens": 0, "matches": 0, "jumps": 0, "rewards": 0, "restarts": 0,
                      "chests": 0, "loot": 0, "started": None}
        # 1.6: зрение и навигация
        self.det = None               # нейросеть YOLO (если есть models/afk_yolo.pt)
        self.dataset = None           # сбор кадров для обучения
        self.nav = None               # последнее решение навигатора (компас + миникарта)
        self._nav_turn_t = 0.0        # когда последний раз поворачивали по навигатору
        self._compass_fail = 0
        self.team_watch = vision.TeamWatch()
        self.team_alive = None        # сколько живых в команде видно на панели
        self._match_counted = False   # текущая катка уже засчитана

    def on(self, key):
        """Включена ли функция с учётом уровня (Free / VIP / Premium)."""
        if not self.s.get(key):
            return False
        if key in FREE_FEATURES:
            return True
        if key in ULTIMATE_FEATURES:
            return self.tier == "ultimate"
        if key in PREMIUM_FEATURES:
            return self.tier in PREMIUM_TIERS
        return self.vip

    @property
    def premium(self):
        return self.tier in PREMIUM_TIERS

    @property
    def ultimate(self):
        return self.tier == "ultimate"

    # ---------- PREMIUM: цель фарма ----------
    def goal_progress(self):
        t = self.s.get("goal_type", "matches")
        k = GOAL_STAT.get(t, "matches")
        need = 1 if t == "token" else max(1, int(self.s.get("goal_value", 20) or 1))
        return self.stats.get(k, 0) - self._goal_base.get(k, 0), need

    def check_goal(self):
        if self._goal_done or not self.on("goal_on"):
            return
        cur, need = self.goal_progress()
        if cur < need:
            return
        self._goal_done = True
        t = self.s.get("goal_type", "matches")
        what = "Пиратский токен выпал" if t == "token" else f"{GOAL_NAMES.get(t, '').capitalize()}: {need}"
        act = self.s.get("goal_action", "stop")
        tail = {"stop": "Бот остановлен.", "close": "Закрываю Fortnite.",
                "shutdown": "ПК выключится через 60 сек."}.get(act, "")
        self.log(f"🎯 Цель выполнена: {what}. {tail}")
        self.tg_send(self.report_text(f"🎉 Цель выполнена: {what}\n{tail}"))
        self.running = False
        if act in ("close", "shutdown"):
            threading.Thread(target=self._goal_after, args=(act,), daemon=True).start()

    def _goal_after(self, act):
        time.sleep(3)
        self.kill_fortnite()
        if act == "shutdown":
            try:
                os.system("shutdown /s /t 60 /c \"Afk token: цель выполнена\"")
            except Exception:
                pass

    # ---------- PREMIUM: интернет ----------
    @staticmethod
    def internet_ok():
        import socket
        for host in (("www.epicgames.com", 443), ("1.1.1.1", 443), ("8.8.8.8", 53), ("www.google.com", 443)):
            try:
                socket.create_connection(host, timeout=4).close()
                return True
            except OSError:
                continue
        return False

    def net_loop(self):
        fails = 0
        while self.running:
            time.sleep(30)
            if not self.on("net_guard"):
                continue
            ok = self.internet_ok()
            fails = 0 if ok else fails + 1
            ok = fails < 2  # «нет интернета» - только после 2 проверок подряд (минута)
            if not ok and not self.net_down:
                self.net_down = True
                self.log("🌐 Пропал интернет - жду, ничего не нажимаю")
            elif ok and self.net_down:
                self.net_down = False
                self.log("🌐 Интернет вернулся - продолжаю")
                self.tg_send("🌐 Интернет пропадал, сейчас всё ок - бот продолжает")

    # ---------- управление ботом ----------
    def start(self):
        if self.running:
            return
        self.running = True
        self.paused = False
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        if self.running:
            self.running = False
            self.log("Останавливаю бота...")

    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        self.auto_paused = False
        self.grace_until = time.time() + 15
        self.log("Пауза" if self.paused else "Продолжаю")
        self.on_state("paused" if self.paused else "running")

    def _sleep(self, sec):
        end = time.time() + sec
        while self.running and time.time() < end:
            time.sleep(0.2)
        return self.running

    # ---------- экран ----------
    def init_ocr(self):
        if self.reader:
            return
        import shutil
        self.on_state("loading")
        # модели храним в папке программы (тот же диск, где программа), а не на диске C:
        app = app_dir()
        models = os.path.join(app, "models")
        os.makedirs(models, exist_ok=True)
        # если модели уже скачаны раньше - переносим, чтобы не качать заново
        olds = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "models"),
                os.path.join(os.path.expanduser("~"), ".EasyOCR", "model")]
        try:
            if not [f for f in os.listdir(models) if f.endswith(".pth")]:
                for old in olds:
                    if os.path.isdir(old) and os.path.abspath(old) != os.path.abspath(models):
                        for f in os.listdir(old):
                            if f.endswith(".pth") and not os.path.exists(os.path.join(models, f)):
                                shutil.copy2(os.path.join(old, f), models)
        except Exception:
            pass
        have = [f for f in os.listdir(models) if f.endswith(".pth")]
        # для ru+en EasyOCR нужны только 2 модели: детектор CRAFT и cyrillic_g2
        need = {"craft_mlt_25k.pth", "cyrillic_g2.pth"}
        if not need.issubset(set(have)):
            free = shutil.disk_usage(models).free // (1024 * 1024)
            drive = os.path.splitdrive(models)[0] or "диске"
            if free < 400:
                raise RuntimeError(f"Не хватает места на {drive}: свободно {free} МБ, нужно хотя бы 400 МБ "
                                   "для моделей распознавания. Освободи место и нажми «Запустить» снова.")
            self.log("Загружаю распознавание текста (первый раз скачает ~100 МБ)...")
        else:
            self.log("Загружаю распознавание текста...")
        fix_ssl()
        import easyocr
        try:
            import torch
            gpu = torch.cuda.is_available()
        except Exception:
            gpu = False
        try:
            self.reader = easyocr.Reader(["ru", "en"], gpu=gpu, verbose=False,
                                         model_storage_directory=models)
        except OSError as e:
            for f in os.listdir(models):  # убираем недокачанные файлы
                if not f.endswith(".pth"):
                    try:
                        os.remove(os.path.join(models, f))
                    except Exception:
                        pass
            if getattr(e, "errno", None) == 28:
                raise RuntimeError("Не хватает места на диске для моделей распознавания. "
                                   "Освободи 1 ГБ и нажми «Запустить» снова.")
            raise
        self.log("Распознавание готово (" + ("видеокарта" if gpu else "процессор") + ")")

    @staticmethod
    def _fortnite_rect():
        """Прямоугольник окна Fortnite (left, top, right, bottom) или None."""
        import ctypes.wintypes
        user32 = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                n = user32.GetWindowTextLengthW(hwnd)
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    user32.GetWindowTextW(hwnd, buf, n + 1)
                    if buf.value.strip() == "Fortnite":
                        rect = ctypes.wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        found.append((rect.left, rect.top, rect.right, rect.bottom))
            return True

        try:
            user32.EnumWindows(cb, 0)
        except Exception:
            return None
        return found[0] if found else None

    def _game_monitor(self, sct):
        """Монитор, на котором реально окно Fortnite (для мульти-монитор сетапов)."""
        r = self._fortnite_rect()
        if r:
            cx, cy = (r[0] + r[2]) // 2, (r[1] + r[3]) // 2
            for m in sct.monitors[1:]:
                if (m["left"] <= cx < m["left"] + m["width"]
                        and m["top"] <= cy < m["top"] + m["height"]):
                    return m
        return sct.monitors[1]

    def grab(self):
        """Снимок монитора с окном Fortnite: (BGR кадр, left, top)."""
        import mss
        import numpy as np
        with mss.mss() as sct:
            mon = self._game_monitor(sct)
            img = np.array(sct.grab(mon))[:, :, :3]
        return np.ascontiguousarray(img), mon["left"], mon["top"]

    def ocr_image(self, img, off=(0, 0), region=(0, 0, 1, 1), scale=0.5):
        """Читает текст в части кадра. Возвращает [(норм. текст, x, y, отн_x, отн_y, текст)]."""
        import cv2
        H, W = img.shape[:2]
        x1, y1, x2, y2 = region
        ox, oy = int(W * x1), int(H * y1)
        crop = img[oy:int(H * y2), ox:int(W * x2)]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        if W < 1800 and scale < 1.0:
            # разрешение ниже 1920 (1600x900, 1366x768, 1280x720, растяг): текст мельче —
            # уменьшаем меньше, иначе OCR не читает кнопки «Играть» / «В лобби»
            scale = min(1.0, scale * 1920.0 / max(W, 640))
        if scale != 1.0:
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        with self.ocr_lock:
            found = self.reader.readtext(gray, canvas_size=1280, text_threshold=0.6, low_text=0.35)
        items = []
        for box, text, conf in found:
            if conf < 0.3:
                continue
            cx = ox + sum(p[0] for p in box) / 4 / scale
            cy = oy + sum(p[1] for p in box) / 4 / scale
            items.append((norm(text), off[0] + int(cx), off[1] + int(cy), cx / W, cy / H, text.strip()))
        return items

    def read_screen(self, scale=None, region=(0, 0, 1, 1)):
        img, left, top = self.grab()
        return self.ocr_image(img, (left, top), region, scale or float(self.s.get("scan_scale", 0.5)))

    @staticmethod
    def screenshot_jpg(max_w=1280):
        import cv2
        import mss
        import numpy as np
        with mss.mss() as sct:
            img = np.array(sct.grab(sct.monitors[1]))
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        if img.shape[1] > max_w:
            k = max_w / img.shape[1]
            img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes() if ok else None

    # ---------- Telegram ----------
    @staticmethod
    def reward_text(items):
        """Текст с экрана награды без кнопок и мусора, сверху вниз."""
        skip = set()
        for _, words, _, _ in BUTTONS:
            skip.update(words)
        skip.update(["использовать", "назад", "закрыть", "esc", "use", "back"])
        lines, seen = [], set()
        for text, ax, ay, rx, ry, raw in sorted(items, key=lambda i: (round(i[4], 2), i[3])):
            if len(text) < 4 or text in skip or match(text, list(skip)):
                continue
            if text in seen:
                continue
            seen.add(text)
            lines.append(raw)
        return lines[:20]

    def notify_reward(self, items, photo=None):
        s = self.s
        if not self.tg_ready():
            return
        lines = self.reward_text(items)
        cap = (f"🎁 Награда #{self.stats['rewards']}  ·  {time.strftime('%d.%m %H:%M')}\n\n"
               + ("\n".join("• " + x for x in lines) if lines else "(текст не распознан)"))
        if photo is None and s.get("tg_photo"):
            try:
                photo = self.screenshot_jpg()
            except Exception:
                photo = None

        def send():
            import tg_notify
            try:
                if photo:
                    tg_notify.send_photo(s["tg_token"], s["tg_chat"], photo, cap)
                else:
                    tg_notify.send_text(s["tg_token"], s["tg_chat"], cap)
                self.log("Награда отправлена в Telegram")
            except Exception as e:
                self.log(f"Telegram: {e}")
        threading.Thread(target=send, daemon=True).start()

    def tg_ready(self):
        s = self.s
        return bool(self.on("tg_enabled") and s.get("tg_token") and s.get("tg_chat"))

    def tg_send(self, text):
        if not self.tg_ready():
            return

        def send():
            import tg_notify
            try:
                tg_notify.send_text(self.s["tg_token"], self.s["tg_chat"], text)
            except Exception as e:
                self.log(f"Telegram: {e}")
        threading.Thread(target=send, daemon=True).start()

    def report_text(self, title="📊 Отчёт Afk token"):
        st = self.stats
        sec = int(time.time() - st["started"]) if st["started"] else 0
        return (f"{title}\n"
                f"⏱ Работает: {sec // 3600} ч {sec % 3600 // 60} мин\n"
                f"🎮 Каток: {st['matches']}\n"
                f"🪂 Прыжков: {st['jumps']}\n"
                f"📦 Сундуков: {st['chests']}  ·  🔫 Лута: {st['loot']}\n"
                f"🎁 Наград: {st['rewards']}" + (f"  ·  🏴‍☠️ Токенов: {st['tokens']}" if st['tokens'] else "") + "\n"
                f"🔄 Перезапусков игры: {st['restarts']}")

    def report_loop(self):
        last = time.time()
        while self.running:
            time.sleep(5)
            if not self.on("tg_reports") or not self.tg_ready():
                last = time.time()
                continue
            if time.time() - last >= float(self.s.get("report_min", 60)) * 60:
                last = time.time()
                self.tg_send(self.report_text())

    # ---------- игра вместо тебя: поиск и открытие сундуков ----------
    @staticmethod
    def _mouse_rel(dx, dy=0):
        if not game_active():
            return                      # не крутим мышь по рабочему столу
        ctypes.windll.user32.mouse_event(0x0001, int(dx), int(dy), 0, 0)

    def look(self, dx, dy=0.0):
        """Поворот камеры. «Плавно» — как живой игрок: разгон, торможение, лёгкая дуга,
        иногда небольшой перелёт и доводка. «Резко» — одним рывком, как раньше."""
        if abs(dx) > 25:
            self._look_t = time.time()       # детектор «упёрся» не путает поворот с бегом
        if not self.on("smooth_mouse"):
            self._mouse_rel(dx, dy)
            return
        for sx, sy, pause in vision.human_path(dx, dy):
            self._mouse_rel(sx, sy)
            if pause:
                time.sleep(pause)

    def prompt_texts(self, img=None):
        """Читает подсказку взаимодействия рядом с прицелом (маленькая область - быстро)."""
        if img is None:
            img = self.grab()[0]
        return [i[0] for i in self.ocr_image(img, region=(0.45, 0.42, 0.80, 0.75), scale=1.0)]

    @staticmethod
    def _has(texts, words):
        for t in texts:
            for w in words:
                if len(t) >= 4 and (w in t or match(t, [w])):
                    return t
        return None

    def start_explore(self):
        if not self.running or not self.on("explore") or self.exploring:
            return
        self.exploring = True
        self.explore_thread = threading.Thread(target=self.explore_loop, daemon=True)
        self.explore_thread.start()

    def stop_explore(self):
        if self.exploring:
            self.exploring = False
            if self.explore_thread:
                self.explore_thread.join(timeout=4)

    def _quip(self, pool, chance=0.3):
        """Редкая живая реплика бота в лог (прикол). Выключается настройкой fun_log."""
        try:
            if self.s.get("fun_log", True) and random.random() < chance:
                self.log("🤖 " + random.choice(pool))
        except Exception:
            pass

    def _open_chest(self, name):
        """Зажимает E, пока сундук открывается (подсказка не исчезнет, макс 2.5 сек)."""
        self.pdi.keyDown("e")
        t0 = time.time()
        try:
            time.sleep(0.6)
            while time.time() - t0 < 2.5 and self.exploring:
                if not self._has(self.prompt_texts(), CHEST_WORDS):
                    break
                time.sleep(0.15)
        finally:
            self.pdi.keyUp("e")
        self.stats["chests"] += 1
        self.match_chests += 1
        self.log(f"📦 Открыл сундук ('{name}') - всего: {self.stats['chests']}")
        self._quip(QUIP_CHEST, 0.25)

    def _scan_around(self, turn):
        """Оглядывается по кругу; True, если увидел сундук."""
        d = random.choice((-1, 1))
        for _ in range(int(self.s.get("scan_turns", 2))):
            if not self.exploring or self.paused:
                return False
            self.look(d * turn * random.uniform(0.9, 1.1), random.uniform(-0.01, 0.01) * turn)
            time.sleep(random.uniform(0.15, 0.25))
            img = self.grab()[0]
            if find_chest(img):
                return True
            if self.det and self.det.ready:
                H, W = img.shape[:2]
                if vision.best_target(self.det.detect(img, float(self.s.get("yolo_conf", 0.45))), W, H):
                    return True
        return False

    def _deg(self, deg, turn):
        """Поворот на deg градусов: по калибровке компаса, если есть, иначе примерно."""
        cpd = float(self.s.get("cpd") or 0)
        return deg * cpd if cpd > 0 else deg / 90.0 * turn

    def _unstuck(self, turn, stage, side="d"):
        """Упёрся. 1 — перелезть (прыжок+прыжок, Fortnite сам цепляется за край);
        2 — обойти боком с прыжком (+E: вдруг это дверь); 3 — отойти назад, повернуть
        на 70–110° и пробежать мимо; 4 — не выходит уже который раз: разворот и бегом прочь.
        W после всех вариантов остаётся зажатой."""
        kd, ku = self.pdi.keyDown, self.pdi.keyUp
        other = "a" if side == "d" else "d"
        sign = 1 if side == "d" else -1
        if stage == 1:
            self.log("🦘 Упёрся, перелезаю")
            kd("w")
            self.press("space", 0.12)
            time.sleep(0.3)
            self.press("space", 0.12)
            time.sleep(0.35)
        elif stage == 2:
            self.log("↔ Не перелез, обхожу " + ("справа" if side == "d" else "слева"))
            self.press("e", 0.08)                   # закрытая дверь — откроется
            kd("w")
            kd(side)
            time.sleep(0.25)
            self.press("space", 0.1)
            time.sleep(random.uniform(0.7, 1.1))
            ku(side)
        elif stage == 3:
            self.log("↩ Не обойти, отхожу и бегу в сторону")
            ku("w")
            kd("s")
            time.sleep(random.uniform(0.4, 0.6))
            ku("s")
            self.look(sign * self._deg(random.uniform(70, 110), turn))
            kd("w")
            self.press("space", 0.1)
            time.sleep(random.uniform(1.2, 1.8))
        else:
            self.log("🔄 Тут тупик, разворачиваюсь и ухожу")
            ku("w")
            kd(other)
            time.sleep(0.3)
            ku(other)
            self.look(sign * self._deg(random.uniform(150, 200), turn))
            kd("w")
            self.press("space", 0.1)
            time.sleep(random.uniform(2.0, 3.0))

    def explore_loop(self):
        """Бегает по карте после приземления: сундуки, препятствия, шторм и вода.
        Приоритеты: подсказка «Обыскать» > выход из шторма > сундук > вода/препятствие > прогулка."""
        import cv2
        open_chests = self.ultimate          # сундуки открываем только на Ultimate; Premium = только бег
        self.log("🏃 Приземлился - ищу сундуки" if open_chests else "🏃 Приземлился - бегаю по карте")
        kd, ku = self.pdi.keyDown, self.pdi.keyUp
        walking = sprinting = False
        hits = deque(maxlen=3)
        ema = None
        last_seen = last_scan = last_turn = time.time()
        prompt_t = 0
        stage = 0
        air_until = 0
        chase_t = None
        chase_area = 0
        ignore_until = 0
        next_sprint = time.time() + random.uniform(3, 8)
        sprint_end = 0
        next_strafe = time.time() + random.uniform(6, 14)
        dets, det_t = [], 0.0
        logged = {}
        calib = None               # (курс_до, сколько_повернули, когда)
        calib_tries = 0
        stuck = vision.StuckWatch()
        map_stuck = vision.MapWatch()  # запасная проверка по миникарте (работает и в шторме)
        stuck_hist = deque(maxlen=6)   # когда упирались — чтобы понять, что это тупик
        blocked = []                   # [(курс, до_какого_времени)] — там стена, туда пока не бежим
        calib_amount = 0.0             # на сколько крутим мышь при замере поворота
        dbg_shots = {}                 # отладочные скрины (шторм / упёрся), не чаще раза в минуту
        detour_until = 0               # пока обходим — компас/зона не тянут обратно в стену
        side = random.choice(("a", "d"))

        def walk(on):
            nonlocal walking
            if on and not walking:
                kd("w")
            elif not on and walking:
                ku("w")
            walking = on

        def sprint(on):
            nonlocal sprinting
            if on and not sprinting:
                kd("shift")
            elif not on and sprinting:
                ku("shift")
            sprinting = on

        def say(key, text, every=8.0):
            if time.time() - logged.get(key, 0) > every:
                logged[key] = time.time()
                self.log(text)

        try:
            while self.running and self.exploring:
                if self.paused:
                    walk(False)
                    sprint(False)
                    time.sleep(0.4)
                    continue
                turn = float(self.s.get("turn_speed", 800))
                img = self.grab()[0]
                H, W = img.shape[:2]
                now = time.time()
                if self.dataset:
                    self._save_frame(img, now)

                # 1) подсказка у прицела: «Обыскать» / «Подобрать» / ещё в воздухе
                if now - prompt_t > 0.35:
                    prompt_t = now
                    texts = self.prompt_texts(img)
                    if self.in_air(texts):
                        walk(False)
                        sprint(False)
                        air_until = now + 1.5
                        hits.clear()
                        ema = None
                        time.sleep(0.3)
                        continue
                    chest = self._has(texts, CHEST_WORDS) if open_chests else None
                    loot = (None if chest else self._has(texts, LOOT_WORDS)) if open_chests else None
                    if chest and self.dataset:
                        self._save_frame(img, now, chest=True)
                    if chest:
                        walk(False)
                        sprint(False)
                        self._open_chest(chest)
                        chase_t = None
                        hits.clear()
                        ema = None
                        last_seen = time.time()
                        continue
                    if loot:
                        self.press("e", 0.15)
                        self.stats["loot"] += 1
                if now < air_until:
                    time.sleep(0.1)
                    continue

                # 2) нейросеть (если подключена)
                if self.det and self.det.ready:
                    if now - det_t > 0.12:
                        try:
                            dets = self.det.detect(img, float(self.s.get("yolo_conf", 0.45)))
                        except Exception as e:
                            say("det_err", f"🧠 Ошибка нейросети: {e}", 60)
                            dets = []
                        det_t = now
                else:
                    dets = []

                # 2.5) упёрся? (бежим, а мир по краям экрана не двигается)
                if stage and now - (stuck_hist[-1] if stuck_hist else 0) > 6:
                    stage = 0                        # давно не упирались — начинаем с прыжка
                hit_wall = stuck.feed(img, now, walking, getattr(self, "_look_t", 0.0))
                if not hit_wall and self.on("obstacle_nav"):
                    try:
                        hit_wall = map_stuck.feed(self._box(img, "minimap_box"), now, walking)
                    except Exception:
                        hit_wall = False
                    if hit_wall:
                        say("map_stuck", "🗺 По миникарте стою на месте, значит упёрся", 5)
                if hit_wall:
                    sprint(False)
                    nv = self.nav
                    if nv is not None and nv.get("heading") is not None and now - nv["t"] < 4.0:
                        blocked[:] = [b for b in blocked if b[1] > now]
                        blocked.append((nv["heading"], now + 14.0))   # в эту сторону стена
                    if now - dbg_shots.get("stuck", 0) > 60:
                        dbg_shots["stuck"] = now
                        self._debug_shot(img, "stuck_debug.png")
                    recent = sum(1 for t in stuck_hist if now - t < 25)
                    stuck_hist.append(now)
                    if not self.on("obstacle_nav"):          # базово: прыжок, не помогло — разворот
                        stage = 3 if stage == 1 else 1
                    elif recent >= 4:
                        stage = 4
                    else:
                        stage = min(3, stage + 1)
                    if stage == 3 and self.on("obstacle_nav"):
                        side = "a" if side == "d" else "d"   # боком не вышло — уходим в другую сторону
                    self._unstuck(turn, stage, side)
                    if stage >= 3:
                        detour_until = time.time() + (6 if stage == 4 else 4)
                        if stage == 4:
                            stuck_hist.clear()
                            stage = 0
                    elif stage == 2:
                        detour_until = time.time() + 2.5
                    walking = True
                    stuck.reset()
                    map_stuck.reset()
                    ema = None
                    hits.clear()
                    continue

                # 3) навигация по компасу и миникарте
                nav = self.nav
                # nav["t"] — момент СНИМКА кадра: курс, снятый до поворота, сюда не попадёт
                fresh = (nav is not None and now - nav["t"] < 3.5
                         and nav["t"] > self._nav_turn_t + 0.15 and nav.get("heading") is not None)
                cpd = float(self.s.get("cpd") or 0)
                # «в шторме» не должно мигать, пока после поворота ждём новый кадр компаса
                storm_mode = bool(nav is not None and now - nav["t"] < 5.0 and nav["in_storm"])
                if storm_mode and now - dbg_shots.get("storm", 0) > 60:
                    dbg_shots["storm"] = now
                    self._debug_shot(img, "storm_debug.png")
                if calib and not (fresh and nav["t"] > calib[2] + 0.15):
                    if time.time() - calib[2] > 6:      # компас пропал — замер не удался
                        calib, calib_tries = None, calib_tries + 1
                    walk(True)
                    time.sleep(0.05)
                    continue                            # во время замера других поворотов нет
                if fresh and self.on("zone_nav") and now > detour_until:
                    if calib and nav["t"] > calib[2] + 0.15:
                        d = vision.angdiff(nav["heading"], calib[0])
                        if 8 < d < 150:
                            cpd = calib[1] / d
                            self.s["cpd"] = round(cpd, 3)
                            self.log(f"🧭 Откалибровал поворот: {cpd:.2f} ед. мыши на 1°")
                        else:
                            # повернуло слишком сильно (или в минус через 180°) — крутим меньше,
                            # почти не повернуло — крутим больше, и меряем ещё раз
                            calib_amount = calib[1] * (2.0 if 0 <= d <= 8 else 0.45)
                            calib_tries += 1
                            if calib_tries == 6:
                                self.log("🧭 Не смог замерить поворот мыши, уход от зоны в этом матче "
                                         "не работает. Проверь, что компас вверху экрана виден целиком")
                        calib = None
                    elif cpd <= 0 and calib is None and calib_tries < 6 and (ema is None or storm_mode):
                        amount = max(40.0, min(turn, calib_amount or turn * 0.35))
                        calib = (nav["heading"], amount, time.time())
                        self.look(amount)
                        self._nav_turn_t = time.time()
                        continue
                    elif cpd > 0:
                        blocked[:] = [b for b in blocked if b[1] > now]
                        course = nav["bearing"]
                        if blocked and self.on("obstacle_nav"):
                            # прямо к цели стена — берём ближайший свободный курс, а не лезем обратно
                            course = vision.pick_course(course, [b[0] for b in blocked],
                                                        1 if side == "d" else -1)
                        delta = vision.angdiff(course, nav["heading"])
                        # шторм важнее сундука; вода — только когда не бежим к сундуку
                        urgent = storm_mode or nav["why"] == "storm"
                        limit = 20 if urgent or nav["why"] == "water" else 60
                        if abs(delta) > limit and (urgent or ema is None):
                            if abs(vision.angdiff(course, nav["bearing"])) > 1:
                                say("nav_detour", f"🧱 Прямо стена, обхожу: курс {course:.0f}° "
                                                  f"вместо {nav['bearing']:.0f}°", 6)
                            elif nav["why"] == "storm":
                                say("nav_storm", f"🌀 Рядом шторм, бегу в зону (курс {nav['bearing']:.0f}°)")
                            elif nav["why"] == "water":
                                say("nav_water", "🌊 Впереди вода, меняю направление")
                            self.look(delta * cpd)
                            self._nav_turn_t = time.time()
                            ema = None
                            hits.clear()
                            walk(True)
                            continue

                # 4) препятствие и вода по нейросети — реагируем ДО того, как упрёмся
                if dets and walking and self.on("obstacle_nav"):
                    act = vision.obstacle_action(dets, W, H)
                    if act == "jump":
                        say("obs_jump", "🦘 Препятствие по пояс, прыгаю", 3)
                        self.press("space", 0.1)
                    elif act in ("left", "right"):
                        say("obs_turn", "🪨 Впереди стена или скала, обхожу", 4)
                        self.look((-1 if act == "left" else 1) * self._deg(random.uniform(30, 50), turn))
                        detour_until = max(detour_until, now + 2.0)
                    if vision.water_ahead(dets, W, H):
                        say("water", "🌊 Впереди вода, сворачиваю", 6)
                        self.look(random.choice((-1, 1)) * random.uniform(0.6, 1.0) * turn)
                        ema = None

                # 5) сундук: нейросеть, если есть, иначе золотое свечение (только Ultimate)
                det = None
                if open_chests and now > ignore_until and not storm_mode:
                    det = vision.best_target(dets, W, H) if dets else None
                    if det is not None:
                        # best_target считает площадь в пикселях полного кадра, а пороги ниже
                        # («совсем близко» > 1800) рассчитаны на кадр 640x360 — приводим к нему
                        det = dict(det, area=det["area"] * (640.0 * 360.0) / float(W * H))
                    if det is None:
                        det = find_chest(img)
                    if det and self.dataset:
                        self._save_frame(img, now, chest=True)
                hits.append(bool(det))
                if det and sum(hits) >= 2:
                    sprint(False)
                    if chase_t is None:
                        chase_t, chase_area = now, det["area"]
                    elif det["area"] > chase_area * 1.6:
                        chase_t, chase_area = now, det["area"]
                    elif now - chase_t > 7:
                        self.log("Это не сундук - ищу дальше")
                        walk(False)
                        self.look(random.choice((-1, 1)) * 0.9 * turn)
                        ignore_until = now + 4
                        chase_t = None
                        hits.clear()
                        ema = None
                        continue
                    ema = det["dx"] if ema is None else 0.65 * det["dx"] + 0.35 * ema
                    if abs(ema) > 0.03:
                        self.look(ema * turn * 1.3)
                    if det["dy"] > 0.32:
                        self._mouse_rel(0, turn * 0.04)
                    elif det["dy"] < -0.25:
                        self._mouse_rel(0, -turn * 0.04)
                    last_seen = now
                    if det["area"] > 1800 and abs(ema) < 0.12:
                        walk(False)               # совсем близко - подходим шагами
                        kd("w")
                        time.sleep(0.12)
                        ku("w")
                    else:
                        walk(True)
                else:
                    if not det:
                        ema = None
                        if chase_t and now - last_seen > 1.5:
                            chase_t = None
                    if (not storm_mode and now - last_seen > 12
                            and now - last_scan > float(self.s.get("scan_every", 35))):
                        last_scan = now          # оглядываемся на ходу, без остановки
                        if self._scan_around(turn):
                            last_seen = time.time()
                        continue
                    walk(True)
                    # дорога рядом — мягко подруливаем к ней
                    rb = vision.road_bias(dets, W, H) if dets else None
                    if now < detour_until:
                        pass                          # обходим препятствие — не подруливаем
                    elif rb is not None and abs(rb) > 0.06:
                        self.look(rb * turn * 0.35)
                    elif not fresh and now - last_turn > random.uniform(14, 22):
                        self.look(random.choice((-1, 1)) * random.uniform(0.15, 0.4) * turn)
                        last_turn = now

                # 6) спринт и «живые» движения
                if self.on("sprint") and walking:
                    if storm_mode and not sprinting:
                        sprint(True)                      # в шторме бежим без передышек
                        sprint_end = now + 4
                    elif sprinting and now > sprint_end and storm_mode:
                        sprint_end = now + 4
                    elif sprinting and now > sprint_end:
                        sprint(False)
                        next_sprint = now + random.uniform(4, 12)
                    elif not sprinting and now > next_sprint and (ema is None or storm_mode):
                        sprint(True)
                        sprint_end = now + random.uniform(2, 6) * (2 if storm_mode else 1)
                    if now > next_strafe and ema is None:
                        k = random.choice(("a", "d"))
                        kd(k)
                        time.sleep(random.uniform(0.15, 0.45))
                        ku(k)
                        next_strafe = now + random.uniform(6, 15)
                elif sprinting:
                    sprint(False)

                time.sleep(0.05)
        except Exception:
            self.log("Ошибка поиска сундуков:\n" + traceback.format_exc())
        finally:
            for k in ("w", "shift"):
                try:
                    ku(k)
                except Exception:
                    pass
            self.exploring = False

    # ---------- навигация: компас + миникарта ----------
    def _box(self, img, key):
        H, W = img.shape[:2]
        x1, y1, x2, y2 = (DEFAULTS[key] if not self.s.get(key) else self.s[key])
        return img[int(H * y1):int(H * y2), int(W * x1):int(W * x2)]

    def read_compass(self, img):
        """Курс (0..360, 0 = север) по полоске компаса вверху экрана или None."""
        box = self.s.get("compass_box") or DEFAULTS["compass_box"]
        items = self.ocr_image(img, region=tuple(box), scale=1.6)
        head, n = vision.compass_heading(vision.compass_points([(raw, rx) for _, _, _, rx, _, raw in items]))
        return head

    def _find_compass(self, img):
        """Ищет полосу компаса в верхней части экрана (у всех разное разрешение и масштаб HUD)
        и подстраивает под неё compass_box. -> курс или None."""
        try:
            items = self.ocr_image(img, region=(0.18, 0.0, 0.82, 0.16), scale=1.2)
        except Exception:
            return None
        marks = [(rx, ry, raw) for _, _, _, rx, ry, raw in items if vision.compass_points([(raw, rx)])]
        if len(marks) < 3:
            return None
        best = []                                   # метки компаса стоят в одну строку
        for _, y0, _ in marks:
            row = [m for m in marks if abs(m[1] - y0) < 0.012]
            if len(row) > len(best):
                best = row
        if len(best) < 3:
            return None
        head, n = vision.compass_heading(vision.compass_points([(raw, rx) for rx, _, raw in best]))
        if head is None or n < 3:
            return None
        xs = [m[0] for m in best]
        y = sum(m[1] for m in best) / len(best)
        self.s["compass_box"] = [round(max(0.0, min(xs) - 0.08), 3), round(max(0.0, y - 0.025), 3),
                                 round(min(1.0, max(xs) + 0.08), 3), round(min(1.0, y + 0.025), 3)]
        return head

    def _debug_shot(self, img, name):
        """Кадр в logs/ для разбора (шторм, упёрся): по нему потом видно, что видел бот."""
        try:
            import cv2
            d = os.path.join(app_dir(), "logs")
            os.makedirs(d, exist_ok=True)
            ok, buf = cv2.imencode(".png", img)
            if ok:
                with open(os.path.join(d, name), "wb") as f:
                    f.write(buf.tobytes())
        except Exception:
            pass

    def nav_loop(self):
        """Пока бот бегает: раз в ~1.2 сек читает компас и миникарту и решает, куда бежать."""
        warned = False
        while self.running:
            if not self.exploring or self.paused or not self.on("zone_nav"):
                time.sleep(0.5)
                continue
            t0 = time.time()
            try:
                img = self.grab()[0]
                head = self.read_compass(img)
                mm = self._box(img, "minimap_box")
                info = (vision.minimap_info(mm, use_storm=bool(self.s.get("storm_nav")))
                        if mm.size else None)
                if head is None:
                    self._compass_fail += 1
                    if self._compass_fail % 30 == 5:        # ищем компас на этом экране сами
                        found = self._find_compass(img)
                        if found is not None:
                            head, self._compass_fail, warned = found, 0, False
                            self.log("🧭 Нашёл компас на твоём экране, уход от зоны работает")
                    if head is None and self._compass_fail >= 25 and not warned:
                        warned = True
                        self.log("🧭 Не вижу компас вверху экрана, поэтому уход от зоны пока не работает "
                                 "(всё остальное работает). Проверь в Fortnite: режим «Оконный без рамки» "
                                 "и масштаб интерфейса 100%. Бот сам продолжит искать компас.")
                else:
                    self._compass_fail = 0
                if info is not None:
                    bearing, why = vision.choose_bearing(info, head)
                    # t — когда сняли кадр (не когда дочитали): иначе курс «до поворота»
                    # выглядит свежим, и бот доворачивает второй раз мимо цели
                    self.nav = {"t": t0, "heading": head, "bearing": bearing, "why": why,
                                "in_storm": info["in_storm"], "line": info.get("line")}
            except Exception as e:
                self.log(f"Навигация: {e}")
                time.sleep(2)
            time.sleep(max(0.2, 1.2 - (time.time() - t0)))

    # ---------- скрин награды ----------
    def capture_reward(self, img, kind="Награда"):
        """Сохраняет кадр с наградой в rewards/ и возвращает JPEG-обрезку для Telegram."""
        if img is None or not self.on("reward_shots"):
            return None
        import cv2
        try:
            d = os.path.join(app_dir(), "rewards")
            os.makedirs(d, exist_ok=True)
            tag = re.sub(r"[^\w]+", "_", kind.lower()).strip("_") or "reward"
            name = time.strftime("%Y-%m-%d_%H-%M-%S") + f"_{tag}.png"
            save_image(os.path.join(d, name), img, ".png")
            H, W = img.shape[:2]
            crop = img[int(H * 0.06):int(H * 0.94), int(W * 0.1):int(W * 0.9)]
            if crop.shape[1] > 1280:
                k = 1280 / crop.shape[1]
                crop = cv2.resize(crop, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
            ok, buf = cv2.imencode(".jpg", crop, [cv2.IMWRITE_JPEG_QUALITY, 88])
            self.log(f"📸 {kind}: скрин сохранён в rewards\\{name}")
            return buf.tobytes() if ok else None
        except Exception as e:
            self.log(f"Скрин награды: {e}")
            return None

    def verify_play(self, img, left, top, p):
        """Жёлтая кнопка найдена по цвету - проверяем, что на ней «Играть», а не «Отмена»."""
        H, W = img.shape[:2]
        fx, fy = p[0] / W, p[1] / H
        region = (max(0.0, fx - 0.18), max(0.0, fy - 0.07), min(1.0, fx + 0.18), min(1.0, fy + 0.07))
        try:
            items = self.ocr_image(img, (left, top), region, 1.0)
        except Exception:
            return False
        texts = [t for t, *_ in items]
        if any(part in t for t in texts for part in CANCEL_PARTS):
            return False
        return any(match(t, PLAY_WORDS) or t.startswith("играт") or t.startswith("play") for t in texts)

    def save_debug(self, img, name="lobby_debug.png"):
        try:
            d = os.path.join(app_dir(), "logs")
            os.makedirs(d, exist_ok=True)
            save_image(os.path.join(d, name), img, ".png")
            return os.path.join("logs", name)
        except Exception:
            return None

    @staticmethod
    def in_lobby(items):
        found = {t for t, *_ in items if match(t, LOBBY_WORDS, contains=True)}
        return len(found) >= 2 or any(match(t, ["текущий выбор", "current selection"]) for t in found)

    def _mode_button(self, items):
        """Кнопка режима в лобби (под логотипом): ((x, y), размер_команды) или (None, None)."""
        for text, ax, ay, rx, ry, *_ in items:
            if rx <= 0.4 and 0.45 <= ry <= 0.9:
                sz = size_of(text)
                if sz:
                    return (ax, ay), sz
        return None, None

    def set_mode_size(self, img, left, top, items):
        """Новое лобби: на кнопке «Нулевая высота, Одиночки» ставим нужный размер команды.
        True - стоит нужный, False - не получилось, None - кнопки режима не видно."""
        want = self.s.get("team_size", "squads")
        roots = TEAM_SIZE_ROOTS.get(want, TEAM_SIZE_ROOTS["squads"])
        pos, cur = self._mode_button(items)
        if pos is None:
            return None
        if cur == want:
            self.log(f"Лобби: размер команды уже нужный ({want})")
            return True
        self.log(f"Лобби: сейчас {cur}, переключаю на {want}")
        self.focus_game()
        self.click(pos)
        scale = float(self.s.get("scan_scale", 0.5))
        idx = {"solo": 0, "duos": 1, "trios": 2, "squads": 3}.get(want, 3)
        panel_words = ["размер команды", "строительство", "нулевая высота", "рейтинговая лига",
                       "заполнение команды", "team size", "zero build", "build"]
        done = False
        in_panel = False
        img2 = img
        for attempt in range(5):
            if not self._sleep(2.0 if attempt else 3.0):
                return False
            img2, l2, t2 = self.grab()
            H2, W2 = img2.shape[:2]
            # мелкий текст окна режима читаем без уменьшения
            it2 = self.ocr_image(img2, (l2, t2), (0.55, 0.05, 1, 0.45), 1.0)
            in_panel = any(match(t, panel_words, contains=True) for t, *_ in it2)
            if not in_panel:
                self.log("Лобби: окно режима не открылось")
                break
            lab, _ = find_words(it2, ["размер команды", "team size"], (0.55, 0, 1, 1), contains=True)
            ly = (lab[1] - t2) if lab else H2 * 0.306
            # значение под подписью (одиночки / дуэты / трио / отряды)
            val = None
            for text, ax, ay, rx, ry, *_ in it2:
                if 0.58 <= rx <= 0.8 and 0 < (ay - t2) - ly <= H2 * 0.045:
                    val = size_of(text) or val
            if val == want:
                self.log(f"✅ Лобби: размер команды «{want}» выбран")
                done = True
                fl, _ = find_words(it2, ["заполнение команды", "team fill"], (0.55, 0, 1, 1), contains=True)
                if fl is not None:
                    fy = fl[1] - t2
                    off = any(0.58 <= rx <= 0.8 and 0 < (ay - t2) - fy <= H2 * 0.045
                              and ("выкл" in text or text.startswith("off"))
                              for text, ax, ay, rx, ry, *_ in it2)
                    if off:
                        self.log("Лобби: включаю «Заполнение команды»")
                        self.click((l2 + int(W2 * 0.88), t2 + int(fy + H2 * 0.012)))
                        self._sleep(1)
                break
            fracs = (0.784, 0.827, 0.869, 0.912)
            tgt = (l2 + int(W2 * fracs[idx]), t2 + int(ly + H2 * 0.011))
            self.log(f"Лобби: жму иконку «{want}» (сейчас: {val})")
            self.click(tgt)
            if attempt >= 2:
                self.press("enter")
        if not done:
            path = self.save_debug(img2, "mode_debug.png")
            self.log("Не получилось выбрать размер команды" + (f" (скрин: {path})" if path else ""))
        # закрываем окно режима одной Esc (только если оно реально открыто) и проверяем кнопку в лобби
        if in_panel:
            self.press("esc")
            self._sleep(2)
        img3, l3, t3 = self.grab()
        it3 = self.ocr_image(img3, (l3, t3), (0, 0.05, 1, 1), scale)
        pos3, cur3 = self._mode_button(it3)
        if cur3 == want:
            self.log(f"✅ Лобби: на кнопке режима теперь {want}")
            return True
        if done and pos3 is None:
            return True      # выбрали в окне, кнопку просто не прочитали
        self.log(f"Не вышло поставить {want} (на кнопке: {cur3})")
        return False

    def pick_battle_royale(self, img, left, top, items):
        """Новое лобби: выбрать «Королевскую битву» и нажать запуск. Возвращает True, если матч ищется."""
        H, W = img.shape[:2]
        # 1) уже выбрана КБ? (крупный заголовок над лентой «КОРОЛЕВСКАЯ БИТВА / Текущий выбор»)
        title_br = any(match(t, BR_WORDS, contains=True) and 0.55 <= ry <= 0.8 for t, ax, ay, rx, ry, *_ in items)
        # 2) плитка КБ в ленте режимов
        pos, txt = find_words(items, BR_WORDS, (0, 0.78, 1, 1), contains=True)
        if pos is None:
            if title_br or not items:
                # выбранная плитка всегда первая слева в ленте
                pos, txt = (left + int(W * 0.095), top + int(H * 0.88)), "плитка режима"
            else:
                path = self.save_debug(img)
                self.log("Не вижу «Королевскую битву» в лобби. Выбери её руками один раз"
                         + (f" (скрин: {path})" if path else ""))
                return False
        self.log(f"Лобби: выбираю Королевскую битву ({txt})")
        self.focus_game()
        self.click(pos)
        img2 = img
        size = self.s.get("team_size", "squads")
        size_words = TEAM_SIZE_WORDS.get(size, TEAM_SIZE_WORDS["squads"])
        size_done = False
        for attempt in range(4):
            if not self._sleep(2.5):
                return False
            img2, l2, t2 = self.grab()
            it2 = self.ocr_image(img2, (l2, t2), (0, 0.12, 1, 1), float(self.s.get("scan_scale", 0.5)))
            texts = [t for t, *_ in it2]
            if any(part in t for t in texts for part in SEARCH_PARTS):
                self.log("Пошёл поиск матча")
                return True
            # сначала явно ставим размер команды — иначе игра могла оставить «Соло»
            if not size_done:
                pz, tz = find_words(it2, size_words, (0, 0.12, 1, 1), contains=True)
                if pz:
                    size_done = True
                    self.log(f"Лобби: режим «{tz}»")
                    self.click(pz)
                    continue
            p2, t2txt = find_words(it2, START_WORDS, (0, 0.3, 1, 1))
            if p2:
                self.log(f"Нажимаю «{t2txt}»")
                self.click(p2)
                self.click_confirm_if_any()
                if match(t2txt, ["выбрать", "select"]):
                    continue  # после «Выбрать» появится «Играть»
                return True
            if attempt == 0:
                # плитку нужно открыть - иногда нужен второй клик / Enter
                self.click(pos)
        path = self.save_debug(img2)
        self.log("Не нашёл кнопку запуска после выбора режима"
                 + (f". Скинь разработчику {path}" if path else ""))
        self.press("esc")
        return False

    # ---------- ввод ----------
    @staticmethod
    def focus_game():
        user32 = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def enum_cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                n = user32.GetWindowTextLengthW(hwnd)
                if n:
                    buf = ctypes.create_unicode_buffer(n + 1)
                    user32.GetWindowTextW(hwnd, buf, n + 1)
                    if buf.value.strip() == "Fortnite":
                        found.append(hwnd)
            return True

        user32.EnumWindows(enum_cb, 0)
        if found and user32.GetForegroundWindow() != found[0]:
            h = found[0]
            # SW_RESTORE (9) только если игра свёрнута: на развёрнутом окне он его уменьшал —
            # экран «моргал», а клики уходили мимо кнопок
            user32.ShowWindow(h, 9 if user32.IsIconic(h) else 5)
            user32.SetForegroundWindow(h)
            if user32.GetForegroundWindow() != h:
                # Windows не даёт фоновой программе забрать фокус (поверх висит Claude, браузер и т.п.):
                # «прицепляемся» к окну, которое сейчас спереди, и забираем фокус от его имени
                try:
                    fg = user32.GetForegroundWindow()
                    fg_tid = user32.GetWindowThreadProcessId(fg, None)
                    me = ctypes.windll.kernel32.GetCurrentThreadId()
                    if fg_tid and fg_tid != me:
                        user32.AttachThreadInput(me, fg_tid, True)
                        try:
                            user32.BringWindowToTop(h)
                            user32.SetForegroundWindow(h)
                        finally:
                            user32.AttachThreadInput(me, fg_tid, False)
                except Exception:
                    pass
            if user32.GetForegroundWindow() != h:
                # запасной способ: короткое нажатие Alt снимает запрет Windows на смену окна
                try:
                    user32.keybd_event(0x12, 0, 0, 0)
                    user32.keybd_event(0x12, 0, 2, 0)
                    user32.SetForegroundWindow(h)
                except Exception:
                    pass
            _FN["t"] = 0.0
            time.sleep(0.5)

    def click(self, pos):
        x, y = pos
        r = game_rect()
        if (r and not (r[0] + 2 <= x <= r[2] - 2 and r[1] + 2 <= y <= r[3] - 2)) or on_taskbar(x, y):
            self.log(f"Клик ({x}, {y}) мимо игры (панель задач / другое окно) — пропускаю")
            return
        if r and not game_active():
            self.focus_game()
        self.pdi.moveTo(x + 5, y + 3)
        time.sleep(0.15)
        self.pdi.moveTo(x, y)
        time.sleep(0.15)
        self._check_input_reaches(x, y)
        self.pdi.click()

    def _check_input_reaches(self, x, y):
        """Мышь реально встала туда, куда бот её отправил? Если нет — Windows режет ввод
        (игра запущена от администратора, а бот нет) или масштаб экрана сбивает координаты.
        Раньше бот в таком случае молча «жал Играть» по кругу."""
        try:
            from ctypes import wintypes
            pt = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        except Exception:
            return
        if abs(pt.x - x) <= 40 and abs(pt.y - y) <= 40:
            self._input_miss = 0
            return
        self._input_miss = getattr(self, "_input_miss", 0) + 1
        if self._input_miss >= 2 and time.time() - getattr(self, "_input_warn_t", 0) > 600:
            self._input_warn_t = time.time()
            self.log(f"⚠ Мышь не встаёт туда, куда жмёт бот (нужно {x},{y}, а она {pt.x},{pt.y}). "
                     "Windows блокирует нажатия: закрой бота и запусти start.bat ПКМ → «Запуск от имени "
                     "администратора». Не помогло? Поставь масштаб экрана Windows 100%.")
            self.tg_send("⚠ Нажатия бота не доходят до игры. Запусти бота от имени администратора")

    def press(self, key, hold=0.1):
        self.pdi.keyDown(key)
        time.sleep(hold)
        self.pdi.keyUp(key)

    # ---------- игра ----------
    @staticmethod
    def fortnite_running():
        import psutil
        for p in psutil.process_iter(["name"]):
            if p.info["name"] and p.info["name"].lower() == FORTNITE_PROC.lower():
                return True
        return False

    # ---------- Пиратский токен ----------
    def check_token(self, items, img=None):
        if not self.s.get("token_alert", True) or not items:
            return
        pos, txt = find_words(items, TOKEN_WORDS, contains=True)
        if not pos or time.time() - self.last_token_alert < 600:
            return
        self.last_token_alert = time.time()
        self.stats["tokens"] += 1
        self.log("🏴‍☠️ ВЫПАЛ ПИРАТСКИЙ ТОКЕН! Забери его в лобби")
        self._quip(QUIP_TOKEN, 1.0)
        shot = self.capture_reward(img, "Пиратский токен")
        try:
            import winsound
            for _ in range(3):
                winsound.Beep(1200, 250)
                time.sleep(0.1)
        except Exception:
            pass
        if not self.tg_ready():
            return
        cap = ("🏴‍☠️🏴‍☠️ ВЫПАЛ ТОКЕН ПИРАТСКОГО МАГАЗИНА! 🏴‍☠️🏴‍☠️\n\n"
               "Зайди в Fortnite → Магазин и активируй доступ.\n" + time.strftime("%d.%m %H:%M"))
        photo = shot
        if photo is None:
            try:
                photo = self.screenshot_jpg()
            except Exception:
                photo = None

        def send():
            import tg_notify
            try:
                if photo:
                    tg_notify.send_photo(self.s["tg_token"], self.s["tg_chat"], photo, cap)
                else:
                    tg_notify.send_text(self.s["tg_token"], self.s["tg_chat"], cap)
            except Exception as e:
                self.log(f"Telegram: {e}")
        threading.Thread(target=send, daemon=True).start()

    # ---------- умная пауза: человек сел за ПК ----------
    def _input_hook_thread(self):
        """Слушает мышь и клавиатуру. События, которые создаёт сам бот (injected), не считаются."""
        import ctypes.wintypes as wt
        user32 = ctypes.windll.user32
        LRESULT = ctypes.c_ssize_t
        HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)
        user32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, wt.WPARAM, wt.LPARAM]
        user32.CallNextHookEx.restype = LRESULT

        class KBD(ctypes.Structure):
            _fields_ = [("vk", wt.DWORD), ("scan", wt.DWORD), ("flags", wt.DWORD),
                        ("time", wt.DWORD), ("extra", ctypes.c_void_p)]

        class MSE(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long), ("data", wt.DWORD),
                        ("flags", wt.DWORD), ("time", wt.DWORD), ("extra", ctypes.c_void_p)]

        def kb(n, w, l):
            if n == 0:
                k = ctypes.cast(l, ctypes.POINTER(KBD)).contents
                if not (k.flags & 0x10) and k.vk not in (0x78, 0x79):  # не injected, не F9/F10
                    self.last_human = time.time()
            return user32.CallNextHookEx(None, n, w, l)

        def ms(n, w, l):
            if n == 0:
                m = ctypes.cast(l, ctypes.POINTER(MSE)).contents
                if not (m.flags & 0x01):  # не injected
                    self.last_human = time.time()
            return user32.CallNextHookEx(None, n, w, l)

        self._kb_proc, self._ms_proc = HOOKPROC(kb), HOOKPROC(ms)  # держим ссылки
        h1 = user32.SetWindowsHookExW(13, self._kb_proc, None, 0)  # WH_KEYBOARD_LL
        h2 = user32.SetWindowsHookExW(14, self._ms_proc, None, 0)  # WH_MOUSE_LL
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        user32.UnhookWindowsHookEx(h1)
        user32.UnhookWindowsHookEx(h2)

    def watch_loop(self):
        """Умная пауза + гашение монитора."""
        if not getattr(self, "_hook_started", False):
            self._hook_started = True
            threading.Thread(target=self._input_hook_thread, daemon=True).start()
        last_off = 0
        while self.running:
            time.sleep(1)
            now = time.time()
            idle = now - self.last_human
            if self.on("auto_pause") and now > self.grace_until:
                if not self.paused and idle < 2:
                    self.paused = self.auto_paused = True
                    self.log("🧑 Ты за ПК - бот на паузе (продолжит, когда отойдёшь)")
                    self.on_state("paused")
                elif self.auto_paused and idle > float(self.s.get("resume_min", 3)) * 60:
                    self.paused = self.auto_paused = False
                    self.log("▶ Тебя нет уже пару минут - продолжаю работу")
                    self.on_state("running")
            if (self.on("monitor_off") and not self.paused and idle > 60 and now - last_off > 60):
                last_off = now
                try:  # SC_MONITORPOWER = 2 (выключить)
                    ctypes.windll.user32.PostMessageW(0xFFFF, 0x0112, 0xF170, 2)
                except Exception:
                    pass

    # ---------- ограничение FPS игры ----------
    @staticmethod
    def _fn_ini():
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "FortniteGame", "Saved", "Config",
                            "WindowsClient", "GameUserSettings.ini")

    def apply_fps_limit(self, restore=False):
        """Меняет FrameRateLimit в настройках Fortnite (действует при запуске игры)."""
        if self.fortnite_running():
            return
        path = self._fn_ini()
        if not os.path.exists(path):
            return
        try:
            txt = open(path, encoding="utf-8-sig", errors="ignore").read()
            m = re.search(r"^FrameRateLimit=([0-9.]+)", txt, re.M)
            if not m:
                return
            if restore:
                old = self.s.get("fps_backup")
                if not old:
                    return
                new = old
                self.s["fps_backup"] = ""
            else:
                lim = int(self.s.get("fps_limit", 0) or 0)
                if lim <= 0 or not self.vip:
                    return
                if not self.s.get("fps_backup"):
                    self.s["fps_backup"] = m.group(1)
                new = f"{lim:.6f}"
            txt = txt[:m.start(1)] + new + txt[m.end(1):]
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            self.log(f"FPS игры: {float(new):g}" + (" (вернул как было)" if restore else ""))
        except Exception as e:
            self.log(f"Не удалось изменить FPS: {e}")

    GFX_KEYS = ("sg.ResolutionQuality", "sg.ViewDistanceQuality", "sg.AntiAliasingQuality",
                "sg.ShadowQuality", "sg.PostProcessQuality", "sg.TextureQuality", "sg.EffectsQuality",
                "sg.FoliageQuality", "sg.ShadingQuality")

    def apply_low_gfx(self, restore=False):
        """PREMIUM: минимальная графика на время фарма, потом возвращает как было."""
        if self.fortnite_running():
            return
        path = self._fn_ini()
        if not os.path.exists(path):
            return
        try:
            txt = open(path, encoding="utf-8-sig", errors="ignore").read()
            if restore:
                bak = self.s.get("gfx_backup")
                if not bak:
                    return
                vals = json.loads(bak)
                self.s["gfx_backup"] = ""
            else:
                if not self.on("low_gfx"):
                    return
                vals, cur = {}, {}
                for k in self.GFX_KEYS:
                    m = re.search(r"^" + re.escape(k) + r"=([0-9.]+)", txt, re.M)
                    if m:
                        cur[k] = m.group(1)
                        vals[k] = "0" if k != "sg.ResolutionQuality" else "50.000000"
                if not self.s.get("gfx_backup"):
                    self.s["gfx_backup"] = json.dumps(cur)
            for k, v in vals.items():
                txt = re.sub(r"^(" + re.escape(k) + r"=)[0-9.]+", lambda m: m.group(1) + v, txt, flags=re.M)
            with open(path, "w", encoding="utf-8") as f:
                f.write(txt)
            self.log("Графика игры: " + ("вернул как было" if restore else "минимальная на время фарма"))
        except Exception as e:
            self.log(f"Не удалось изменить графику: {e}")

    def launch_fortnite(self):
        self.apply_fps_limit()
        self.apply_low_gfx()
        self.log("Запускаю Fortnite через Epic Games Launcher...")
        try:
            os.startfile(LAUNCH_URL)
        except Exception as e:
            self.log(f"Не удалось запустить: {e}")
        return self._sleep(LAUNCH_WAIT)

    @staticmethod
    def kill_fortnite():
        import psutil
        names = {FORTNITE_PROC.lower(), "fortnitelauncher.exe",
                 "fortniteclient-win64-shipping_eac.exe",
                 "fortniteclient-win64-shipping_eac_eos.exe"}
        for p in psutil.process_iter(["name"]):
            try:
                if p.info["name"] and p.info["name"].lower() in names:
                    p.kill()
            except Exception:
                pass

    def restart_game(self):
        self.kill_fortnite()
        self.stats["restarts"] += 1
        self.log("Fortnite закрыт, жду 20 сек...")
        if not self._sleep(20):
            return False
        return self.launch_fortnite()

    def click_confirm_if_any(self):
        time.sleep(1.5)
        pos, txt = find_words(self.read_screen(), CONFIRM_WORDS, (0.2, 0.3, 0.8, 0.9))
        if pos:
            self.log(f"Подтверждаю: '{txt}'")
            self.click(pos)

    def force_leave(self):
        self.log(f"Матч идёт дольше {self.s['max_match_min']} мин - выхожу через ESC")
        self.focus_game()
        self.press("esc")
        time.sleep(2)
        pos, txt = find_words(self.read_screen(), LEAVE_WORDS)
        if pos:
            self.log(f"Нажимаю '{txt}'")
            self.click(pos)
            self.click_confirm_if_any()
            return True
        self.press("esc")
        return False

    def _schedule_jump(self, txt):
        """Один прыжок на матч. Точка высадки (Premium) заменяет обычную задержку прыжка."""
        if getattr(self, "_jump_pending", False):
            return
        self._jump_pending = True
        delay = float(self.s["jump_delay"])
        if self.on("land_mode"):
            spot = self.s.get("land_spot", "mid")
            if spot == "random":
                spot = random.choice(list(LAND_DELAY))
            delay = random.uniform(*LAND_DELAY.get(spot, LAND_DELAY["mid"]))
            self.log(f"🎯 Точка высадки: {dict(start='начало', mid='середина', end='конец').get(spot)} маршрута")
        self.log(f"🚌 Автобус ('{txt}') - прыгаю через {delay:g} сек")
        t = threading.Timer(delay, self.do_jump)
        t.daemon = True
        t.start()

    def after_drop(self):
        """Персонаж уже падает без автобуса: считаем высадку и после приземления ищем сундуки."""
        self.stats["jumps"] += 1
        if self.on("explore"):
            self._jump_id = getattr(self, "_jump_id", 0) + 1
            threading.Thread(target=self._wait_landing, args=(self._jump_id,), daemon=True).start()

    def do_jump(self):
        self._jump_pending = False
        if not self.running or self.paused:
            return
        self.focus_game()
        self.log("Прыгаю из автобуса")
        self.stats["jumps"] += 1
        # Раньше пробел жался 2 раза подряд: второй раскрывал дельтаплан сразу после прыжка,
        # и персонаж ~2 минуты летел на дельтаплане. Теперь жмём 1 раз и повторяем, только
        # если всё ещё видна подсказка «Прыгнуть» (нажатие не дошло, мы ещё в автобусе).
        self.press("space")
        for _ in range(3):
            time.sleep(1.2)
            try:
                pt = self.prompt_texts()
            except Exception:
                break
            if self.in_air(pt):
                break                      # уже падаем - пробел больше НЕ трогаем
            if self._has(pt, JUMP_WORDS):
                self.log("Ещё в автобусе, жму прыжок ещё раз")
                self.focus_game()
                self.press("space")
            else:
                break
        if self.on("explore"):
            self._jump_id = getattr(self, "_jump_id", 0) + 1
            threading.Thread(target=self._wait_landing, args=(self._jump_id,), daemon=True).start()

    def in_air(self, texts):
        return self._has(texts, AIR_WORDS) is not None

    def _wait_landing(self, jid):
        """Ждёт, пока пропадут подсказки «свободное падение / раскрыть дельтаплан» - значит, приземлился."""
        t0 = time.time()
        max_wait = max(75.0, float(self.s.get("explore_delay", 90)))
        seen_air, ground_n = False, 0
        time.sleep(4)
        while self.running and jid == self._jump_id and not self.exploring:
            if time.time() - t0 > max_wait:
                self.log("Не увидел приземления, начинаю искать по таймеру")
                break
            if self.paused:
                time.sleep(1)
                continue
            try:
                air = self.in_air(self.prompt_texts())
            except Exception:
                air = False
            if air:
                seen_air, ground_n = True, 0
            else:
                ground_n += 1
            # приземлился: подсказки полёта были и пропали на 3 проверки подряд
            if seen_air and ground_n >= 3:
                break
            # подсказок полёта не было вообще 40 сек (другой язык/интерфейс) - считаем, что на земле
            if not seen_air and time.time() - t0 > 40:
                break
            time.sleep(0.8)
        if self.running and jid == self._jump_id and not self.exploring:
            time.sleep(1.0)
            self.start_explore()

    def _afk_ok(self):
        return (self.running and not self.paused and not self.exploring
                and self.on("anti_afk"))

    def anti_afk_loop(self):
        """Держит W afk_hold секунд, потом пауза afk_pause секунд, и по кругу."""
        last = time.time()
        while self.running:
            time.sleep(0.5)
            if not self._afk_ok():
                last = time.time()
                continue
            if time.time() - last < float(self.s.get("afk_pause", 30)):
                continue
            hold = float(self.s.get("afk_hold", 30))
            self.focus_game()
            human = self.on("human_afk")
            self.log(f"Анти-AFK: держу W {hold:g} сек" + (" (как человек)" if human else ""))
            self.pdi.keyDown("w")
            end = time.time() + hold
            nxt = time.time() + random.uniform(1.5, 4)
            try:
                while self._afk_ok() and time.time() < end:
                    time.sleep(0.2)
                    if human and time.time() >= nxt:
                        self._human_move()
                        nxt = time.time() + random.uniform(1.5, 4.5)
            finally:
                self.pdi.keyUp("w")
            last = time.time()

    def _human_move(self):
        """PREMIUM: случайное «живое» действие - стрейф, прыжок, присед или поворот."""
        try:
            act = random.choice(("strafe", "strafe", "jump", "crouch", "turn", "turn"))
            if act == "strafe":
                k = random.choice(("a", "d"))
                self.pdi.keyDown(k)
                time.sleep(random.uniform(0.3, 0.9))
                self.pdi.keyUp(k)
            elif act == "jump":
                self.press("space")
            elif act == "crouch":
                self.press("ctrl", random.uniform(0.3, 0.8))
            else:
                turn = float(self.s.get("turn_speed", 800))
                self.look(random.uniform(-0.3, 0.3) * turn, random.uniform(-0.02, 0.02) * turn)
        except Exception:
            pass

    def _count_match(self):
        """Катка засчитывается один раз — когда бот реально в матче (автобус / полёт)."""
        if not getattr(self, "_match_counted", True):
            self._match_counted = True
            self.stats["matches"] += 1
            self.log(f"🎮 Катка #{self.stats['matches']} началась")

    def _save_frame(self, img, now, chest=False):
        """Сохраняет кадр для обучения нейросети и пишет прогресс в журнал."""
        ds = self.dataset
        try:
            if ds.maybe_save(img, now, "chest" if chest else "run", force=chest):
                n = ds.count
                if n % 100 == 0:
                    self.log(f"🗂 Кадров для нейросети: {n} / {ds.max} (с сундуками: {ds.chests})")
            elif ds.stopped and not getattr(ds, "_told", False):
                ds._told = True
                if ds.stopped == "limit":
                    self.log(f"✅ Набрал {ds.max} кадров, сбор остановлен. Можно размечать")
                else:
                    self.log("⚠️ На диске меньше 1 ГБ, сбор кадров остановлен")
        except Exception:
            pass

    def _init_vision(self):
        """Нейросеть (если есть модель) и сбор кадров для обучения."""
        import detector
        app = app_dir()
        self.s["cpd"] = 0.0        # чувствительность могла поменяться — замерим поворот заново в катке
        self.nav = None
        if self.on("explore") and self.det is None:
            self.det = detector.Detector(app, self.log)
            if not self.det.ready and "не найдена" not in (self.det.error or ""):
                # модели просто нет (ИИ-сундуки ещё не вышли) — молчим; пишем только о реальной ошибке
                self.log(f"🧠 Нейросеть не подключена: {self.det.error}. Сундуки ищу по свечению")
        if self.on("dataset_capture"):
            self.dataset = detector.DatasetSaver(app, float(self.s.get("dataset_every", 4)))
            try:
                d = self.dataset.dir
                self.dataset.count = len(os.listdir(d)) if os.path.isdir(d) else 0
            except Exception:
                pass
            self.log(f"🗂 Сбор кадров для нейросети включён → dataset\\images "
                     f"(уже есть: {self.dataset.count} / {self.dataset.max}, кадры с сундуками сохраняю чаще)")
        else:
            self.dataset = None
        if self.on("smooth_mouse"):
            self.log("🖱 Мышь: плавная (как у человека)")

    # ---------- главный цикл ----------
    def _run(self):
        try:
            import keyboard
        except Exception:
            keyboard = None
            self.log("⚠ Библиотека keyboard не найдена: F9/F10 не работают, управляй кнопками в окне")
        try:
            import pydirectinput
            pydirectinput.PAUSE = 0.05
            pydirectinput.FAILSAFE = False
            self.pdi = SafeInput(pydirectinput, self)
            self.init_ocr()
            if not self.running:
                return
            self._init_vision()
            try:
                if keyboard is not None:
                    keyboard.add_hotkey("f9", self.toggle_pause)
                    keyboard.add_hotkey("f10", self.stop)
            except Exception:
                pass
            threading.Thread(target=self.anti_afk_loop, daemon=True).start()
            threading.Thread(target=self.report_loop, daemon=True).start()
            self.grace_until = time.time() + 20
            self.auto_paused = False
            threading.Thread(target=self.watch_loop, daemon=True).start()
            self.apply_fps_limit()
            self.apply_low_gfx()
            threading.Thread(target=self.net_loop, daemon=True).start()
            threading.Thread(target=self.nav_loop, daemon=True).start()
            self._goal_base = dict(self.stats)
            self._goal_done = False
            self.net_down = False
            self.stats["started"] = time.time()
            self.on_state("running")
            self.log("Бот запущен. F9 - пауза, F10 - стоп.")
            self.tg_send("▶️ Afk token запущен")
            import urllib.error
            while self.running:
                try:
                    self._loop()
                    break
                except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, ConnectionError) as e:
                    self.log(f"🌐 Сбой сети ({e}). Не останавливаюсь, пробую снова через 10 сек")
                    time.sleep(10)
        except RuntimeError as e:
            self.log("⚠ " + str(e))
        except Exception:
            self.log("ОШИБКА:\n" + traceback.format_exc())
        finally:
            if self.stats["started"]:
                self.tg_send(self.report_text("⏹ Afk token остановлен. Итог"))
            self.running = False
            self.exploring = False
            try:
                if keyboard is not None:
                    keyboard.unhook_all_hotkeys()
            except Exception:
                pass
            self.stats["started"] = None
            self.auto_paused = False
            self.paused = False
            self.apply_fps_limit(restore=True)
            self.apply_low_gfx(restore=True)
            self.on_state("stopped")
            self.log("Бот остановлен")

    def _loop(self):
        import cv2
        s = self.s
        match_since = bus_seen_at = None
        last_progress = time.time()
        last_leave_try = 0
        last_thumb = None
        last_ocr = 0
        scan_n = 0
        play_block_until = 0   # после нажатия «Играть» не трогаем жёлтую кнопку (там «Отмена»)
        lobby_since = None
        last_pick = 0
        last_tab = 0
        last_air_chk = 0
        alive_ref = None
        last_alive = time.time()
        blind_since = None
        last_blind_warn = 0
        last_team_chk = 0
        last_team_log = None
        spectating = None      # время, когда персонаж выбыл и бот смотрит за командой
        last_spec_log = 0
        size_checked = False   # в этом лобби уже выставляли размер команды (Отряды и т.п.)
        go_lobby = False       # прошлая катка была без тиммейтов -> в лобби, а не «Играть снова»
        mode_ok = s.get("team_size", "squads") == "solo"   # размер команды в лобби уже проверен

        while self.running:
            self.check_goal()
            if not self.running:
                break
            if self.paused or self.net_down:
                time.sleep(0.5)
                last_progress = last_alive = time.time()
                continue

            if self.on("auto_restart") and not self.fortnite_running():
                if not self.launch_fortnite():
                    return
                match_since = bus_seen_at = None
                last_progress = last_alive = time.time()
                alive_ref = None
                continue

            img, left, top = self.grab()

            # Захват пустой/чёрный -> бот «слепой». Чаще всего Fortnite в полноэкранном
            # режиме (mss снимает чёрное) или игра на другом мониторе. Раньше бот при
            # этом молча ничего не делал; теперь прямо говорит, что чинить.
            try:
                blank = float(img.std()) < 3.0
            except Exception:
                blank = False
            if blank:
                blind_since = blind_since or time.time()
                if time.time() - blind_since > 8 and time.time() - last_blind_warn > 60:
                    last_blind_warn = time.time()
                    self.log("⚠ Не вижу игру, экран чёрный. Открой в Fortnite «Настройки → "
                             "Режим отображения → Оконный без рамки» (НЕ полный экран) и запусти "
                             "бота от имени администратора. Если мониторов два, Fortnite должен "
                             "быть на том же мониторе, что и рабочий стол.")
                self._sleep(float(s.get("scan_interval", 1.0)))
                continue
            blind_since = None

            # игра «живая», пока картинка меняется. Перезапуск - только если экран
            # застыл на stuck_min минут подряд (реальное зависание / окно ошибки).
            try:
                cur_thumb = screen_thumb(img)
                if screen_moved(alive_ref, cur_thumb):
                    alive_ref = cur_thumb
                    last_alive = time.time()
            except Exception:
                last_alive = time.time()
            if self.on("auto_restart"):
                limit = max(5.0, float(s["stuck_min"]))
                if time.time() - last_alive > limit * 60:
                    self.log(f"Экран не меняется {limit:g} мин - игра зависла, перезапускаю Fortnite")
                    if not self.restart_game():
                        return
                    match_since = bus_seen_at = None
                    last_progress = last_alive = time.time()
                    alive_ref = None
                    continue
            hit = None

            # 1) кнопка «Играть» по цвету - мгновенно, без чтения букв
            if self.on("auto_play") and not self.exploring and time.time() > play_block_until:
                p = find_play_button(img)
                if p:
                    if self.verify_play(img, left, top, p):
                        hit = ("play", (left + p[0], top + p[1]), "играть")
                    else:
                        play_block_until = time.time() + 5  # жёлтая, но не «Играть» - позже проверим

            # 2) чтение текста - только если экран изменился (или давно не читали)
            items = []
            jump_on = self.on("auto_jump") or self.on("land_mode")
            waiting_bus = (jump_on and match_since and bus_seen_at is None
                           and time.time() - match_since < 10 * 60)
            if hit is None:
                thumb = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (96, 54))
                changed = last_thumb is None or cv2.absdiff(thumb, last_thumb).mean() > 2.5
                if changed or waiting_bus or time.time() - last_ocr > 6:
                    scan_n += 1
                    scale = float(s.get("scan_scale", 0.5))
                    if waiting_bus:
                        items = self.ocr_image(img, (left, top), (0.2, 0.55, 0.8, 1.0), 1.0)
                        if scan_n % 3 == 0:
                            items += self.ocr_image(img, (left, top), (0, 0, 1, 1), scale)
                    else:
                        region = (0, 0, 1, 1) if scan_n % 4 == 0 else (0, 0.3, 1, 1)
                        items = self.ocr_image(img, (left, top), region, scale)
                    last_thumb = thumb
                    last_ocr = time.time()
            if not self.running:
                return

            if items:
                self.check_token(items, img)

            if items and match_since and spectating is None:
                pos, txt = find_words(items, DEAD_WORDS, contains=True)
                if pos:
                    spectating = time.time()
                    last_team_chk = 0              # сразу посмотреть, кто жив
                    self.log(f"💀 Меня выбили ('{txt}'). Смотрю за своими, "
                             f"новую катку начну, когда выбьют всех")
                    self.stop_explore()

            if waiting_bus and items:
                pos, txt = find_words(items, JUMP_WORDS, contains=True)
                if pos:
                    bus_seen_at = last_progress = time.time()
                    self._count_match()
                    self._schedule_jump(txt)

            # новый режим Fortnite: автобуса нет - сразу свободное падение.
            # Подсказку «Пробел - свободное падение» читаем крупно у прицела.
            if waiting_bus and bus_seen_at is None and time.time() - last_air_chk > 1.5:
                last_air_chk = time.time()
                try:
                    pt = self.prompt_texts(img)
                except Exception:
                    pt = []
                jw = self._has(pt, JUMP_WORDS)
                if jw:
                    bus_seen_at = last_progress = time.time()
                    self._count_match()
                    self._schedule_jump(jw)
                elif self.in_air(pt):
                    bus_seen_at = last_progress = time.time()
                    self._count_match()
                    self.log("🪂 Уже лечу (автобуса нет) - жду приземления")
                    self.after_drop()

            if hit is None and items:
                # всегда «Играть снова» (отряд и режим сохраняются); «В лобби» — только если
                # кнопки «Играть снова» на экране нет (она первая в списке BUTTONS)
                replay = self.vip
                for name, words, area, flag in BUTTONS:
                    if not self.on(flag) or (name == "play_again" and not replay):
                        continue
                    if (name == "play_again" and (go_lobby or not mode_ok)
                            and find_words(items, BUTTONS[1][1], BUTTONS[1][2])[0]):
                        continue   # «Играть снова» оставит Соло - выходим в лобби и ставим Отряды
                    pos, txt = find_words(items, words, area)
                    if pos:
                        if (name in ("play_again", "return_lobby") and spectating
                                and time.time() - spectating < 20 * 60
                                and s.get("team_size", "squads") != "solo"):
                            try:      # считаем живых прямо на этом кадре, а не по старым данным
                                mates = len(vision.team_bars(self._box(img, "team_box")))
                            except Exception:
                                mates = 0
                            self.team_alive = mates
                        else:
                            mates = 0
                        if mates >= 1:
                            if time.time() - last_spec_log > 60:
                                last_spec_log = time.time()
                                self.log(f"👀 Смотрю за своими, живых: {mates}. Жду, пока выбьют всех")
                            last_progress = time.time()
                            continue
                        hit = (name, pos, txt)
                        break

            if (hit and hit[0] == "play" and not size_checked
                    and s.get("team_size", "squads") != "solo"):
                size_checked = True
                try:
                    lob = items or self.ocr_image(img, (left, top), (0, 0.12, 1, 1),
                                                  float(s.get("scan_scale", 0.5)))
                except Exception:
                    lob = []
                self.log("Лобби: перед запуском выставляю размер команды")
                self.stop_explore()
                try:
                    res = self.set_mode_size(img, left, top, lob)
                except Exception as e:
                    self.log(f"Размер команды: {e}")
                    res = False
                if res is not None:
                    if res:
                        mode_ok = True
                        go_lobby = False
                    else:
                        self.log("Размер команды выставить не вышло - жму «Играть» как есть")
                    last_thumb = None
                    continue   # на следующем кадре найдём «Играть» и нажмём
                if self.pick_battle_royale(img, left, top, lob):
                    play_block_until = time.time() + 20
                    self._match_counted = False
                    if not (self.on("auto_jump") or self.on("land_mode")):
                        self._count_match()
                    match_since = last_progress = time.time()
                    self.match_chests = 0
                    bus_seen_at = None
                    lobby_since = None
                    spectating = None
                    go_lobby = False
                    size_checked = False
                    mode_ok = True
                    self.team_alive = None
                    self.team_watch.reset(time.time())
                    last_thumb = None
                    self.log("▶ Ищу матч")
                    continue
                self.log("Размер команды выставить не вышло - жму «Играть» как есть")
                last_thumb = None
                continue   # на следующем кадре заново найдём «Играть» и нажмём

            if hit:
                name, pos, txt = hit
                if name == "claim":
                    self.stats["rewards"] += 1
                    self.notify_reward(items, self.capture_reward(img, "Награда"))
                self.stop_explore()
                self.focus_game()
                self.click(pos)
                last_progress = time.time()
                last_thumb = None
                if name in ("return_lobby", "play_again"):
                    if self.on("tg_match") and match_since:
                        mins = int((time.time() - match_since) / 60)
                        self.tg_send(f"🏁 Катка #{self.stats['matches']} окончена · {mins} мин"
                                     f" · сундуков: {self.match_chests}")
                    self._quip(QUIP_MATCH, 0.4)
                if name in ("play", "play_again"):
                    play_block_until = time.time() + 20
                    size_checked = False
                    if name == "play":
                        go_lobby = False
                    self._match_counted = False      # засчитаем, когда реально окажемся в матче
                    if not (self.on("auto_jump") or self.on("land_mode")):
                        self._count_match()          # автобус не отслеживаем - считаем сразу
                    match_since = time.time()
                    self.match_chests = 0
                    bus_seen_at = None
                    spectating = None
                    self.team_alive = None
                    self.team_watch.reset(time.time())
                    self.log(f"▶ Нажал «{txt}» - ищу матч")
                    if name == "play_again":
                        self.click_confirm_if_any()
                elif name == "return_lobby":
                    match_since = None
                    spectating = None
                    self.log(f"Нажал «{txt}» - выхожу в лобби")
                    self.click_confirm_if_any()
                else:
                    self.log(f"Нажал «{txt}»")
                self._sleep(2)
                continue

            # новое лобби без жёлтой кнопки: сами выбираем Королевскую битву и запускаем
            # не на вкладке «Играть» (Сокровище, Шкафчик, меню «Общение»...) - возвращаемся
            if (self.on("auto_play") and items and not self.exploring and time.time() - last_tab > 20
                    and self.in_lobby(items)
                    and not any(match(t, RESULT_WORDS, contains=True) for t, *_ in items)):
                tab, _ = find_words(items, ["играть", "play"], (0, 0, 0.45, 0.1))
                social = any(match(t, ["общение"]) for t, *_ in items)
                elsewhere = social or any(match(t, ["духи", "развитие", "приключение", "посмотреть архив",
                                                    "сортировка"], contains=True) for t, *_ in items)
                if (tab and elsewhere and not self._mode_button(items)[0]
                        and not any(match(t, BR_WORDS, contains=True) for t, *_ in items)):
                    last_tab = time.time()
                    self.log("Лобби: не на вкладке «Играть» - возвращаюсь")
                    self.stop_explore()
                    if social:
                        self.press("esc")
                        self._sleep(1.5)
                    self.focus_game()
                    self.click(tab)
                    last_thumb = None
                    self._sleep(2)
                    continue

            if self.on("auto_play") and items and self.in_lobby(items) and not self.exploring:
                lobby_since = lobby_since or time.time()
                if (time.time() - lobby_since > 4 and time.time() - last_pick > 25
                        and time.time() > play_block_until):
                    last_pick = time.time()
                    if self.pick_battle_royale(img, left, top, items):
                        play_block_until = time.time() + 20
                        size_checked = False
                        go_lobby = False
                        mode_ok = True
                        self._match_counted = False
                        if not (self.on("auto_jump") or self.on("land_mode")):
                            self._count_match()
                        match_since = last_progress = time.time()
                        self.match_chests = 0
                        bus_seen_at = None
                        lobby_since = None
                        spectating = None
                        self.team_alive = None
                        self.team_watch.reset(time.time())
                        last_thumb = None
                        self.log("▶ Ищу матч")
                    continue
            elif items:
                lobby_since = None

            # рестарт по панели команды: тиммейты выбыли (или их не было) — не стоим одни
            if (match_since and (bus_seen_at or spectating) and self.on("auto_leave")
                    and s.get("team_size", "squads") != "solo"
                    and (spectating or time.time() - bus_seen_at > 25)
                    and time.time() - last_team_chk > 3):
                last_team_chk = time.time()
                try:
                    alive = len(vision.team_bars(self._box(img, "team_box")))
                except Exception:
                    alive = None
                if alive is not None:
                    self.team_alive = alive
                    if alive != last_team_log:
                        last_team_log = alive
                        self.log(f"👥 Живых в команде на панели: {alive}")
                    # пока сам выбыл и смотришь за своими — это не «остался один»
                    verdict = None if spectating else self.team_watch.feed(time.time(), alive)
                    if verdict and not self.on("team_check"):
                        verdict = None
                    if verdict and not s.get("team_calibrated"):
                        verdict = None    # пока панель не откалибрована — только наблюдаем
                    if verdict and time.time() - last_leave_try > 60:
                        last_leave_try = time.time()
                        why = ("тиммейты выбыли" if verdict == "team_gone"
                               else "тиммейтов нет с начала катки")
                        if verdict != "team_gone":
                            go_lobby = True   # похоже, запустилось Соло - в лобби и ставим Отряды
                        self.log(f"👥 {why.capitalize()}, выхожу и ищу новую катку")
                        if self.on("tg_match"):
                            self.tg_send(f"👥 {why.capitalize()}, перезапускаю катку")
                        self.stop_explore()
                        if self.force_leave():
                            match_since = bus_seen_at = spectating = None
                            last_progress = time.time()
                            self._sleep(2)
                            continue

            if (self.on("auto_leave") and match_since
                    and time.time() - match_since > float(s["max_match_min"]) * 60
                    and time.time() - last_leave_try > 120):
                last_leave_try = time.time()
                self.stop_explore()
                if self.force_leave():
                    match_since = bus_seen_at = spectating = None
                    last_progress = time.time()

            self._sleep(float(s.get("scan_interval", 1.0)))
