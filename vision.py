"""Зрение и «человечность» Afk token.

Здесь только чистые функции: кадр/числа на входе -> решение на выходе.
Никакого ввода, мыши и сети, поэтому всё это можно проверить тестами без игры.

Направления (bearing / heading) везде в градусах: 0 = север, по часовой стрелке
(90 = восток), как на компасе Fortnite. Миникарта считается «север вверху».
"""
import math
import random
import re

import numpy as np


def angdiff(a, b):
    """Подписанная разница углов a-b в диапазоне (-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


# ======================= плавная «человеческая» мышь =======================
def ease_in_out(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)


def human_path(dx, dy=0.0, rng=random):
    """Раскладывает поворот (dx, dy) в счётчиках мыши на шаги как у человека:
    разгон и торможение, лёгкая дуга, иногда небольшой перелёт и доводка.
    Возвращает [(шаг_x, шаг_y, пауза_сек)], сумма шагов ровно (round(dx), round(dy))."""
    tx, ty = int(round(dx)), int(round(dy))
    dist = math.hypot(dx, dy)
    if dist < 1:
        return [(tx, ty, 0.0)] if (tx or ty) else []
    if dist < 12:                       # микрокоррекция — одним-двумя движениями
        return [(tx, ty, 0.0)]
    steps = int(min(40, max(4, dist / 16)))
    dur = min(0.42, 0.05 + dist / 2600.0)
    over = 1.0
    if dist > 150 and rng.random() < 0.45:
        over = 1.0 + rng.uniform(0.03, 0.08)
    gx, gy = dx * over, dy * over
    px, py = -dy / dist, dx / dist      # перпендикуляр для дуги
    wob = rng.uniform(-0.05, 0.05) * dist
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        e = ease_in_out(t)
        w = math.sin(math.pi * t) * wob
        pts.append((gx * e + px * w, gy * e + py * w))
    if over != 1.0:                     # перелетел — доводит обратно
        x0, y0 = pts[-1]
        cs = max(2, steps // 4)
        for i in range(1, cs + 1):
            e = ease_in_out(i / cs)
            pts.append((x0 + (dx - x0) * e, y0 + (dy - y0) * e))
    pause = dur / len(pts)
    out, cx, cy = [], 0, 0
    for x, y in pts:
        ix, iy = int(round(x)) - cx, int(round(y)) - cy
        cx += ix
        cy += iy
        if ix or iy:
            out.append((ix, iy, pause))
    rx, ry = tx - cx, ty - cy
    if rx or ry:
        out.append((rx, ry, 0.0))
    return out


# ================================ компас ================================
_DIRS = {"с": 0, "n": 0, "св": 45, "ne": 45, "в": 90, "e": 90, "юв": 135, "se": 135,
         "ю": 180, "s": 180, "юз": 225, "sw": 225, "з": 270, "w": 270, "сз": 315, "nw": 315}
_DIGIT_FIX = str.maketrans({"o": "0", "о": "0", "O": "0", "О": "0", "l": "1", "i": "1", "|": "1",
                            "s": "5", "б": "6", "b": "6", "z": "2", "g": "9"})


def compass_points(items):
    """items: [(текст, rx)] из полосы компаса (rx — центр слова в долях ширины экрана).
    Возвращает [(rx, градусы)]: числа 0..359 и буквы сторон света (рус/англ)."""
    pts = []
    for text, rx in items:
        t = str(text).strip().lower()
        if not t:
            continue
        if t in _DIRS:
            pts.append((float(rx), float(_DIRS[t])))
            continue
        d = re.sub(r"[^0-9]", "", t.translate(_DIGIT_FIX))
        if d and len(d) <= 3 and len(d) >= len(re.sub(r"\s", "", t)) - 1:
            v = int(d)
            if 0 <= v < 360:
                pts.append((float(rx), float(v)))
    return pts


def compass_heading(pts, center=0.5, tol=7.0):
    """По меткам компаса находит курс в центре экрана.
    Устойчиво к ошибкам распознавания: перебирает пары меток, выбирает модель,
    с которой согласно больше всего меток. -> (курс, число_согласных_меток) или (None, 0)."""
    pts = sorted(set(pts))
    if len(pts) < 2:
        return None, 0
    best = (None, 0, 1e9)
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            (xi, di), (xj, dj) = pts[i], pts[j]
            if xj - xi < 0.01:
                continue
            dd = (dj - di) % 360.0
            if not 0 < dd < 180:
                continue
            slope = dd / (xj - xi)                    # градусов на ширину экрана
            inl, err = 0, 0.0
            for xk, dk in pts:
                e = abs(angdiff(di + slope * (xk - xi), dk))
                if e <= tol:
                    inl += 1
                    err += e
            if inl > best[1] or (inl == best[1] and err < best[2]):
                best = ((di + slope * (center - xi)) % 360.0, inl, err)
    head, inl, _ = best
    if head is None or inl < 2:
        return None, 0
    return head, inl


# =============================== миникарта ===============================
def _keep_big(mask, min_frac=0.02):
    """Оставляет только крупные пятна (шторм — это большая заливка, а не розовая мишура типа сакуры)."""
    import cv2
    n, lab, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), 8)
    if n <= 1:
        return mask
    total = mask.shape[0] * mask.shape[1]
    out = np.zeros_like(mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_frac * total:
            out[lab == i] = 255
    return out


def minimap_masks(bgr):
    """Маски шторма (фиолетовый) и воды (синяя) на кадре миникарты."""
    import cv2
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    storm = cv2.inRange(hsv, (120, 45, 45), (170, 255, 255))
    # режим для дальтоников (дейтеранопия и др.): шторм светло-розовый, оттенок 170–180
    storm |= cv2.inRange(hsv, (170, 35, 150), (180, 140, 255))
    storm |= cv2.inRange(hsv, (0, 35, 150), (4, 140, 255))
    storm |= cv2.inRange(hsv, (116, 85, 185), (122, 135, 250))   # шторм над водой в этом режиме — сиреневый
    water = cv2.inRange(hsv, (88, 80, 60), (115, 255, 255))
    k = np.ones((3, 3), np.uint8)
    storm = cv2.morphologyEx(storm, cv2.MORPH_OPEN, k)
    storm = _keep_big(storm, min_frac=0.02)         # убрать мелкие розовые пятна, не шторм
    water = cv2.morphologyEx(water, cv2.MORPH_OPEN, k) > 0
    return storm > 0, water


def _white_mask(bgr):
    import cv2
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return cv2.inRange(hsv, (0, 0, 185), (180, 65, 255))   # яркое и малонасыщенное = белая обводка


def _ring_white_frac(white, x, y, r, n=60):
    """Какая доля окружности (x,y,r) проходит по белым пикселям — так отличаем круг зоны от предмета."""
    h, w = white.shape
    hit = 0
    for i in range(n):
        a = 2 * math.pi * i / n
        px, py = x + r * math.cos(a), y + r * math.sin(a)
        ok = False
        for dr in (-2, -1, 0, 1, 2):
            xx, yy = int(round(px + dr * math.cos(a))), int(round(py + dr * math.sin(a)))
            if 0 <= xx < w and 0 <= yy < h and white[yy, xx]:
                ok = True
                break
        hit += ok
    return hit / float(n)


def safe_circle(bgr, storm=None):
    """Белый круг безопасной зоны на миникарте (север вверху).
    -> (направление_к_центру_круга | None, уверенность 0..1).
    None, если круг не найден или игрок уже в его центре."""
    import cv2
    h, w = bgr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    white = _white_mask(bgr)
    cv2.circle(white, (int(cx), int(cy)), max(3, int(min(w, h) * 0.13)), 0, -1)   # стрелка игрока — вон
    gray = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    wimg = cv2.GaussianBlur(white, (5, 5), 0)          # только белое: граница шторма сюда не попадает
    rmin, rmax = int(min(w, h) * 0.14), int(min(w, h) * 0.95)
    found = []
    for src, p2 in ((wimg, 18), (gray, 22)):
        try:
            cs = cv2.HoughCircles(src, cv2.HOUGH_GRADIENT, dp=1.2, minDist=max(8, min(w, h) // 12),
                                  param1=100, param2=p2, minRadius=rmin, maxRadius=rmax)
        except Exception:
            cs = None
        if cs is not None:
            found.extend(cs[0][:12])
    if not found:
        return None, 0.0
    circles = [found]
    best, bestf = None, 0.0
    for c in circles[0]:
        f = _ring_white_frac(white, float(c[0]), float(c[1]), float(c[2]))
        if storm is not None:
            # внутри круга зоны шторма нет: если внутри заметно шторма — это значок/надпись, не круг
            x0, y0, rr = float(c[0]), float(c[1]), float(c[2])
            if not (0 <= x0 < w and 0 <= y0 < h):
                continue                         # центр за краем миникарты — не проверить, не верим
            yy, xx = np.ogrid[:h, :w]
            disk = (xx - x0) ** 2 + (yy - y0) ** 2 <= (rr * 0.92) ** 2
            if disk.any() and storm[disk].mean() > 0.06:
                continue
        if f > bestf:
            best, bestf = c, f
    if best is None or bestf < 0.25:            # мало белого по окружности — это не круг зоны
        return None, 0.0
    vx, vy = float(best[0]) - cx, float(best[1]) - cy
    if math.hypot(vx, vy) < max(2.0, float(best[2]) * 0.45):
        return None, float(bestf)               # игрок уже глубоко в зоне — бежать никуда не надо
    bearing = math.degrees(math.atan2(vx, -vy)) % 360.0
    return bearing, float(min(1.0, bestf))


def guide_line(bgr):
    """Белая линия от игрока к безопасной зоне (Fortnite рисует её на миникарте, когда
    игрок вне зоны). Это самый надёжный ориентир: круг зоны в глубоком шторме на миникарту
    не попадает, а линия есть всегда. -> направление (0 = север) или None."""
    import cv2
    h, w = bgr.shape[:2]
    m = min(w, h)
    if m < 40:
        return None
    cx, cy = w / 2.0, h / 2.0
    white = cv2.dilate(_white_mask(bgr), np.ones((3, 3), np.uint8)) > 0
    r0, r1 = m * 0.15, m * 0.49
    n = max(24, int(r1 - r0))
    need = 0.30 * m                      # линия должна тянуться от игрока хотя бы на треть карты
    runs = {}
    for b in range(0, 360, 2):
        a = math.radians(b)
        sa, ca = math.sin(a), math.cos(a)
        run, gap = 0.0, 0
        for i in range(n + 1):
            r = r0 + (r1 - r0) * i / n
            x, y = int(round(cx + sa * r)), int(round(cy - ca * r))
            if not (0 <= x < w and 0 <= y < h):
                break
            if white[y, x]:
                run, gap = r - r0, 0
            else:
                gap += 1
                if gap > 3:
                    break
        runs[b] = run
    good = [b for b, v in runs.items() if v >= need]
    if not good:
        return None
    best = max(good, key=lambda b: runs[b])
    # линия тонкая: «длинных» лучей мало и все рядом. Иначе это белое пятно (снег, надпись)
    if len(good) > 9 or any(abs(angdiff(b, best)) > 14 for b in good):
        return None
    sx = sum(math.sin(math.radians(b)) * runs[b] for b in good)
    sy = sum(math.cos(math.radians(b)) * runs[b] for b in good)
    return math.degrees(math.atan2(sx, sy)) % 360.0


def minimap_info(bgr, step=15, use_storm=True):
    """Анализ миникарты (игрок в центре, север вверху).
    use_storm=False — шторм не учитываем вообще (пока цвет шторма не откалиброван).
    rays: {направление: (доля_воды, доля_шторма)} по лучу от игрока (ближнее важнее);
    in_storm: игрок стоит в шторме; away: направление ОТ шторма (к безопасной зоне) или None."""
    storm, water = minimap_masks(bgr)
    if not use_storm:
        storm = np.zeros_like(storm)
    h, w = storm.shape
    cx, cy = w / 2.0, h / 2.0
    R = min(w, h) * 0.46
    # стоит ли игрок в шторме: смотрим кольцо вокруг стрелки (сама стрелка белая и шторм закрывает)
    yy, xx = np.ogrid[:h, :w]
    dd = (xx - cx) ** 2 + (yy - cy) ** 2
    r1, r2 = min(w, h) * 0.05, min(w, h) * 0.11
    c = storm[(dd >= r1 * r1) & (dd <= r2 * r2)]
    rays = {}
    n = 36
    for b in range(0, 360, step):
        a = math.radians(b)
        ws = ss = tot = 0.0
        for i in range(4, n + 1):                 # центр (стрелка игрока) пропускаем
            r = R * i / n
            x = min(w - 1, max(0, int(cx + math.sin(a) * r)))
            y = min(h - 1, max(0, int(cy - math.cos(a) * r)))
            wgt = 1.0 - 0.6 * (i / n)
            ws += water[y, x] * wgt
            ss += storm[y, x] * wgt
            tot += wgt
        rays[b] = (ws / tot, ss / tot)
    frac = float(storm.mean())
    # 1) главный ориентир — центр белого круга зоны
    circ_b, circ_conf = (safe_circle(bgr, storm) if use_storm else (None, 0.0))
    if circ_b is not None and frac > 0.03:
        ys, xs = np.nonzero(storm)
        sv = math.degrees(math.atan2(xs.mean() - cx, -(ys.mean() - cy))) % 360.0
        if abs(angdiff(circ_b, (sv + 180.0) % 360.0)) > 100:
            circ_b, circ_conf = None, 0.0          # «круг» в сторону шторма — ложный
    away = circ_b
    # 0) белая линия к зоне важнее всего: она точно показывает, куда бежать
    line_b = guide_line(bgr) if use_storm else None
    if line_b is not None:
        away = line_b
    # 2) запасной вариант: подальше от середины шторма
    if away is None and frac > 0.01:
        ys, xs = np.nonzero(storm)
        vx, vy = xs.mean() - cx, ys.mean() - cy
        if math.hypot(vx, vy) > 2:
            to_storm = math.degrees(math.atan2(vx, -vy)) % 360.0
            away = (to_storm + 180.0) % 360.0
    # зона поджимает: шторма в кадре миникарты уже заметно или он близко к игроку
    half = storm[int(cy - R * 0.5):int(cy + R * 0.5), int(cx - R * 0.5):int(cx + R * 0.5)]
    closing = bool(frac > 0.06 or (half.size and half.mean() > 0.04))
    return {"rays": rays, "in_storm": bool(c.size and c.mean() > 0.4), "away": away,
            "storm_frac": frac, "water_frac": float(water.mean()),
            "closing": closing, "circle": circ_b is not None, "circle_conf": circ_conf,
            "line": line_b}


def choose_bearing(info, heading=None, rng=random):
    """Куда бежать: подальше от шторма и воды, без лишних метаний.
    -> (направление, причина) — причина для журнала: 'storm' | 'water' | 'roam'."""
    best_b, best_s = None, -1e9
    prefer = info.get("away")
    urgent = bool(info.get("in_storm") or info.get("closing"))
    line = info.get("line")
    if line is not None:
        # есть линия к зоне — бежим ровно по ней (если там не сплошная вода)
        wf_line = min(info["rays"].items(), key=lambda kv: abs(angdiff(kv[0], line)))[1][0]
        if wf_line < 0.5:
            return float(line), "storm"
    for b, (wf, sf) in info["rays"].items():
        s = -3.0 * sf - 2.5 * wf
        if prefer is not None:
            # к центру зоны тянемся всегда, а когда шторм поджимает — сильно
            s -= (1.8 if urgent else 0.6) * abs(angdiff(b, prefer)) / 180.0
        if heading is not None:
            s -= 0.25 * abs(angdiff(b, heading)) / 180.0     # не дёргаться без причины
        s += rng.uniform(0, 0.04)
        if s > best_s:
            best_b, best_s = b, s
    why = "roam"
    if urgent or (prefer is not None and info.get("circle") and info.get("circle_conf", 0) > 0.3) \
            or (prefer is not None and info.get("storm_frac", 0) > 0.03):
        why = "storm"
    elif heading is not None:
        wf_here = min(info["rays"].items(), key=lambda kv: abs(angdiff(kv[0], heading)))[1][0]
        if wf_here > 0.25:
            why = "water"
    return best_b, why


# ============================ панель команды ============================
def team_bars(bgr):
    """Полоски здоровья (зелёные) на панели команды -> список рядов [(y, ширина)] сверху вниз.
    Один ряд = один живой игрок (включая тебя)."""
    import cv2
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, (35, 90, 110), (85, 255, 255))
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, np.ones((3, 7), np.uint8))
    n, _, stats, _ = cv2.connectedComponentsWithStats(green, 8)
    H, W = green.shape
    bars = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if 2 <= h <= max(18, H * 0.08) and w >= max(20, W * 0.12) and w >= 5 * h and area >= 0.5 * w * h:
            bars.append((y + h / 2.0, float(w)))
    bars.sort()
    rows = []
    for y, w in bars:
        if rows and abs(rows[-1][0] - y) < 9:
            rows[-1] = ((rows[-1][0] + y) / 2.0, max(rows[-1][1], w))
        else:
            rows.append((y, w))
    return rows


class TeamWatch:
    """Решает, пора ли уходить из катки, потому что команды больше нет.
    feed() вызывается раз в несколько секунд с числом живых (включая себя)."""

    def __init__(self, gone_sec=20.0, alone_sec=150.0):
        self.gone_sec, self.alone_sec = gone_sec, alone_sec
        self.mates_ever_seen = False   # на этом ПК детектор хоть раз видел тиммейтов
        self.reset(0.0)

    def reset(self, now):
        self.start, self.peak, self.low_since = now, 0, None

    def feed(self, now, alive):
        """-> None | 'team_gone' (тиммейты были и выбыли) | 'no_team' (их не было вовсе).
        alive = 0 значит «панели сейчас не видно» (карта/меню) — это не доказательство, пропускаем.
        «no_team» срабатывает, только если на этом ПК тиммейтов уже когда-то видели: иначе
        возможно, детектор просто не видит их полоски, и уходить из катки нельзя."""
        if alive <= 0:
            return None
        self.peak = max(self.peak, alive)
        if alive >= 2:
            self.mates_ever_seen = True
        if alive <= 1:
            self.low_since = self.low_since or now
        else:
            self.low_since = None
        if self.low_since is None:
            return None
        if self.peak >= 2 and now - self.low_since >= self.gone_sec:
            return "team_gone"
        if self.peak <= 1 and self.mates_ever_seen and now - self.start >= self.alone_sec:
            return "no_team"
        return None


# ============================== препятствия ==============================
def obstacle_action(dets, W, H):
    """По детекциям нейросети: что делать с препятствием прямо по курсу.
    Персонаж стоит по центру; «по пояс» ≈ 0.62 высоты кадра, ноги ≈ 0.75.
    -> None | 'jump' (выше половины тела, но перепрыгнуть можно) | 'left'/'right' (стена/скала — обойти)."""
    best = None
    for d in dets:
        if d["name"] not in ("obstacle", "rock", "wall", "tree", "fence"):
            continue
        x1, y1, x2, y2 = d["box"]
        if x2 < W * 0.38 or x1 > W * 0.62:      # не по курсу
            continue
        if y2 < H * 0.58:                      # ещё далеко
            continue
        h = (y2 - y1) / H
        if best is None or h > best[0]:
            best = (h, x1, x2, y1)
    if best is None:
        return None
    h, x1, x2, y1 = best
    if y1 > H * 0.62:                          # ниже пояса — сам перешагнёт
        return None
    if y1 < H * 0.30:                          # высокая стена/скала — обходим
        return "left" if (x1 + x2) / 2 > W / 2 else "right"
    return "jump"


def water_ahead(dets, W, H):
    for d in dets:
        if d["name"] != "water":
            continue
        x1, y1, x2, y2 = d["box"]
        if x1 < W * 0.6 and x2 > W * 0.4 and y2 > H * 0.7 and (y2 - y1) > H * 0.12:
            return True
    return False


def best_target(dets, W, H, names=("chest", "ammo_box")):
    """Ближайший (самый крупный) сундук -> {'dx','dy','area','conf','name'} как у find_chest."""
    best = None
    for d in dets:
        if d["name"] not in names:
            continue
        x1, y1, x2, y2 = d["box"]
        area = (x2 - x1) * (y2 - y1)
        if best is None or area > best["area"]:
            best = {"dx": ((x1 + x2) / 2) / W - 0.5, "dy": ((y1 + y2) / 2) / H - 0.5,
                    "area": area, "conf": d["conf"], "name": d["name"]}
    return best


def road_bias(dets, W, H):
    """Смещение к ближайшей дороге (-0.5..0.5) или None."""
    best = None
    for d in dets:
        if d["name"] != "road":
            continue
        x1, y1, x2, y2 = d["box"]
        if y2 < H * 0.55:
            continue
        cx = ((x1 + x2) / 2) / W - 0.5
        if best is None or abs(cx) < abs(best):
            best = cx
    return best


class StuckWatch:
    """Понимает, что персонаж упёрся: бежим (W зажата), а мир вокруг не движется.
    Смотрит НЕ на центр (там анимация бега самого персонажа), а на фон по краям,
    сравнивает кадр с кадром ~0.7 сек назад и берёт медиану по клеткам сетки —
    поэтому трава, частицы и чужие игроки не мешают."""
    GAP = 0.7          # с каким кадром сравнивать (сек назад)
    HOLD = 1.0         # сколько секунд мир должен стоять, чтобы считать «упёрся»
    THR = 2.6          # средняя разница яркости, ниже которой «ничего не движется»

    def __init__(self):
        self.hist = []
        self.still = 0.0       # сколько секунд подряд мир не двигался (повороты не считаются)
        self.last = None
        self.mask = None

    def reset(self):
        self.hist = []
        self.still = 0.0
        self.last = None

    def _small(self, img):
        import cv2
        g = cv2.cvtColor(cv2.resize(img, (96, 54), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        if self.mask is None:
            m = np.ones((54, 96), bool)
            m[int(54 * 0.35):, int(96 * 0.36):int(96 * 0.64)] = False   # персонаж
            m[:int(54 * 0.38), int(96 * 0.80):] = False                 # миникарта
            m[:int(54 * 0.22), :int(96 * 0.22)] = False                 # левый верх HUD
            m[int(54 * 0.86):, :] = False                               # нижний HUD
            self.mask = m
        return g.astype(np.int16)

    def score(self, a, b):
        d = np.abs(a - b)
        vals = []
        for y in range(0, 54, 9):
            for x in range(0, 96, 12):
                mm = self.mask[y:y + 9, x:x + 12]
                if mm.mean() > 0.6:
                    vals.append(d[y:y + 9, x:x + 12][mm].mean())
        return float(np.median(vals)) if vals else 99.0

    def feed(self, img, now, walking, turned_at=0.0):
        """True — упёрся (после этого история сбрасывается).
        Поворот камеры только выбрасывает кадры (сравнивать через поворот нельзя), но НЕ
        обнуляет накопленное время: иначе при частых доворотах к зоне бот мог бесконечно
        бежать в стену и ни разу не заметить, что упёрся."""
        if not walking:
            self.reset()
            return False
        if now - turned_at < 0.5:           # сам поворот (плавная мышь — до 0.45 сек)
            self.hist = []
            self.last = None
            return False
        cur = self._small(img)
        self.hist.append((now, cur))
        self.hist = [h for h in self.hist if now - h[0] < 2.5]
        old = None
        for t, s in self.hist:
            if now - t >= self.GAP:
                old = s
            else:
                break
        if old is None:
            self.last = now
            return False
        if self.score(cur, old) < self.THR:
            self.still += min(0.4, now - self.last) if self.last is not None else 0.0
            if self.still >= self.HOLD:
                self.reset()
                return True
        else:
            self.still = 0.0
        self.last = now
        return False


class MapWatch:
    """Запасная проверка «стою на месте» по миникарте: она «север вверху» и едет только
    когда персонаж реально перемещается, поэтому ей не мешают ни повороты камеры, ни
    туман и дождь шторма на экране. W зажата, а карта не сдвинулась за HOLD сек — упёрся."""
    GAP = 3.0          # с каким кадром миникарты сравнивать (сек назад)
    HOLD = 5.0         # сколько секунд карта должна стоять
    THR = 0.8          # средняя разница яркости, ниже которой «карта не сдвинулась»
    EVERY = 0.5

    def __init__(self):
        self.hist = []
        self.since = None
        self.t = 0.0

    def reset(self):
        self.hist = []
        self.since = None

    @staticmethod
    def _small(mm):
        import cv2
        g = cv2.cvtColor(cv2.resize(mm, (64, 64), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(g, (3, 3), 0).astype(np.int16)

    def feed(self, mm, now, walking):
        if not walking or mm is None or mm.size == 0 or min(mm.shape[:2]) < 40:
            self.reset()
            return False
        if now - self.t < self.EVERY:
            return False
        self.t = now
        cur = self._small(mm)
        self.hist.append((now, cur))
        self.hist = [h for h in self.hist if now - h[0] < self.GAP + 2.0]
        old = None
        for t, s in self.hist:
            if now - t >= self.GAP:
                old = s
            else:
                break
        if old is None:
            return False
        yy, xx = np.ogrid[:64, :64]
        keep = (xx - 32) ** 2 + (yy - 32) ** 2 > 11 ** 2        # стрелка игрока не в счёт
        sd = float(cur[keep].std())
        if sd < 2.5:
            self.since = None           # карта однотонная (вода, сплошной шторм) — судить не по чему
            return False
        if float(np.abs(cur - old)[keep].mean()) < min(self.THR, 0.15 * sd):
            if self.since is None:
                self.since = now - self.GAP
            if now - self.since >= self.HOLD:
                self.reset()
                return True
        else:
            self.since = None
        return False


def pick_course(target, blocked, prefer=1):
    """Куда бежать, если прямой курс target упирается в стену.
    blocked — курсы, в которых недавно упёрлись. Берём ближайший к цели курс (шаг 30°),
    который дальше 50° от всех них; prefer (+1 вправо / -1 влево) — с какой стороны пробовать первой."""
    if not blocked:
        return target % 360.0
    for k in range(0, 6):
        for sg in ((0,) if k == 0 else (prefer, -prefer)):
            c = (target + sg * k * 30.0) % 360.0
            if all(abs(angdiff(c, b)) >= 50 for b in blocked):
                return c
    return (target + 180.0) % 360.0
