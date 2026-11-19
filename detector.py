"""Нейросеть-зрение (YOLO) для Afk token. Полностью необязательная.

Положи обученную модель в  models/afk_yolo.onnx  (её делает ai_2_train.bat) — бот начнёт
видеть сундуки, воду, препятствия и дороги нейросетью. Запуск через onnxruntime: маленькая
библиотека, не мешает распознаванию текста; с onnxruntime-directml считает на видеокарте
(любой с DirectX 12, в том числе AMD). Нет модели — бот работает по-старому (по свечению).

Классы модели (при разметке называй ровно так):
    chest     — сундук (обычный и редкий)
    ammo_box  — ящик с патронами
    water     — вода
    obstacle  — камень / скала / стена / дерево / забор — всё, во что упирается персонаж
    road      — дорога / тропинка
"""
import os
import threading
import time

CLASSES = ["chest", "ammo_box", "water", "obstacle", "road"]
MODEL_NAMES = ("afk_yolo.onnx", "afk_yolo.pt")      # ONNX — основной (без тяжёлых библиотек)


def model_path(app_dir):
    for n in MODEL_NAMES:
        p = os.path.join(app_dir, "models", n)
        if os.path.exists(p):
            return p
    return None


def letterbox(img, size):
    """Вписывает кадр в квадрат size×size с серыми полями (как при обучении YOLO)."""
    import cv2
    import numpy as np
    h, w = img.shape[:2]
    r = min(size / h, size / w)
    nw, nh = int(round(w * r)), int(round(h * r))
    out = np.full((size, size, 3), 114, np.uint8)
    dx, dy = (size - nw) // 2, (size - nh) // 2
    out[dy:dy + nh, dx:dx + nw] = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
    return out, r, dx, dy


def decode_yolo(out, names, conf, r, dx, dy, W, H, iou=0.5):
    """Выход YOLOv8/11 (1, 4+классы, N) -> [{'name','conf','box'}] в пикселях исходного кадра."""
    import cv2
    import numpy as np
    p = np.asarray(out)[0]
    if p.shape[0] < p.shape[1]:
        p = p.T                                     # (N, 4+классы)
    scores = p[:, 4:]
    cls = scores.argmax(1)
    sc = scores[np.arange(len(cls)), cls]
    keep = sc >= conf
    if not keep.any():
        return []
    b, cls, sc = p[keep, :4], cls[keep], sc[keep]
    x1 = (b[:, 0] - b[:, 2] / 2 - dx) / r
    y1 = (b[:, 1] - b[:, 3] / 2 - dy) / r
    x2 = (b[:, 0] + b[:, 2] / 2 - dx) / r
    y2 = (b[:, 1] + b[:, 3] / 2 - dy) / r
    x1, x2 = np.clip(x1, 0, W), np.clip(x2, 0, W)
    y1, y2 = np.clip(y1, 0, H), np.clip(y2, 0, H)
    out = []
    for c in np.unique(cls):                        # NMS отдельно по каждому классу
        m = np.where(cls == c)[0]
        rects = [[float(x1[i]), float(y1[i]), float(x2[i] - x1[i]), float(y2[i] - y1[i])] for i in m]
        idx = cv2.dnn.NMSBoxes(rects, [float(sc[i]) for i in m], conf, iou)
        for k in np.array(idx).reshape(-1):
            i = m[int(k)]
            name = names[int(c)] if int(c) < len(names) else str(int(c))
            out.append({"name": name, "conf": float(sc[i]),
                        "box": (float(x1[i]), float(y1[i]), float(x2[i]), float(y2[i]))})
    return out


class Detector:
    def __init__(self, app_dir, log=print):
        self.log = log
        self.model = None           # ultralytics (для .pt, если вдруг нет .onnx)
        self.sess = None            # onnxruntime
        self.names = []
        self.imgsz = 640
        self.ms = 0.0               # среднее время одного кадра, мс
        self.error = None
        self.device = "CPU"
        self._lock = threading.Lock()
        path = model_path(app_dir)
        if not path:
            self.error = "модель не найдена (models/afk_yolo.onnx)"
            return
        meta = os.path.join(app_dir, "models", "afk_yolo.json")
        if os.path.exists(meta):
            try:
                import json
                with open(meta, encoding="utf-8") as fh:
                    j = json.load(fh)
                self.names, self.imgsz = list(j.get("names") or []), int(j.get("imgsz") or 640)
            except Exception:
                pass
        try:
            if path.endswith(".onnx"):
                self._load_onnx(path)
            else:
                self._load_pt(path)
        except Exception as e:
            self.sess = self.model = None
            self.error = f"не удалось загрузить модель: {e}"
            return
        self.log(f"🧠 Нейросеть подключена: {os.path.basename(path)} ({self.device}) · классы: "
                 + ", ".join(self.names))

    def _load_onnx(self, path):
        try:
            import onnxruntime as ort
        except Exception:
            raise RuntimeError("нет библиотеки onnxruntime (pip install onnxruntime)")
        avail = ort.get_available_providers()
        prov = [p for p in ("DmlExecutionProvider", "CPUExecutionProvider") if p in avail]
        so = ort.SessionOptions()
        so.intra_op_num_threads = max(1, min(4, (os.cpu_count() or 4) // 2))   # не душим игру
        self.sess = ort.InferenceSession(path, sess_options=so, providers=prov)
        self.device = "видеокарта" if self.sess.get_providers()[0] == "DmlExecutionProvider" else "процессор"
        self.inp = self.sess.get_inputs()[0].name
        meta = self.sess.get_modelmeta().custom_metadata_map or {}
        if not self.names and "names" in meta:          # ultralytics кладёт имена классов в модель
            import ast
            d = ast.literal_eval(meta["names"])
            self.names = [d[k] for k in sorted(d)]
        if "imgsz" in meta:
            try:
                import ast
                self.imgsz = int(ast.literal_eval(meta["imgsz"])[0])
            except Exception:
                pass
        if not self.names:
            self.names = list(CLASSES)

    def _load_pt(self, path):
        try:
            from ultralytics import YOLO
        except Exception:
            raise RuntimeError("для .pt нужна ultralytics — лучше положи afk_yolo.onnx")
        self.model = YOLO(path, task="detect")
        self.names = [str(v) for _, v in sorted(dict(self.model.names).items())]

    @property
    def ready(self):
        return self.sess is not None or self.model is not None

    def detect(self, img, conf=0.45, imgsz=None):
        """img — BGR кадр. -> [{'name','conf','box':(x1,y1,x2,y2)}] в пикселях кадра."""
        if not self.ready:
            return []
        import numpy as np
        t0 = time.time()
        H, W = img.shape[:2]
        with self._lock:
            if self.sess is not None:
                lb, r, dx, dy = letterbox(img, self.imgsz)
                x = lb[:, :, ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0
                out = self.sess.run(None, {self.inp: np.ascontiguousarray(x)})[0]
                dets = decode_yolo(out, self.names, conf, r, dx, dy, W, H)
            else:
                res = self.model.predict(img, imgsz=imgsz or self.imgsz, conf=conf, verbose=False)[0]
                dets = []
                for b in getattr(res, "boxes", None) or []:
                    c = int(b.cls[0])
                    x1, y1, x2, y2 = (float(v) for v in b.xyxy[0].tolist())
                    dets.append({"name": self.names[c] if c < len(self.names) else str(c),
                                 "conf": float(b.conf[0]), "box": (x1, y1, x2, y2)})
        dt = (time.time() - t0) * 1000
        self.ms = dt if not self.ms else 0.9 * self.ms + 0.1 * dt
        return dets


class DatasetSaver:
    """Сохраняет кадры из каток для обучения нейросети: dataset/images/*.jpg.
    Похожие подряд кадры пропускает, чтобы не было тысячи одинаковых картинок."""

    MAX_FILES = 4000
    MIN_FREE_GB = 1.0           # оставляем на диске хотя бы 1 ГБ

    def __init__(self, app_dir, every_sec=4.0, max_files=MAX_FILES):
        self.dir = os.path.join(app_dir, "dataset", "images")
        self.every, self.max = float(every_sec), int(max_files)
        self.last_t = 0.0
        self.last_thumb = None
        self.count = 0
        self.stopped = ""          # почему перестали сохранять (лимит / мало места)
        self._disk_checked = False # место на диске проверяем и при первом кадре
        self.chests = 0

    def _disk_ok(self):
        try:
            import shutil
            return shutil.disk_usage(self.dir).free / 1024 ** 3 >= self.MIN_FREE_GB
        except Exception:
            return True

    def maybe_save(self, img, now=None, tag="run", force=False):
        """force=True для кадров с сундуком: чаще и без отсева похожих."""
        import cv2
        now = now or time.time()
        if self.stopped:
            return None
        if now - self.last_t < (1.0 if force else self.every):
            return None
        thumb = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (64, 36))
        if self.last_thumb is not None and cv2.absdiff(thumb, self.last_thumb).mean() < (3 if force else 6):
            return None
        os.makedirs(self.dir, exist_ok=True)
        if self.count == 0:
            self.count = len(os.listdir(self.dir))
        if self.count >= self.max:
            self.stopped = "limit"
            return None
        first, self._disk_checked = not self._disk_checked, True
        if (first or self.count % 25 == 0) and not self._disk_ok():
            self.stopped = "disk"
            return None
        h, w = img.shape[:2]
        out = img
        if w > 1280:
            k = 1280 / w
            out = cv2.resize(img, (1280, int(h * k)), interpolation=cv2.INTER_AREA)
        name = time.strftime("%Y%m%d_%H%M%S") + f"_{int(now * 1000) % 1000:03d}_{tag}.jpg"
        path = os.path.join(self.dir, name)
        ok, buf = cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:
            return None
        buf.tofile(path)          # imwrite не умеет русские буквы в пути
        self.last_t, self.last_thumb = now, thumb
        self.count += 1
        if force:
            self.chests += 1
        return path
